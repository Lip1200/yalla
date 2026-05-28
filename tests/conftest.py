"""Shared pytest fixtures.

We test against an in-process FastAPI TestClient with the Supabase
client patched at the module boundary — we don't want unit/integration
runs to hit the real cloud DB. Each integration test rebuilds a small
in-memory store keyed by table name + row id so the assertions read
from the same data the request handler wrote.
"""

import os

# Provide minimal Supabase config before src.* imports happen, otherwise
# `from src.core.config import settings` would fail on the missing
# SUPABASE_URL / SUPABASE_KEY env vars.
os.environ.setdefault("SUPABASE_URL", "http://test.invalid")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("API_SECRET_TOKEN", "test-secret")

import pytest
