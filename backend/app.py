"""TechBai backend: Flask API + static file server for the PyScript frontend.

Run from the project root:   python main.py
"""
import hmac
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta

from flask import Flask, jsonify, request, send_from_directory

import config
import database as db
import schedule

app = Flask(__name__, static_folder=None)
app.json.sort_keys = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # bookings are tiny; reject big bodies

ADMIN_PASSWORD = config.ADMIN_PASSWORD or secrets.token_urlsafe(9)
GENERATED_PASSWORD = not config.ADMIN_PASSWORD

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

# ---- tiny in-memory rate limiter (per IP) ------------------------------
_hits: dict[str, deque] = defaultdict(deque)


def rate_limited(bucket: str, limit: int, per_seconds: int = 3600) -> bool:
    key = f"{bucket}:{request.remote_addr}"
    q, now = _hits[key], time.monotonic()
    while q and now - q[0] > per_seconds:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def error(message: str, status: int = 400, **extra):
    return jsonify({"error": message, **extra}), status


def parse_date(value):
    if not isinstance(value, str) or not DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def require_admin():
    token = request.headers.get("X-Admin-Token", "")
    if hmac.compare_digest(token.encode(), ADMIN_PASSWORD.encode()):
        return None
    if rate_limited("admin-fail", 20, 600):  # only wrong guesses are counted
        return error("Too many attempts. Try again later.", 429)
    return error("Wrong admin password.", 401)


# ---- public API ---------------------------------------------------------
@app.get("/api/config")
def get_config():
    return jsonify({
        "slots": schedule.all_slots(),
        "break": f"{schedule.fmt12(datetime(2000, 1, 1, config.BREAK_START_HOUR).time())} - "
                 f"{schedule.fmt12(datetime(2000, 1, 1, config.BREAK_END_HOUR).time())}",
        "open_weekdays": sorted(config.OPEN_WEEKDAYS),
        "today": schedule.today_local().isoformat(),
        "max_date": (schedule.today_local()
                     + timedelta(days=config.BOOKING_WINDOW_DAYS)).isoformat(),
    })


@app.get("/api/services")
def get_services():
    return jsonify({"services": db.load_services()})


@app.get("/api/availability")
def availability():
    month = request.args.get("month", "")
    if not MONTH_RE.match(month):
        return error("month must look like 2026-10")
    try:
        first = date.fromisoformat(month + "-01")
    except ValueError:
        return error("Invalid month")
    nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    last = nxt - timedelta(days=1)
    slots = schedule.slot_starts()
    now = schedule.now_local()
    with db.connect() as con:
        counts = db.slot_counts(con, first.isoformat(), last.isoformat())
        closed = db.closed_days(con, first.isoformat(), last.isoformat())
    days = {}
    d = first
    while d <= last:
        iso = d.isoformat()
        status = schedule.day_status(d, iso in closed, now)
        free = 0
        if status == "open":
            free = sum(1 for t in slots
                       if counts.get((iso, t.strftime("%H:%M")), 0) < config.SLOT_CAPACITY
                       and not schedule.slot_is_past(d, t, now))
            if free == 0:
                status = "full"
        days[iso] = {"status": status, "free": free, "total": len(slots),
                     "reason": closed.get(iso, "")}
        d += timedelta(days=1)
    return jsonify({"month": month, "days": days})


@app.get("/api/slots")
def slots_for_day():
    day = parse_date(request.args.get("date"))
    if not day:
        return error("date must look like 2026-10-20")
    now = schedule.now_local()
    with db.connect() as con:
        counts = db.slot_counts(con, day.isoformat(), day.isoformat())
        closed = db.closed_days(con, day.isoformat(), day.isoformat())
    status = schedule.day_status(day, day.isoformat() in closed, now)
    out = []
    for s in schedule.all_slots():
        t = datetime.strptime(s["time"], "%H:%M").time()
        taken = counts.get((day.isoformat(), s["time"]), 0) >= config.SLOT_CAPACITY
        if status != "open":
            state = status
        elif schedule.slot_is_past(day, t, now):
            state = "past"
        else:
            state = "booked" if taken else "available"
        out.append({**s, "state": state})
    return jsonify({"date": day.isoformat(), "day_status": status,
                    "reason": closed.get(day.isoformat(), ""), "slots": out})


