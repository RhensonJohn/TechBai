"""Staff dashboard logic."""
from tb import api
from tb.dom import by_id, closest, fill, h, hide, on, show_alert
from tb.fmt import long_date, peso, time_label

auth = {"token": ""}


def headers():
    return {"X-Admin-Token": auth["token"]}


def stats(bookings):
    counts = {k: 0 for k in ("booked", "completed", "cancelled", "no_show")}
    for b in bookings:
        counts[b["status"]] += 1
    items = [("Shown", len(bookings)), ("Booked", counts["booked"]), ("Completed", counts["completed"]),
             ("Cancelled", counts["cancelled"]), ("No show", counts["no_show"])]
    fill(by_id("stats"), *[h("div", "stat", children=[h("b", text=n), h("span", text=label)]) for label, n in items])


def status_select(b):
    select = h("select", aria_label=f"Status for {b['ref']}", data_id=b["id"])
    for value in ("booked", "completed", "cancelled", "no_show"):
        option = h("option", text=value.replace("_", " ").title(), value=value)
        if value == b["status"]:
            option.selected = True
        select.appendChild(option)
    return select


def table(bookings):
    if not bookings:
        return h("div", "empty", "No bookings found.")
    head = h("tr", children=[h("th", text=t) for t in ("Date", "Time", "Customer", "Service", "Notes", "Status", "Ref")])
    rows = [head]
    for b in bookings:
        contact = [h("b", text=b["name"]), h("br"), h("span", text=b["phone"])]
        if b["email"]:
            contact += [h("br"), h("span", "muted", b["email"])]
        rows.append(h("tr", children=[
            h("td", text=long_date(b["booking_date"])),
            h("td", text=time_label(b["booking_time"])),
            h("td", children=contact),
            h("td", text=f"{b['service_name']} ({'from ' if b['price_from'] else ''}{peso(b['price'])})"),
            h("td", "notes-cell", b["notes"] or "-"),
            h("td", children=[status_select(b)]),
            h("td", text=b["ref"]),
        ]))
    return h("table", "data", children=rows)


def closures(items):
    fill(by_id("closure-list"), *[
        h("li", children=[h("span", text=f"{long_date(c['day'])}" + (f" – {c['reason']}" if c["reason"] else "")),
                          h("button", "btn btn--danger btn--small", "Reopen", type="button", data_day=c["day"])])
        for c in items])


async def load():
    query = []
    if by_id("a-date").value:
        query.append("date=" + by_id("a-date").value)
    if by_id("a-status").value:
        query.append("status=" + by_id("a-status").value)
    status, data = await api.get("/api/admin/bookings" + ("?" + "&".join(query) if query else ""), headers())
    msg = by_id("admin-msg")
    if status != 200:
        show_alert(msg, data.get("error", "Could not load bookings."))
        if status == 401:
            logout(None)
        return False
    hide(msg)
    stats(data["bookings"])
    fill(by_id("bookings-box"), table(data["bookings"]))
    closures(data["closures"])
    return True


async def login(ev):
    auth["token"] = by_id("a-pass").value
    msg = by_id("login-msg")
    status, data = await api.get("/api/admin/bookings", headers())
    if status != 200:
        auth["token"] = ""
        show_alert(msg, data.get("error", "Login failed."))
        return
    hide(msg)
    by_id("a-pass").value = ""
    by_id("login-form").hidden = True
    by_id("dashboard").hidden = False
    by_id("logout-btn").hidden = False
    await load()


def logout(_ev):
    auth["token"] = ""
    by_id("dashboard").hidden = True
    by_id("logout-btn").hidden = True
    by_id("login-form").hidden = False


async def change_status(ev):
    select = closest(ev, "select[data-id]")
    if not select:
        return
    status, data = await api.post(f"/api/admin/bookings/{select.getAttribute('data-id')}/status",
                                  {"status": select.value}, headers())
    if status != 200:
        show_alert(by_id("admin-msg"), data.get("error", "Could not update."))
    await load()


async def add_closure(ev):
    status, data = await api.post("/api/admin/closures", {"date": by_id("c-date").value,
                                                          "reason": by_id("c-reason").value.strip()}, headers())
    if status == 200:
        by_id("c-date").value = by_id("c-reason").value = ""
        await load()
    else:
        show_alert(by_id("admin-msg"), data.get("error", "Could not close that date."))


async def remove_closure(ev):
    btn = closest(ev, "button[data-day]")
    if btn:
        await api.delete("/api/admin/closures/" + btn.getAttribute("data-day"), headers())
        await load()


def clear_filters(_ev):
    by_id("a-date").value = ""
    by_id("a-status").value = ""
    return load()


def init():
    by_id("login-btn").disabled = False
    on(by_id("login-form"), "submit", login, prevent=True)
    on(by_id("logout-btn"), "click", logout)
    on(by_id("a-date"), "change", lambda ev: load())
    on(by_id("a-status"), "change", lambda ev: load())
    on(by_id("a-refresh"), "click", lambda ev: load())
    on(by_id("a-clear"), "click", clear_filters)
    on(by_id("bookings-box"), "change", change_status)
    on(by_id("closure-form"), "submit", add_closure, prevent=True)
    on(by_id("closure-list"), "click", remove_closure)
