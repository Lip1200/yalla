"""Seed a direct conversation between Tefa (108) and Amina (102) with a
few messages, so the patient-app Messages tab is not empty during the
demo. Idempotent: skips if Tefa already has a conversation."""

from src.core.database import supabase_client


def main() -> None:
    tefa_id = 108
    amina_id = 102

    existing = (
        supabase_client.table("conversation_participants")
        .select("conversation_id")
        .eq("user_id", tefa_id)
        .execute()
    )
    if existing.data:
        print(f"Tefa already in {len(existing.data)} conversation(s) — skipping seed.")
        return

    conv = (
        supabase_client.table("conversations")
        .insert({"kind": "direct", "title": None})
        .execute()
        .data[0]
    )
    conversation_id = conv["id"]
    print(f"created conversation #{conversation_id}")

    supabase_client.table("conversation_participants").insert(
        [
            {"conversation_id": conversation_id, "user_id": tefa_id},
            {"conversation_id": conversation_id, "user_id": amina_id},
        ]
    ).execute()

    for sender_id, content in [
        (amina_id, "Salut Tefa, bienvenue sur Yalla! Tu démarres ton parcours, raconte-moi tes objectifs ?"),
        (tefa_id, "Hello Amina, je veux surtout marcher plus régulièrement et mieux gérer les repas."),
        (amina_id, "Top, on va y aller en douceur. J'ai mis un défi marche douce, jette un œil dans l'onglet Défis."),
        (tefa_id, "Merci, je m'y inscris ce soir !"),
    ]:
        supabase_client.table("messages").insert(
            {"conversation_id": conversation_id, "sender_id": sender_id, "content": content}
        ).execute()

    print("seeded 4 messages")


if __name__ == "__main__":
    main()
