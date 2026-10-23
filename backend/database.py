"""SQLite access. One short-lived connection per call; bookings use a write lock."""
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS bookings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ref           TEXT    NOT NULL UNIQUE,
    name          TEXT    NOT NULL,
    phone         TEXT    NOT NULL,
    email         TEXT    NOT NULL DEFAULT '',
    service_id    TEXT    NOT NULL,
    service_name  TEXT    NOT NULL,
    price         INTEGER NOT NULL,
    price_from    INTEGER NOT NULL DEFAULT 0,
    notes         TEXT    NOT NULL DEFAULT '',
    booking_date  TEXT    NOT NULL,           -- YYYY-MM-DD
    booking_time  TEXT    NOT NULL,           -- HH:MM (24h)
    status        TEXT    NOT NULL DEFAULT 'booked',
    created_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bookings_slot ON bookings (booking_date, booking_time);
CREATE TABLE IF NOT EXISTS closures (
    day    TEXT PRIMARY KEY,
    reason TEXT NOT NULL DEFAULT ''
);
"""

SCHEMA_POSTGRES = [
    """CREATE TABLE IF NOT EXISTS bookings (
        id            SERIAL PRIMARY KEY,
        ref           TEXT    NOT NULL UNIQUE,
        name          TEXT    NOT NULL,
        phone         TEXT    NOT NULL,
        email         TEXT    NOT NULL DEFAULT '',
        service_id    TEXT    NOT NULL,
        service_name  TEXT    NOT NULL,
        price         INTEGER NOT NULL,
        price_from    INTEGER NOT NULL DEFAULT 0,
        notes         TEXT    NOT NULL DEFAULT '',
        booking_date  TEXT    NOT NULL,
        booking_time  TEXT    NOT NULL,
        status        TEXT    NOT NULL DEFAULT 'booked',
        created_at    TEXT    NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_bookings_slot ON bookings (booking_date, booking_time)",
    "CREATE TABLE IF NOT EXISTS closures (day TEXT PRIMARY KEY, reason TEXT NOT NULL DEFAULT '')",
]

USE_POSTGRES = bool(config.DATABASE_URL)

STATUSES = ("booked", "completed", "cancelled", "no_show")
REF_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L confusion


class _PgConnection:
    """Makes a psycopg connection look like our SQLite one: '?' placeholders, dict rows."""

    def __init__(self, con):
        self._con = con

    def execute(self, sql, args=()):
        return self._con.execute(sql.replace("?", "%s"), tuple(args))


@contextmanager
def connect():
    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row
        con = psycopg.connect(config.DATABASE_URL, row_factory=dict_row, autocommit=True,
                              connect_timeout=10)
        try:
            yield _PgConnection(con)
        finally:
            con.close()
    else:
        con = sqlite3.connect(config.DB_PATH, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            yield con
        finally:
            con.close()


def init_db() -> None:
    with connect() as con:
        if USE_POSTGRES:
            for statement in SCHEMA_POSTGRES:
                con.execute(statement)
        else:
            con.execute("PRAGMA journal_mode=WAL")
    if not USE_POSTGRES:
        raw = sqlite3.connect(config.DB_PATH, isolation_level=None)
        try:
            raw.executescript(SCHEMA_SQLITE)
        finally:
            raw.close()


_ready = {"ok": False}


def ensure_ready() -> None:
    """Create the tables on first use (not at import, so a database problem can't crash startup)."""
    if not _ready["ok"]:
        init_db()
        _ready["ok"] = True


def load_services() -> list[dict]:
    with open(config.SERVICES_FILE, encoding="utf-8") as fh:
        return json.load(fh)["services"]


def get_service(service_id: str) -> dict | None:
    return next((s for s in load_services() if s["id"] == service_id), None)


def normalize_phone(raw: str) -> str:
    """Digits only; +63917... and 0917... both become 0917... (PH mobile)."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("63") and len(digits) == 12:
        digits = "0" + digits[2:]
    return digits


def new_ref() -> str:
    return "TB-" + "".join(secrets.choice(REF_ALPHABET) for _ in range(6))


def slot_counts(con, start: str, end: str) -> dict:
    """{(date, time): active_booking_count} for start <= date <= end."""
    rows = con.execute(
        "SELECT booking_date, booking_time, COUNT(*) n FROM bookings "
        "WHERE booking_date BETWEEN ? AND ? AND status NOT IN ('cancelled') "
        "GROUP BY booking_date, booking_time", (start, end)).fetchall()
    return {(r["booking_date"], r["booking_time"]): r["n"] for r in rows}


def closed_days(con, start: str, end: str) -> dict:
    rows = con.execute("SELECT day, reason FROM closures WHERE day BETWEEN ? AND ?",
                       (start, end)).fetchall()
    return {r["day"]: r["reason"] for r in rows}


class SlotTaken(Exception):
    pass


def create_booking(data: dict, service: dict) -> dict:
    """Insert a booking atomically; raises SlotTaken if the slot just filled up."""
    with connect() as con:
        if USE_POSTGRES:
            con.execute("BEGIN")
            # one lock per slot: two people booking the same slot are handled one after the other
            con.execute("SELECT pg_advisory_xact_lock(hashtext(?))", (data["date"] + " " + data["time"],))
        else:
            con.execute("BEGIN IMMEDIATE")  # serialize writers -> no double booking
        try:
            taken = con.execute(
                "SELECT COUNT(*) AS n FROM bookings WHERE booking_date=? AND booking_time=? "
                "AND status NOT IN ('cancelled')",
                (data["date"], data["time"])).fetchone()["n"]
            if taken >= config.SLOT_CAPACITY:
                raise SlotTaken()
            ref = new_ref()
            while con.execute("SELECT 1 AS x FROM bookings WHERE ref=?", (ref,)).fetchone():
                ref = new_ref()
            con.execute(
                "INSERT INTO bookings (ref,name,phone,email,service_id,service_name,price,"
                "price_from,notes,booking_date,booking_time,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (ref, data["name"], data["phone"], data["email"], service["id"],
                 service["name"], service["price"], int(service["from"]), data["notes"],
                 data["date"], data["time"],
                 datetime.now(timezone.utc).isoformat(timespec="seconds")))
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    return {"ref": ref}


def row_to_public(r) -> dict:
    return {k: r[k] for k in ("ref", "name", "service_name", "price", "price_from",
                              "notes", "booking_date", "booking_time", "status")}