@app.post("/api/bookings")
def create_booking():
    if rate_limited("book", config.BOOKINGS_PER_IP_PER_HOUR):
        return error("Too many booking attempts. Please try again later.", 429)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("Invalid request.")

    def text(key, limit):
        v = body.get(key, "")
        return v.strip()[:limit] if isinstance(v, str) else ""

    data = {"name": text("name", 80), "email": text("email", 120),
            "notes": text("notes", 500), "time": text("time", 5),
            "date": text("date", 10), "phone": db.normalize_phone(text("phone", 25))}
    errors = {}
    if len(data["name"]) < 2:
        errors["name"] = "Please enter your full name."
    if not (10 <= len(data["phone"]) <= 13):
        errors["phone"] = "Enter a valid mobile number (e.g. 0917 123 4567)."
    if data["email"] and not EMAIL_RE.match(data["email"]):
        errors["email"] = "That email doesn't look right."
    service = db.get_service(text("service_id", 40))
    if not service:
        errors["service_id"] = "Please choose a service."
    day = parse_date(data["date"])
    if not day:
        errors["date"] = "Please pick a date."
    if not schedule.valid_slot(data["time"]):
        errors["time"] = "Please pick a time slot."
    if errors:
        return error("Please fix the highlighted fields.", 422, fields=errors)

    now = schedule.now_local()
    with db.connect() as con:
        closed = db.closed_days(con, data["date"], data["date"])
    if schedule.day_status(day, data["date"] in closed, now) != "open":
        return error("Sorry, we can't take bookings on that date.", 409)
    slot_time = datetime.strptime(data["time"], "%H:%M").time()
    if schedule.slot_is_past(day, slot_time, now):
        return error("That time has already passed. Please pick a later slot.", 409)
    try:
        result = db.create_booking(data, service)
    except db.SlotTaken:
        return error("That slot was just taken. Please choose another time.", 409)
    return jsonify({"ref": result["ref"], "service": service["name"],
                    "date": data["date"], "time": data["time"],
                    "label": next(s["label"] for s in schedule.all_slots()
                                  if s["time"] == data["time"])}), 201


def _find_booking(con, ref, phone):
    row = con.execute("SELECT * FROM bookings WHERE ref=?", (ref.upper().strip(),)).fetchone()
    if row and hmac.compare_digest(db.normalize_phone(row["phone"]),
                                   db.normalize_phone(phone)):
        return row
    return None


@app.post("/api/bookings/lookup")
def lookup_booking():
    if rate_limited("lookup", 30, 600):
        return error("Too many attempts. Try again later.", 429)
    body = request.get_json(silent=True) or {}
    with db.connect() as con:
        row = _find_booking(con, str(body.get("ref", "")), str(body.get("phone", "")))
    if not row:
        return error("No booking found for that reference and phone number.", 404)
    return jsonify(db.row_to_public(row))


@app.post("/api/bookings/cancel")
def cancel_booking():
    if rate_limited("lookup", 30, 600):
        return error("Too many attempts. Try again later.", 429)
    body = request.get_json(silent=True) or {}
    with db.connect() as con:
        row = _find_booking(con, str(body.get("ref", "")), str(body.get("phone", "")))
        if not row:
            return error("No booking found for that reference and phone number.", 404)
        if row["status"] != "booked":
            return error(f"This booking is already {row['status'].replace('_', ' ')}.", 409)
        con.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (row["id"],))
    return jsonify({"ok": True})


# ---- admin API ----------------------------------------------------------
@app.get("/api/admin/bookings")
def admin_bookings():
    if (denied := require_admin()):
        return denied
    day = request.args.get("date", "")
    status = request.args.get("status", "")
    sql, args = "SELECT * FROM bookings WHERE 1=1", []
    if day:
        if not parse_date(day):
            return error("Bad date")
        sql += " AND booking_date=?"
        args.append(day)
    else:
        sql += " AND booking_date>=?"
        args.append(schedule.today_local().isoformat())
    if status in db.STATUSES:
        sql += " AND status=?"
        args.append(status)
    sql += " ORDER BY booking_date, booking_time LIMIT 500"
    with db.connect() as con:
        rows = con.execute(sql, args).fetchall()
        closures = con.execute("SELECT day, reason FROM closures WHERE day>=? ORDER BY day",
                               (schedule.today_local().isoformat(),)).fetchall()
    return jsonify({"bookings": [{**db.row_to_public(r), "id": r["id"], "phone": r["phone"],
                                  "email": r["email"]} for r in rows],
                    "closures": [dict(c) for c in closures]})


@app.post("/api/admin/bookings/<int:booking_id>/status")
def admin_set_status(booking_id):
    if (denied := require_admin()):
        return denied
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in db.STATUSES:
        return error("Invalid status")
    with db.connect() as con:
        cur = con.execute("UPDATE bookings SET status=? WHERE id=?", (status, booking_id))
    return jsonify({"ok": True}) if cur.rowcount else error("Not found", 404)


@app.post("/api/admin/closures")
def admin_add_closure():
    if (denied := require_admin()):
        return denied
    body = request.get_json(silent=True) or {}
    day = parse_date(body.get("date"))
    if not day:
        return error("Bad date")
    with db.connect() as con:
        con.execute("INSERT OR REPLACE INTO closures (day, reason) VALUES (?,?)",
                    (day.isoformat(), str(body.get("reason", ""))[:100]))
    return jsonify({"ok": True})


@app.delete("/api/admin/closures/<day>")
def admin_remove_closure(day):
    if (denied := require_admin()):
        return denied
    if not parse_date(day):
        return error("Bad date")
    with db.connect() as con:
        con.execute("DELETE FROM closures WHERE day=?", (day,))
    return jsonify({"ok": True})


# ---- frontend -----------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(config.FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path):
    if path.startswith("api/"):
        return error("Not found", 404)
    return send_from_directory(config.FRONTEND_DIR, path, conditional=True)


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


db.init_db()
