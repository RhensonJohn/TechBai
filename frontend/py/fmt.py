"""Formatting helpers (money, dates, times)."""
from datetime import date


def peso(amount):
    return f"₱{int(amount):,}"


def price_text(price, is_from=False):
    return ("From " if is_from else "") + peso(price)


def parse_iso(value):
    y, m, d = (int(x) for x in value.split("-"))
    return date(y, m, d)


def long_date(value):
    d = parse_iso(value) if isinstance(value, str) else value
    return d.strftime("%A, %b ") + str(d.day) + d.strftime(", %Y")


def time_label(hhmm):
    hour, minute = (int(x) for x in hhmm.split(":"))
    suffix = "AM" if hour < 12 else "PM"
    return f"{hour % 12 or 12}:{minute:02d} {suffix}"
