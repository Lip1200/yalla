"""Surface profile insert issues + schema introspection."""

from src.core.database import supabase_client
from src.core.config import settings


def main() -> None:
    print(f"supabase_url        = {settings.supabase_url}")
    print(f"supabase_key starts = {settings.supabase_key[:18]}...")

    print()
    print("=== Inserting minimal doctor profile (age=None) ===")
    payload_min = {
        "id": 9998,
        "auth_user_id": "00000000-0000-0000-0000-000000000998",
        "full_name": "DEBUG MIN",
        "role": "doctor",
        "specialty": "",
        "facility": "",
    }
    try:
        res = supabase_client.table("profiles").insert(payload_min).execute()
        print(f"INSERT OK rowcount={len(res.data or [])}")
    except Exception as exc:
        print(f"INSERT ERR {type(exc).__name__}: {exc!r}")

    print()
    print("=== Inserting with all backend fields ===")
    payload_all = {
        "id": 9999,
        "auth_user_id": "00000000-0000-0000-0000-000000000999",
        "full_name": "DEBUG ALL",
        "role": "doctor",
        "privacy_level": "Donnees limitees",
        "primary_goal": "",
        "weekly_activity_minutes": 0,
        "challenge_completion_rate": 0,
        "activity_completion_rate": 0,
        "has_app_access": True,
        "specialty": "",
        "facility": "",
        "age": 0,
    }
    try:
        res = supabase_client.table("profiles").insert(payload_all).execute()
        print(f"INSERT OK rowcount={len(res.data or [])}")
        print(f"data = {res.data}")
    except Exception as exc:
        print(f"INSERT ERR {type(exc).__name__}: {exc!r}")

    print()
    print("=== Cleanup ===")
    for stale_id in (9998, 9999):
        try:
            supabase_client.table("profiles").delete().eq("id", stale_id).execute()
        except Exception:
            pass
    print("done")


if __name__ == "__main__":
    main()
