"""Pure scheduling rules (no Flask, no database) so they are easy to test."""
from datetime import date, datetime, time, timedelta

import config


def now_local() -> datetime:
    return datetime.now(config.SHOP_TZ)


def today_local() -> date:
    return now_local().date()


def slot_starts() -> list[time]:
    """Daily slot start times: 9-11 AM, break 11 AM-1 PM, then 1-5 PM."""
    starts = []
    minute = config.OPEN_HOUR * 60
    while minute + config.SLOT_MINUTES <= config.CLOSE_HOUR * 60:
        end = minute + config.SLOT_MINUTES
        in_break = (minute < config.BREAK_END_HOUR * 60
                    and end > config.BREAK_START_HOUR * 60)
        if not in_break:
            starts.append(time(minute // 60, minute % 60))
        minute = end
    return starts


def fmt12(t: time) -> str:
    hour = t.hour % 12 or 12
    return f"{hour}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def slot_label(start: time) -> str:
    end = (datetime.combine(date.today(), start)
           + timedelta(minutes=config.SLOT_MINUTES)).time()
    return f"{fmt12(start)} - {fmt12(end)}"


def all_slots() -> list[dict]:
    return [{"time": t.strftime("%H:%M"), "label": slot_label(t)} for t in slot_starts()]


def valid_slot(value: str) -> bool:
    return value in {s["time"] for s in all_slots()}


def day_status(day: date, closed: bool = False, now: datetime | None = None) -> str:
    """'open', 'closed' or 'past' (ignores how many slots are taken)."""
    now = now or now_local()
    if day < now.date():
        return "past"
    if closed or day.weekday() not in config.OPEN_WEEKDAYS:
        return "closed"
    if day > now.date() + timedelta(days=config.BOOKING_WINDOW_DAYS):
        return "closed"
    return "open"


def slot_is_past(day: date, start: time, now: datetime | None = None) -> bool:
    now = now or now_local()
    begins = datetime.combine(day, start, tzinfo=config.SHOP_TZ)
    return begins < now + timedelta(minutes=config.MIN_LEAD_MINUTES)
