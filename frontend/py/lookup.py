"""'Find my booking' + cancel."""
from pyscript import window

from tb import api, booking
from tb.dom import by_id, closest, fill, h, on
from tb.fmt import long_date, price_text, time_label

_last = {"ref": "", "phone": ""}


def _row(label, value):
    return [h("dt", text=label), h("dd", text=value)]


def render(b):
    rows = []
    for label, value in (("Reference", b["ref"]), ("Name", b["name"]), ("Service", b["service_name"]),
                         ("Price", price_text(b["price"], b["price_from"])),
                         ("Date", long_date(b["booking_date"])),
                         ("Time", time_label(b["booking_time"]))):
        rows += _row(label, value)
    status = b["status"]
    pill = h("span", f"status-pill status-{status}", status.replace("_", " "))
    kids = [h("h3", children=[h("span", text="Your booking  "), pill]),
            h("div", "summary", children=[h("dl", children=rows)])]
    if b.get("notes"):
        kids.append(h("p", "muted", "Notes: " + b["notes"]))
    if status == "booked":
        kids.append(h("button", "btn btn--danger btn--small", "Cancel this booking", type="button", id="cancel-btn"))
    fill(by_id("lookup-result"), h("div", "panel", children=kids))


def message(text, kind="error"):
    fill(by_id("lookup-result"), h("div", f"alert alert--{kind}", text))


async def find(ev):
    ref, phone = by_id("l-ref").value.strip(), by_id("l-phone").value.strip()
    if not ref or not phone:
        message("Please enter both the reference code and your mobile number.")
        return
    status, data = await api.post("/api/bookings/lookup", {"ref": ref, "phone": phone})
    if status == 200:
        _last.update(ref=ref, phone=phone)
        render(data)
    else:
        message(data.get("error", "Could not find that booking."))


async def cancel(ev):
    if not closest(ev, "#cancel-btn"):
        return
    if not window.confirm("Cancel this booking? This frees the time slot for others."):
        return
    status, data = await api.post("/api/bookings/cancel", _last)
    if status == 200:
        s2, b = await api.post("/api/bookings/lookup", _last)
        if s2 == 200:
            render(b)
        await booking.refresh_availability()
    else:
        message(data.get("error", "Could not cancel."))


def init():
    by_id("lookup-btn").disabled = False
    on(by_id("lookup-form"), "submit", find, prevent=True)
    on(by_id("lookup-result"), "click", cancel)
