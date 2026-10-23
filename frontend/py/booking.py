"""Booking panel: time slots, form, validation, confirmation."""
from tb import api, cal
from tb.dom import by_id, closest, fill, h, hide, on, scroll_to, show_alert
from tb.fmt import long_date, peso, time_label
from tb.state import state

FIELD_IDS = {"service_id": "service", "name": "name", "phone": "phone", "email": "email"}
_slots = {"data": None}


# ---------- summary ----------
def _rows(dl, rows):
    parts = []
    for label, value in rows:
        parts.append(h("dt", text=label))
        parts.append(h("dd", "" if value else "is-empty", value or "Not selected"))
    fill(dl, *parts)


def update_summary():
    service = state["service_map"].get(by_id("f-service").value)
    price = ""
    if service:
        price = ("From " if service["from"] else "") + peso(service["price"])
    _rows(by_id("summary"), [
        ("Service", service["name"] if service else ""),
        ("Price", price),
        ("Date", long_date(state["date"]) if state["date"] else ""),
        ("Time", state["slot_labels"].get(state["time"], "") if state["time"] else ""),
    ])


def choose_service(service_id):
    by_id("f-service").value = service_id
    update_summary()


# ---------- slots ----------
def paint_slots():
    data = _slots["data"]
    box, title = by_id("slots-box"), by_id("slots-title")
    if not data:
        return
    title.textContent = "Available times – " + long_date(data["date"])
    if data["day_status"] != "open":
        reason = data.get("reason")
        msg = {"closed": "We're closed on this date." + (f" ({reason})" if reason else ""),
               "past": "This date has already passed."}.get(data["day_status"], "Not available.")
        fill(box, h("p", "alert alert--info", msg))
        return

    def slot_button(s):
        selected = s["time"] == state["time"]
        sub = {"available": "Available", "booked": "Booked", "past": "Passed"}.get(s["state"], "")
        classes = "slot" + (" is-selected" if selected else "")
        return h("button", classes, type="button", data_time=s["time"],
                 disabled=s["state"] != "available", aria_pressed="true" if selected else "false",
                 children=[h("span", text=s["label"]), h("small", text="Selected" if selected else sub)])

    morning = [s for s in data["slots"] if int(s["time"][:2]) < 12]
    afternoon = [s for s in data["slots"] if int(s["time"][:2]) >= 12]
    fill(box,
         h("div", "slot-group-label", "Morning"),
         h("div", "slot-grid", children=[slot_button(s) for s in morning]),
         h("div", "break-row", f"Break {state['cfg']['break']}"),
         h("div", "slot-group-label", "Afternoon"),
         h("div", "slot-grid", children=[slot_button(s) for s in afternoon]))


async def load_slots():
    if not state["date"]:
        return
    status, data = await api.get(f"/api/slots?date={state['date']}")
    if status == 200:
        _slots["data"] = data
        paint_slots()
    else:
        fill(by_id("slots-box"), h("p", "alert alert--error", data.get("error", "Could not load times.")))


async def pick_date(iso):
    state["date"], state["time"] = iso, None
    await cal.render()
    await load_slots()
    update_summary()


def pick_time(ev):
    btn = closest(ev, "button[data-time]")
    if btn and not btn.disabled:
        state["time"] = btn.getAttribute("data-time")
        paint_slots()
        update_summary()


async def refresh_availability():
    """Re-fetch calendar and slots (after a booking is made or cancelled)."""
    await cal.render()
    await load_slots()


# ---------- form ----------
def clear_errors():
    for key, name in FIELD_IDS.items():
        by_id(f"err-{key}").textContent = ""
        by_id(f"fld-{name}").classList.remove("has-error")
    hide(by_id("form-msg"))


def show_field_errors(fields):
    for key, message in fields.items():
        if key in FIELD_IDS:
            by_id(f"err-{key}").textContent = message
            by_id(f"fld-{FIELD_IDS[key]}").classList.add("has-error")


async def submit(ev):
    clear_errors()
    msg = by_id("form-msg")
    if not state["date"] or not state["time"]:
        show_alert(msg, "Please choose a date and a time slot first.")
        return
    body = {"service_id": by_id("f-service").value, "name": by_id("f-name").value.strip(),
            "phone": by_id("f-phone").value.strip(), "email": by_id("f-email").value.strip(),
            "notes": by_id("f-notes").value.strip(), "date": state["date"], "time": state["time"]}
    button = by_id("submit-btn")
    button.disabled, button.textContent = True, "Booking..."
    try:
        status, data = await api.post("/api/bookings", body)
    finally:
        button.disabled, button.textContent = False, "Confirm Booking"

    if status == 201:
        show_success(data)
        await refresh_availability()
    elif status == 422:
        show_field_errors(data.get("fields", {}))
        show_alert(msg, data.get("error", "Please check your details."))
    else:
        show_alert(msg, data.get("error", "Something went wrong."))
        if status == 409:  # slot taken / passed -> show fresh availability
            state["time"] = None
            await refresh_availability()
            update_summary()


def show_success(data):
    by_id("success-ref").textContent = data["ref"]
    _rows(by_id("success-summary"), [
        ("Service", data["service"]),
        ("Date", long_date(data["date"])),
        ("Time", data["label"]),
    ])
    hide(by_id("booking-form"))
    by_id("success").hidden = False
    scroll_to(by_id("form-panel"))


def book_another(_ev):
    for field in ("f-service", "f-notes"):
        by_id(field).value = ""
    state["date"] = state["time"] = None
    by_id("success").hidden = True
    by_id("booking-form").hidden = False
    fill(by_id("slots-box"), h("p", "muted", "Select a date on the calendar to see available times."))
    by_id("slots-title").textContent = "Available times"
    update_summary()
    return cal.render()


async def copy_ref(_ev):
    from pyscript import window
    try:
        await window.navigator.clipboard.writeText(by_id("success-ref").textContent)
        by_id("copy-ref").textContent = "Copied!"
    except Exception:
        by_id("copy-ref").textContent = "Copy failed"


def init():
    state["slot_labels"] = {s["time"]: s["label"] for s in state["cfg"]["slots"]}

    select = by_id("f-service")
    options = [h("option", text="Choose a service...", value="")]
    categories = {}
    for s in state["services"]:
        categories.setdefault(s["category"], []).append(s)
    for category, items in categories.items():
        group = h("optgroup", label=category)
        for s in items:
            group.appendChild(h("option", text=f"{s['name']} – " + ("from " if s["from"] else "") + peso(s["price"]),
                                value=s["id"]))
        options.append(group)
    fill(select, *options)

    on(select, "change", lambda ev: update_summary())
    on(by_id("booking-form"), "submit", submit, prevent=True)
    on(by_id("slots-box"), "click", pick_time)
    on(by_id("book-another"), "click", book_another)
    on(by_id("copy-ref"), "click", copy_ref)
    update_summary()
    by_id("submit-btn").disabled = False  # enabled only once Python is ready
    return cal.init(pick_date)
