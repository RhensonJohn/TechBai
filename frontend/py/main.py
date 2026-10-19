"""Entry point for index.html (PyScript runs this file)."""
import asyncio

from tb import api, booking, lookup, nav, services
from tb.dom import by_id, fill, h
from tb.state import state


async def start():
    nav.init()
    (s1, cfg), (s2, svc) = await asyncio.gather(api.get("/api/config"), api.get("/api/services"))
    if s1 != 200 or s2 != 200:
        error = h("p", "alert alert--error", "We couldn't load the booking system. Please refresh the page.")
        fill(by_id("service-grid"), error)
        return
    state["cfg"] = cfg
    state["services"] = svc["services"]
    state["service_map"] = {s["id"]: s for s in svc["services"]}

    services.init()
    lookup.init()
    await booking.init()


asyncio.ensure_future(start())
