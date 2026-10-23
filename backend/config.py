"""TechBai settings. Change shop hours, slots and limits here - nowhere else."""
import os
from datetime import timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
# Database: set DATABASE_URL (or POSTGRES_URL) to use Postgres - needed on Vercel, whose disk is
# temporary. Without it the app uses the local SQLite file below (fine for your own computer).
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
DB_PATH = Path(os.environ.get("TECHBAI_DB", BASE_DIR / "techbai.db"))
SERVICES_FILE = BASE_DIR / "services.json"

# Philippine time (UTC+8, no daylight saving) - all schedule logic uses this.
SHOP_TZ = timezone(timedelta(hours=8))

# ---- Booking schedule -------------------------------------------------
OPEN_HOUR = 9            # first slot starts 9:00 AM
BREAK_START_HOUR = 11    # break starts 11:00 AM ...
BREAK_END_HOUR = 13      # ... until 1:00 PM
CLOSE_HOUR = 17          # last slot ends 5:00 PM
SLOT_MINUTES = 60
SLOT_CAPACITY = 1        # bookings allowed per slot (= technicians working at once)
OPEN_WEEKDAYS = {0, 1, 2, 3, 4, 5}   # Mon=0 ... Sun=6  (closed on Sunday)
BOOKING_WINDOW_DAYS = 60  # how far ahead customers may book
MIN_LEAD_MINUTES = 60     # same-day bookings must start at least this far ahead

# ---- Security ---------------------------------------------------------
# Set ADMIN_PASSWORD in the environment. If missing, a random one is generated
# at startup and printed to the console (see app.py).
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
BOOKINGS_PER_IP_PER_HOUR = 10
# Behind a proxy (Vercel) the real visitor IP is in a header. Only trust it when hosted there.
TRUST_PROXY = bool(os.environ.get("VERCEL") or os.environ.get("TRUST_PROXY"))
