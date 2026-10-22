import os
import sys
import tempfile
from datetime import timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ["TECHBAI_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["ADMIN_PASSWORD"] = "secret-pw"

import app as backend  # noqa: E402
import schedule  # noqa: E402


@pytest.fixture()
def client():
    backend._hits.clear()
    return backend.app.test_client()


def next_open_day(offset=2):
    d = schedule.today_local() + timedelta(days=offset)
    while d.weekday() == 6:
        d += timedelta(days=1)
    return d


def payload(day, time="09:00", **kw):
    base = {"name": "Juan Dela Cruz", "phone": "0917 123 4567", "service_id": "ts-pc",
            "date": day.isoformat(), "time": time, "notes": "slow PC"}
    return {**base, **kw}


def test_slots_follow_shop_hours():
    times = [s["time"] for s in schedule.all_slots()]
    assert times == ["09:00", "10:00", "13:00", "14:00", "15:00", "16:00"]
    assert "11:00" not in times and "12:00" not in times


def test_labels():
    labels = [s["label"] for s in schedule.all_slots()]
    assert labels[0] == "9:00 AM - 10:00 AM" and labels[-1] == "4:00 PM - 5:00 PM"


def test_services_complete(client):
    s = client.get("/api/services").get_json()["services"]
    cats = {x["category"] for x in s}
    assert cats == {"Troubleshooting", "Deep Cleaning", "Building PC", "Repair", "Wi-Fi Configuration"}
    assert len(s) == 8


def test_book_and_double_book(client):
    day = next_open_day()
    r = client.post("/api/bookings", json=payload(day))
    assert r.status_code == 201 and r.get_json()["ref"].startswith("TB-")
    r2 = client.post("/api/bookings", json=payload(day, name="Maria Santos"))
    assert r2.status_code == 409
    slots = client.get(f"/api/slots?date={day}").get_json()["slots"]
    assert slots[0]["state"] == "booked" and slots[1]["state"] == "available"


def test_rejects_break_hours_and_bad_input(client):
    day = next_open_day()
    assert client.post("/api/bookings", json=payload(day, time="11:00")).status_code == 422
    assert client.post("/api/bookings", json=payload(day, time="12:00")).status_code == 422
    assert client.post("/api/bookings", json=payload(day, service_id="nope")).status_code == 422
    assert client.post("/api/bookings", json=payload(day, name="A")).status_code == 422
    assert client.post("/api/bookings", json=payload(day, phone="12")).status_code == 422
    assert client.post("/api/bookings", json=payload(day, email="bad")).status_code == 422
    assert client.post("/api/bookings", data="x").status_code == 400


def test_sunday_past_and_far_future_rejected(client):
    d = schedule.today_local()
    while d.weekday() != 6:
        d += timedelta(days=1)
    assert client.post("/api/bookings", json=payload(d)).status_code == 409
    past = schedule.today_local() - timedelta(days=1)
    assert client.post("/api/bookings", json=payload(past)).status_code == 409
    far = schedule.today_local() + timedelta(days=400)
    assert client.post("/api/bookings", json=payload(far)).status_code == 409


def test_lookup_cancel_frees_slot(client):
    day = next_open_day(5)
    ref = client.post("/api/bookings", json=payload(day, "14:00")).get_json()["ref"]
    assert client.post("/api/bookings/lookup", json={"ref": ref, "phone": "0000"}).status_code == 404
    r = client.post("/api/bookings/lookup", json={"ref": ref.lower(), "phone": "+63 917 123 4567"})
    assert r.status_code == 200 and r.get_json()["booking_time"] == "14:00"
    assert client.post("/api/bookings/cancel", json={"ref": ref, "phone": "09171234567"}).status_code == 200
    assert client.post("/api/bookings/cancel", json={"ref": ref, "phone": "09171234567"}).status_code == 409
    assert client.post("/api/bookings", json=payload(day, "14:00")).status_code == 201


def test_availability_month(client):
    day = next_open_day(3)
    month = day.strftime("%Y-%m")
    data = client.get(f"/api/availability?month={month}").get_json()["days"]
    assert data[day.isoformat()]["total"] == 6
    sundays = [k for k in data if schedule.date.fromisoformat(k).weekday() == 6]
    assert all(data[k]["status"] in ("closed", "past") for k in sundays)
    assert client.get("/api/availability?month=bad").status_code == 400


def test_full_day_and_closure(client):
    day = next_open_day(9)
    for s in schedule.all_slots():
        assert client.post("/api/bookings", json=payload(day, s["time"])).status_code == 201
        backend._hits.clear()
    m = client.get(f"/api/availability?month={day.strftime('%Y-%m')}").get_json()["days"]
    assert m[day.isoformat()]["status"] == "full"
    day2 = next_open_day(10)
    h = {"X-Admin-Token": "secret-pw"}
    assert client.post("/api/admin/closures", json={"date": day2.isoformat(), "reason": "Holiday"}, headers=h).status_code == 200
    assert client.post("/api/bookings", json=payload(day2)).status_code == 409
    assert client.delete(f"/api/admin/closures/{day2}", headers=h).status_code == 200


def test_admin_auth_and_status(client):
    assert client.get("/api/admin/bookings").status_code == 401
    assert client.get("/api/admin/bookings", headers={"X-Admin-Token": "x"}).status_code == 401
    h = {"X-Admin-Token": "secret-pw"}
    r = client.get("/api/admin/bookings", headers=h).get_json()["bookings"]
    assert r
    bid = r[0]["id"]
    assert client.post(f"/api/admin/bookings/{bid}/status", json={"status": "completed"}, headers=h).status_code == 200
    assert client.post(f"/api/admin/bookings/{bid}/status", json={"status": "zzz"}, headers=h).status_code == 400


def test_static_and_traversal(client):
    assert client.get("/api/unknown").status_code == 404
    assert client.get("/../backend/app.py").status_code in (400, 404)
    assert client.get("/%2e%2e/backend/app.py").status_code == 404
