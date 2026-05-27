"""Test: does supabase_client.auth.get_user(token) leak the JWT into the
client's session, making subsequent .table() queries use the user JWT
(subject to RLS) instead of the service_role key?

To reproduce, we'd need a valid JWT for Tefa. Instead, we just compare a
query before and after a get_user call — if the client's auth state
changed, the second query will use a different identity."""

from src.core.database import supabase_client


def query_profile() -> list:
    return (
        supabase_client.table("profiles")
        .select("id, auth_user_id, full_name")
        .eq("auth_user_id", "44cf4977-732f-428e-a763-396559e2d789")
        .execute()
        .data
        or []
    )


print("=== query BEFORE any auth call ===")
print(f"  rows={len(query_profile())}")

# Inspect the client's headers / session state, if accessible
postgrest = supabase_client.postgrest
print()
print("=== postgrest client state ===")
print(f"  headers Authorization = {postgrest.session.headers.get('Authorization')[:30]}...")
print(f"  headers apikey         = {postgrest.session.headers.get('apikey')[:30] if postgrest.session.headers.get('apikey') else None}...")
