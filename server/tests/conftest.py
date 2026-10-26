"""Test environment.

Set before any app import, because app.core.config reads the environment at
import time and raises if DATABASE_URL is missing. SQLite keeps the unit
tests runnable without Postgres; anything that needs real Postgres behaviour
belongs in the API tests run against the compose stack (TEST_DATABASE_URL).
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

# A fresh database for every test run. A fixed file in the temp folder kept
# accounts from the previous run, so tests that sign up fixed emails failed
# with 409 on every run after the first.
_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="handshake_test_"))
atexit.register(shutil.rmtree, _TEST_DB_DIR, ignore_errors=True)

# The tests always run against their own throwaway SQLite database, never the
# DATABASE_URL in the container (that is the live Postgres with your demo
# data), and never against a real model. Set TEST_DATABASE_URL to run them
# on another database on purpose.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_TEST_DB_DIR / 'handshake_test.db'}"
# Forced, not defaulted: a developer's .env must not change what the tests see.
os.environ["DEMO_TAMPER_ENABLED"] = "true"
os.environ["LLM_CACHE_ENABLED"] = "true"
os.environ["GROQ_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
