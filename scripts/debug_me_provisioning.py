"""Reproduce /me's auto-provision path for an existing auth user that
has no profiles row, surfacing whatever silently fails."""

import sys

from src.core.database import supabase_client
from src.modules.auth.service import _ensure_profile_for_auth_user

if len(sys.argv) < 2:
    print("usage: python debug_me_provisioning.py <auth_user_id_uuid>")
    sys.exit(1)

uid = sys.argv[1]
print(f"=== probing auth user {uid} ===")

# 1. Can we list auth users at all (service-role required)?
try:
    admin_resp = supabase_client.auth.admin.get_user_by_id(uid)
    print(f"admin.get_user_by_id type: {type(admin_resp).__name__}")
    user = getattr(admin_resp, "user", None)
    print(f"  user: {user}")
    if user is not None:
        print(f"  metadata: {getattr(user, 'user_metadata', None)}")
        print(f"  email: {getattr(user, 'email', None)}")
except Exception as exc:
    print(f"admin.get_user_by_id ERR {type(exc).__name__}: {exc!r}")
    user = None

# 2. Does the profile already exist?
sel = (
    supabase_client.table("profiles")
    .select("id, auth_user_id, full_name, role")
    .eq("auth_user_id", uid)
    .execute()
)
print(f"=== current profiles row ===\n  {sel.data}")

# 3. Try ensure
if user is not None:
    metadata = getattr(user, "user_metadata", None) or {}
    full_name = metadata.get("full_name") or getattr(user, "email", None) or "Patient Yalla"
    print(f"=== running _ensure_profile_for_auth_user(name='{full_name}') ===")
    try:
        _ensure_profile_for_auth_user(user, full_name)
        print("  done")
    except Exception as exc:
        print(f"  ERR {type(exc).__name__}: {exc!r}")

# 4. Re-check
sel2 = (
    supabase_client.table("profiles")
    .select("id, auth_user_id, full_name, role")
    .eq("auth_user_id", uid)
    .execute()
)
print(f"=== profiles row after provisioning ===\n  {sel2.data}")
