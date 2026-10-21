"""Services & prices section + filter chips."""
from tb import booking
from tb.dom import by_id, closest, fill, h, on, scroll_to
from tb.fmt import peso
from tb.state import state

current = {"category": "All"}


def render():
    categories = ["All"]
    for s in state["services"]:
        if s["category"] not in categories:
            categories.append(s["category"])

    chips = by_id("service-filters")
    fill(chips, *[
        h("button", "chip", name, type="button", data_category=name,
          aria_pressed="true" if name == current["category"] else "false")
        for name in categories])

    cards = []
    for s in state["services"]:
        if current["category"] not in ("All", s["category"]):
            continue
        price = h("div", "price")
        if s["from"]:
            price.appendChild(h("small", text="from"))
        price.appendChild(h("span", text=peso(s["price"])))
        cards.append(h("article", "service-card", children=[
            h("div", "service-meta", children=[h("span", "badge", s["category"]),
                                               h("span", "badge badge--device", s["device"])]),
            h("h3", text=s["name"]),
            h("p", text=s["description"]),
            h("div", "service-foot", children=[
                price,
                h("button", "btn btn--dark btn--small", "Book this", type="button", data_service=s["id"])]),
        ]))
    fill(by_id("service-grid"), *cards)


def init():
    render()

    def on_chip(ev):
        chip = closest(ev, ".chip")
        if chip:
            current["category"] = chip.getAttribute("data-category")
            render()

    def on_book(ev):
        btn = closest(ev, "[data-service]")
        if btn:
            booking.choose_service(btn.getAttribute("data-service"))
            scroll_to(by_id("booking"))

    on(by_id("service-filters"), "click", on_chip)
    on(by_id("service-grid"), "click", on_book)
