"""Dump current profiles + their auth_user_id links."""

from src.core.database import supabase_client


def main() -> None:
    profiles = (
        supabase_client.table("profiles")
        .select("id, full_name, role, auth_user_id")
        .order("id")
        .execute()
    )
    print(f"{'id':<6} {'role':<14} {'full_name':<35} auth_user_id")
    print("-" * 90)
    for row in profiles.data:
        print(
            f"{row['id']:<6} "
            f"{(row.get('role') or '').ljust(14)[:14]} "
            f"{(row.get('full_name') or '').ljust(35)[:35]} "
            f"{row.get('auth_user_id') or '-'}"
        )


if __name__ == "__main__":
    main()
