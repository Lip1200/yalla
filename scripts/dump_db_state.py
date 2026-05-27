"""Print row counts + a few sample rows from every important table,
so we can decide what to seed."""

from src.core.database import supabase_client


def main() -> None:
    tables = [
        ("profiles", "id, full_name, role"),
        ("challenges", "id, title, category, target_value, target_unit, duration_days"),
        ("patient_challenges", "id, patient_id, challenge_id, status, progress"),
        ("feed_posts", "id, author_id, type, created_at"),
        ("feed_post_supports", "post_id, user_id"),
        ("groups", "id, name, category, creator_id, member_count"),
        ("group_members", "group_id, user_id, role"),
        ("badges", "id, code, label"),
        ("patient_badges", "id, patient_id, badge_id, earned_at"),
        ("messages", "id, conversation_id, sender_id, content"),
    ]
    for table, cols in tables:
        try:
            resp = supabase_client.table(table).select(cols).order("id" if "id" in cols.split(",")[0].strip() else cols.split(",")[0].strip()).execute()
            rows = resp.data or []
            print(f"\n=== {table} ({len(rows)} rows) ===")
            for row in rows[:5]:
                print(f"  {row}")
            if len(rows) > 5:
                print(f"  ... and {len(rows) - 5} more")
        except Exception as exc:
            print(f"\n=== {table} ===  ERR {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
