# TechBai

Online booking system for TechBai's PC & mobile repair, troubleshooting, deep cleaning, PC building and Wi-Fi services.
Academic project by Rhenson John Dela Cruz, John Carlo Ortega, Justin Abendan and Jerome Lee Manosor.

## Run it

```bash
pip install -r requirements.txt
ADMIN_PASSWORD="choose-a-password" python main.py     # Windows PowerShell: $env:ADMIN_PASSWORD="..."; python main.py
```
Open http://localhost:5000 (customers) and http://localhost:5000/admin.html (staff).
If `ADMIN_PASSWORD` is not set, a random one is printed in the console each run.
The browser needs internet to load PyScript from the jsDelivr CDN.

## Deploy
See **DEPLOY.md** (Vercel + free Postgres).

## Structure

```
main.py                 start the server locally
api/index.py            Vercel entry point
vercel.json             Vercel settings
DEPLOY.md               how to put it online
backend/                Flask + SQLite API
  config.py             opening hours, break, slot length, capacity, closed days (edit here)
  services.json         services and prices (edit here)
  schedule.py           slot rules (9-11 AM, break 11 AM-1 PM, 1-5 PM)
  database.py, app.py   storage (SQLite locally, Postgres when DATABASE_URL is set) and endpoints
frontend/
  index.html            customer site (video, services, booking, find/cancel booking)
  admin.html            staff dashboard
  css/                  base, layout, components, booking, admin
  py/                   PyScript modules (api, dom, calendar, booking, lookup, admin ...)
  pyscript.toml         tells PyScript which Python files to load
  assets/               logo, promo video (compressed), poster
tests/test_backend.py   run: pytest tests
```

## Rules built in
- Slots (1 hour): 9-10, 10-11, 1-2, 2-3, 3-4, 4-5. Nothing bookable 11 AM-1 PM.
- Open Mon-Sat (change `OPEN_WEEKDAYS`); bookings up to 60 days ahead; same-day slots need 60 min notice.
- One booking per slot (`SLOT_CAPACITY`); double booking is blocked in the database transaction.
- Customers get a code like `TB-7K2M9Q`; code + mobile number lets them view or cancel.
- Staff can mark bookings completed / no show / cancelled and close holidays.
