"""Small helpers for building and wiring DOM elements from Python."""
import asyncio
import inspect

from pyodide.ffi import create_proxy
from pyscript import document, window


def h(tag, cls="", text=None, children=(), **attrs):
    """Create an element. Text is always set with textContent (never innerHTML) -> no XSS.
    Keyword names use underscores for dashes: data_date="..." -> data-date, aria_label -> aria-label."""
    el = document.createElement(tag)
    if cls:
        el.className = cls
    if text is not None:
        el.textContent = str(text)
    for key, value in attrs.items():
        if value is None or value is False:
            continue
        name = key.rstrip("_").replace("_", "-")
        el.setAttribute(name, "" if value is True else str(value))
    for child in children:
        el.appendChild(child)
    return el


def by_id(element_id):
    return document.getElementById(element_id)


def clear(el):
    el.replaceChildren()


def fill(el, *children):
    el.replaceChildren(*children)


def on(el, event, handler, prevent=False):
    """Attach a handler; async handlers are scheduled automatically.
    prevent=True calls preventDefault() right away (needed for forms: an async handler
    only starts running after the browser has already finished the event)."""
    def wrapper(ev):
        if prevent:
            ev.preventDefault()
        result = handler(ev)
        if inspect.isawaitable(result):
            asyncio.ensure_future(_guard(result))
    el.addEventListener(event, create_proxy(wrapper))


async def _guard(awaitable):
    try:
        await awaitable
    except Exception as exc:  # keep the page alive; details go to the browser console
        print("TechBai error:", repr(exc))


def closest(ev, selector):
    """The ancestor of the event target matching selector (or None)."""
    target = ev.target
    return target.closest(selector) if target else None


def show_alert(el, message, kind="error"):
    el.className = f"alert alert--{kind}"
    el.textContent = message
    el.hidden = False


def hide(el):
    el.hidden = True


def scroll_to(el):
    el.scrollIntoView()


def storage_set(key, value):
    try:
        window.sessionStorage.setItem(key, value)
    except Exception:
        pass
