"""Collapse duplicate active patient_challenges rows.

For each (patient_id, challenge_id, status='active') combo, keep the
oldest row (smallest id) and delete the rest. Demo cleanup after a
double-tap before the idempotency guard was added."""

from collections import defaultdict

from src.core.database import supabase_client


def main() -> None:
    rows = (
        supabase_client.table("patient_challenges")
        .select("id, patient_id, challenge_id, status")
        .eq("status", "active")
        .order("id")
        .execute()
    )
    groups: dict[tuple[int, int], list[int]] = defaultdict(list)
    for row in rows.data or []:
        groups[(row["patient_id"], row["challenge_id"])].append(row["id"])

    to_delete: list[int] = []
    for key, ids in groups.items():
        if len(ids) <= 1:
            continue
        keep, *dupes = ids
        print(f"patient={key[0]} challenge={key[1]} → keep {keep}, delete {dupes}")
        to_delete.extend(dupes)

    if not to_delete:
        print("no duplicates")
        return

    supabase_client.table("patient_challenges").delete().in_("id", to_delete).execute()
    print(f"deleted {len(to_delete)} duplicate rows")


if __name__ == "__main__":
    main()
