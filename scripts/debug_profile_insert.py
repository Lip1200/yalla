"""Manually trigger the profile-insert codepath to surface whatever the
silent try/except in _ensure_profile_for_auth_user is hiding.

Usage (from inside the backend container):
    docker compose exec backend python /app/scripts/debug_profile_insert.py
"""

from src.core.database import supabase_client
from src.core.config import settings


def main() -> None:
    print("=== Sanity checks ===")
    print(f"supabase_url        = {settings.supabase_url}")
    print(f"supabase_key starts = {settings.supabase_key[:18]}...")
    print()

    print("=== Probing profiles SELECT (max id) ===")
    try:
        sel = (
            supabase_client.table("profiles")
            .select("id")
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        print(f"max id row = {sel.data}")
    except Exception as exc:
        print(f"SELECT ERR {type(exc).__name__}: {exc!r}")
        return

    print()
    print("=== Probing INSERT with all fields ===")
    payload = {
        "id": 9999,
        "auth_user_id": "00000000-0000-0000-0000-000000000999",
        "full_name": "DEBUG INSERT",
        "role": "doctor",
        "privacy_level": "Donnees limitees",
        "primary_goal": "",
        "weekly_activity_minutes": 0,
        "challenge_completion_rate": 0,
        "activity_completion_rate": 0,
        "has_app_access": True,
        "specialty": "",
        "facility": "",
    }
    try:
        res = supabase_client.table("profiles").insert(payload).execute()
        print(f"INSERT OK rowcount={len(res.data or [])}")
        print(f"INSERT data    = {res.data}")
    except Exception as exc:
        print(f"INSERT ERR {type(exc).__name__}: {exc!r}")
        return

    print()
    print("=== Cleanup ===")
    try:
        supabase_client.table("profiles").delete().eq("id", 9999).execute()
        print("cleanup OK (test row removed)")
    except Exception as exc:
        print(f"cleanup ERR {type(exc).__name__}: {exc!r}")


if __name__ == "__main__":
    main()
