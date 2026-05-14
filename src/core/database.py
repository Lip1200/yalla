from supabase import Client, create_client

from src.core.config import settings

supabase_client: Client = create_client(settings.supabase_url, settings.supabase_key)
