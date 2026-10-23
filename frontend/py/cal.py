"""Month calendar with live availability from the backend."""
from datetime import date, timedelta

from tb import api
from tb.dom import by_id, closest, fill, h, on
from tb.fmt import parse_iso
from tb.state import state

_request_id = {"n": 0}  # ignore out-of-date responses when clicking months quickly
_on_pick = {"fn": None}


def _month_start(d):
    return d.replace(day=1)


def _shift(first, months):
    index = first.year * 12 + (first.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def _update_nav():
    today = parse_iso(state["cfg"]["today"])
    last = parse_iso(state["cfg"]["max_date"])
    by_id("cal-prev").disabled = state["month"] <= _month_start(today)
    by_id("cal-next").disabled = _shift(state["month"], 1) > _month_start(last)


async def render():
    _request_id["n"] += 1
    mine = _request_id["n"]
    first = state["month"]
    by_id("cal-title").textContent = first.strftime("%B %Y")
    _update_nav()

    status, data = await api.get(f"/api/availability?month={first.strftime('%Y-%m')}")
    if mine != _request_id["n"]:
        return
    grid = by_id("cal-grid")
    if status != 200:
        fill(grid, h("p", "alert alert--error", data.get("error", "Could not load calendar.")))
        return

    cells = [h("div", "cal-dow", name) for name in ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")]
    cells += [h("div", "cal-blank") for _ in range((first.weekday() + 1) % 7)]

    today_iso = state["cfg"]["today"]
    day = first
    while day.month == first.month:
        iso = day.isoformat()
        info = data["days"][iso]
        kind = info["status"]
        if kind == "open" and info["free"] <= 2:
            kind = "limited"
        classes = f"day day--{kind}"
        if iso == today_iso:
            classes += " is-today"
        if iso == state["date"]:
            classes += " is-selected"
        small = {"open": f"{info['free']} open", "limited": f"{info['free']} left",
                 "full": "Full", "closed": "Closed", "past": ""}[kind]
        selectable = kind in ("open", "limited")
        label = f"{day.strftime('%A, %B')} {day.day}: " + (f"{info['free']} slots available" if selectable else kind)
        cells.append(h("button", classes, type="button", data_date=iso, disabled=not selectable,
                       aria_label=label, aria_pressed="true" if iso == state["date"] else "false",
                       children=[h("span", text=day.day), h("small", text=small)]))
        day += timedelta(days=1)
    fill(grid, *cells)


def init(on_pick):
    _on_pick["fn"] = on_pick
    state["month"] = _month_start(parse_iso(state["cfg"]["today"]))

    async def change(delta):
        state["month"] = _shift(state["month"], delta)
        await render()

    async def pick(ev):
        btn = closest(ev, "button[data-date]")
        if btn and not btn.disabled:
            await _on_pick["fn"](btn.getAttribute("data-date"))

    on(by_id("cal-prev"), "click", lambda ev: change(-1))
    on(by_id("cal-next"), "click", lambda ev: change(1))
    on(by_id("cal-grid"), "click", pick)
    return render()
