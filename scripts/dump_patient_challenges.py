"""Show all active patient_challenges rows with patient name + challenge title."""

from src.core.database import supabase_client


def main() -> None:
    rows = (
        supabase_client.table("patient_challenges")
        .select("id, patient_id, challenge_id, progress, due_on, started_at, status")
        .order("patient_id")
        .order("started_at", desc=True)
        .execute()
    )
    profiles = {
        p["id"]: p["full_name"]
        for p in (
            supabase_client.table("profiles").select("id, full_name").execute().data or []
        )
    }
    challenges = {
        c["id"]: c["title"]
        for c in (
            supabase_client.table("challenges").select("id, title").execute().data or []
        )
    }
    print(f"{'aid':<6} {'pid':<6} {'patient':<28} {'cid':<6} {'challenge':<35} {'status':<11} {'prog':<5}")
    print("-" * 100)
    for r in rows.data or []:
        print(
            f"{r['id']:<6} "
            f"{r['patient_id']:<6} "
            f"{profiles.get(r['patient_id'], '?').ljust(28)[:28]} "
            f"{r['challenge_id']:<6} "
            f"{challenges.get(r['challenge_id'], '?').ljust(35)[:35]} "
            f"{r['status'].ljust(11)} "
            f"{r.get('progress', 0):<5}"
        )


if __name__ == "__main__":
    main()
