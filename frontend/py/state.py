"""Shared page state (one tiny dict instead of globals everywhere)."""
state = {
    "cfg": None,          # /api/config
    "services": [],       # list of service dicts
    "service_map": {},    # id -> service
    "month": None,        # datetime.date for the 1st of the visible month
    "date": None,         # selected "YYYY-MM-DD"
    "time": None,         # selected "HH:MM"
    "slot_labels": {},    # "HH:MM" -> "9:00 AM - 10:00 AM"
}
