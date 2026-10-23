"""Talk to the Flask backend. Every call returns (http_status, json_dict)."""
import json

from pyodide.http import pyfetch

OFFLINE = {"error": "Can't reach the server. Check your connection and try again."}


async def request(method, url, body=None, headers=None):
    options = {"method": method, "headers": {"Content-Type": "application/json", **(headers or {})}}
    if body is not None:
        options["body"] = json.dumps(body)
    try:
        response = await pyfetch(url, **options)
    except Exception:
        return 0, dict(OFFLINE)
    try:
        data = await response.json()
    except Exception:
        data = {"error": "Unexpected response from the server."}
    return response.status, data


async def get(url, headers=None):
    return await request("GET", url, headers=headers)


async def post(url, body, headers=None):
    return await request("POST", url, body, headers)


async def delete(url, headers=None):
    return await request("DELETE", url, headers=headers)
