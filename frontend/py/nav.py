"""Mobile menu toggle."""
from tb.dom import by_id, closest, on


def init():
    toggle, menu = by_id("nav-toggle"), by_id("site-nav")

    def flip(_ev):
        opened = menu.classList.toggle("is-open")
        toggle.setAttribute("aria-expanded", "true" if opened else "false")

    def close_on_link(ev):
        if closest(ev, "a"):
            menu.classList.remove("is-open")
            toggle.setAttribute("aria-expanded", "false")

    on(toggle, "click", flip)
    on(menu, "click", close_on_link)
