"""Confirm hypothesis: does auth.get_user(token) mutate the postgrest
client's headers? Get a fresh Tefa JWT via login, then check headers
before/after the get_user call."""

import json
import urllib.request
import urllib.error

from src.core.config import settings
from src.core.database import supabase_client


def query_rows() -> int:
    r = (
        supabase_client.table("profiles")
        .select("id, auth_user_id, full_name")
        .eq("auth_user_id", "44cf4977-732f-428e-a763-396559e2d789")
        .execute()
    )
    return len(r.data or [])


def show_headers(tag: str) -> None:
    session = supabase_client.postgrest.session
    auth = (session.headers.get("Authorization") or "")[:30]
    apikey = (session.headers.get("apikey") or "")[:30]
    print(f"  [{tag}] Authorization={auth!r}  apikey={apikey!r}  rows={query_rows()}")


show_headers("baseline")

# Mint a fresh Tefa JWT via the auth login endpoint
print("\n=== signing in as tefa ===")
url = f"{settings.supabase_url}/auth/v1/token?grant_type=password"
body = json.dumps({"email": "tefa@gmail.com", "password": "PASSWORD_PLACEHOLDER"}).encode()
req = urllib.request.Request(
    url,
    data=body,
    headers={
        "Content-Type": "application/json",
        "apikey": settings.supabase_key,
    },
)
try:
    resp = urllib.request.urlopen(req)
    payload = json.loads(resp.read())
    jwt = payload.get("access_token")
    print(f"  jwt acquired ({len(jwt)} chars)")
except urllib.error.HTTPError as exc:
    print(f"  login HTTP {exc.code}: {exc.read()!r}")
    print("  → set PASSWORD_PLACEHOLDER above to a real value before running")
    raise SystemExit(1)

show_headers("after login HTTP call")

print("\n=== calling supabase_client.auth.get_user(jwt) ===")
try:
    user_resp = supabase_client.auth.get_user(jwt)
    print(f"  user.id={user_resp.user.id}")
except Exception as exc:
    print(f"  ERR {type(exc).__name__}: {exc!r}")

show_headers("after auth.get_user")
