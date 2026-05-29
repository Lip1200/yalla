from supabase import Client, create_client

from src.core.config import settings

supabase_client: Client = create_client(settings.supabase_url, settings.supabase_key)


def restore_service_bearer() -> None:
    """Force the shared postgrest client's Authorization header back to
    the service-role key.

    Background: `supabase_client.postgrest.auth(key)` is misleading in
    supabase-py 2.x — it returns a NEW SyncPostgrestClient with the
    auth set, but does NOT mutate the original singleton. So calling
    `supabase_client.postgrest.auth(settings.supabase_key)` in a
    `finally` block (the pattern we used after every supabase-py auth
    call) was a no-op: the original singleton kept whichever JWT
    `sign_up` / `sign_in_with_password` / `get_user` had stamped on it.

    The downstream `.table().update()` calls in the same request then
    ran under the just-created patient's identity, and RLS silently
    returned empty result sets — so the patient activation never linked
    `profiles.auth_user_id`, never burned the invitation token, and the
    patient's second login bootstrapped with no profile (the demo bug
    that #47 / #48 *attempted* to fix but didn't actually).

    The reliable restore is direct header assignment on the singleton's
    session, which IS what supabase-py uses to attach the bearer on each
    request. Call this from every `finally` after a supabase-py auth call.
    """
    supabase_client.postgrest.session.headers["Authorization"] = (
        f"Bearer {settings.supabase_key}"
    )
