"""TechBai settings. Change shop hours, slots and limits here - nowhere else."""
import os
from datetime import timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
# Database: when a Postgres address is set, the app uses Postgres - needed on Vercel, whose disk is
# temporary. Without one it uses the local SQLite file below (fine for your own computer).
def _find_database_url() -> str:
    """DATABASE_URL / POSTGRES_URL, or any variable holding a postgres:// address (Vercel's Neon
    setup may add a prefix such as STORAGE_URL). Pooled addresses are preferred on serverless."""
    for name in ("DATABASE_URL", "POSTGRES_URL"):
        if os.environ.get(name, "").startswith(("postgres://", "postgresql://")):
            return os.environ[name]
    found = [(k, v) for k, v in os.environ.items() if v.startswith(("postgres://", "postgresql://"))]
    found.sort(key=lambda kv: (any(bad in kv[0] for bad in ("UNPOOLED", "NON_POOLING", "NO_SSL", "PRISMA")), kv[0]))
    return found[0][1] if found else ""


DATABASE_URL = _find_database_url()
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
