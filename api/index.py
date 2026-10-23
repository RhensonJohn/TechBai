"""Vercel entry point: Vercel looks for a WSGI object called `app` in api/*.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app import app  # noqa: E402,F401
