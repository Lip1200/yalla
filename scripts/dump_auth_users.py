"""List every auth user + show which ones have a linked profile."""

from src.core.database import supabase_client


def main() -> None:
    resp = supabase_client.auth.admin.list_users()
    users = resp if isinstance(resp, list) else getattr(resp, "users", None) or []
    profs = (
        supabase_client.table("profiles")
        .select("id, full_name, role, auth_user_id")
        .execute()
        .data
        or []
    )
    profile_by_uid = {p["auth_user_id"]: p for p in profs if p.get("auth_user_id")}

    print(f"{len(users)} auth users\n")
    for u in users:
        meta = u.user_metadata or {}
        role = meta.get("role", "?")
        prof = profile_by_uid.get(str(u.id))
        prof_str = f"profile {prof['id']} ({prof['role']})" if prof else "** NO PROFILE LINKED **"
        print(f"  {u.id}  {u.email!r:<35}  metadata.role={role!r:<18}  {prof_str}")


if __name__ == "__main__":
    main()
