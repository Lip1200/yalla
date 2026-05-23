"""
Restaurant booking service — pool-based group reservations with TheFork integration.

Flow:
1. Patient creates a pool for a curated restaurant → status: open
2. Other patients join the pool
3. When enrolled_count == capacity → auto-book via TheFork → status: booked
4. Pools past their scheduled_for date with status open → expired
"""

import asyncio
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher

import httpx
from fastapi import HTTPException, status

from src.core.config import settings
from src.core.database import supabase_client
from src.core.thefork_client import thefork_client
from src.modules.restaurants.schemas import (
    CuratedRestaurant,
    PoolCreate,
    PoolJoinResult,
    PoolParticipant,
    PoolResponse,
    PoolStatus,
)


# --- Restaurant discovery ---


SEARCH_STOPWORDS = {
    "a",
    "au",
    "aux",
    "de",
    "des",
    "du",
    "la",
    "le",
    "les",
    "l",
    "the",
    "and",
    "restaurant",
    "resto",
}


HEALTHY_RESTAURANTS = [
    CuratedRestaurant(
        id=1,
        thefork_restaurant_id="fallback-maison-verte",
        name="Maison Verte",
        area="Centre-ville",
        cuisine_type="Cuisine saine",
        diabetes_friendly_score=92,
        best_for="Déjeuner léger",
        notes="Options riches en légumes, portions modulables et desserts sans sucre ajouté.",
        price_range="15-22 CHF",
        image_url="",
    ),
    CuratedRestaurant(
        id=4,
        thefork_restaurant_id="healthy-green-gorilla",
        name="Green Gorilla",
        area="Genève",
        cuisine_type="Bowls et salades",
        diabetes_friendly_score=90,
        best_for="Repas healthy",
        notes="Bols, salades et options riches en légumes; pratique pour composer un repas équilibré sans menu trop lourd.",
        price_range="15-24 CHF",
        image_url="",
    ),
    CuratedRestaurant(
        id=5,
        thefork_restaurant_id="healthy-qibi",
        name="Qibi",
        area="Genève",
        cuisine_type="Cuisine saine",
        diabetes_friendly_score=88,
        best_for="Déjeuner équilibré",
        notes="Adresse orientée repas frais et modulables; privilégiez les légumes, protéines simples et féculents complets.",
        price_range="14-22 CHF",
        image_url="",
    ),
    CuratedRestaurant(
        id=6,
        thefork_restaurant_id="healthy-elsalad",
        name="El Salad",
        area="Genève",
        cuisine_type="Salades",
        diabetes_friendly_score=86,
        best_for="Salade complète",
        notes="Bon choix pour une salade composée avec protéines et toppings maîtrisés; demandez la sauce à part si possible.",
        price_range="13-21 CHF",
        image_url="",
    ),
    CuratedRestaurant(
        id=7,
        thefork_restaurant_id="local-la-goulette",
        name="La Goulette",
        area="Rue des Bains 43, Genève",
        cuisine_type="Tunisien",
        diabetes_friendly_score=74,
        best_for="Cuisine tunisienne",
        notes="Restaurant tunisien; privilégiez les plats riches en légumes, les grillades ou un couscous avec portion maîtrisée.",
        price_range="45-55 CHF",
        image_url="",
    ),
]

FALLBACK_RESTAURANTS = [
    *HEALTHY_RESTAURANTS,
    CuratedRestaurant(
        id=2,
        thefork_restaurant_id="fallback-atlas-bowl",
        name="Atlas Bowl",
        area="Plainpalais",
        cuisine_type="Bowls",
        diabetes_friendly_score=87,
        best_for="Repas rapide équilibré",
        notes="Bowls personnalisables avec céréales complètes, protéines maigres et sauces séparées.",
        price_range="14-20 CHF",
        image_url="",
    ),
    CuratedRestaurant(
        id=3,
        thefork_restaurant_id="fallback-jardin-simple",
        name="Le Jardin Simple",
        area="Eaux-Vives",
        cuisine_type="Grillades",
        diabetes_friendly_score=82,
        best_for="Dîner calme",
        notes="Carte claire, plats grillés, accompagnements légumes disponibles.",
        price_range="20-32 CHF",
        image_url="",
    ),
]

CHAIN_RESTAURANTS = [
    CuratedRestaurant(
        id=9001,
        thefork_restaurant_id="chain-kfc",
        name="KFC",
        area="Autour de vous",
        cuisine_type="Restauration rapide",
        diabetes_friendly_score=50,
        best_for="Option rapide",
        notes="Chaîne de restauration rapide à utiliser ponctuellement; privilégiez l'eau, les petites portions et évitez les menus très sucrés.",
        price_range="10-18 CHF",
        image_url="",
    ),
    CuratedRestaurant(
        id=9002,
        thefork_restaurant_id="chain-mcdonalds",
        name="McDonald's",
        area="Autour de vous",
        cuisine_type="Restauration rapide",
        diabetes_friendly_score=52,
        best_for="Option rapide",
        notes="Chaîne pratique pour un repas rapide; choisissez plutôt une portion simple, de l'eau et limitez les boissons sucrées.",
        price_range="10-18 CHF",
        image_url="",
    ),
    CuratedRestaurant(
        id=9003,
        thefork_restaurant_id="chain-burger-king",
        name="Burger King",
        area="Autour de vous",
        cuisine_type="Restauration rapide",
        diabetes_friendly_score=50,
        best_for="Option rapide",
        notes="Option rapide à garder occasionnelle; les petites portions et les boissons sans sucre sont les choix les plus simples.",
        price_range="10-18 CHF",
        image_url="",
    ),
    CuratedRestaurant(
        id=9004,
        thefork_restaurant_id="chain-subway",
        name="Subway",
        area="Autour de vous",
        cuisine_type="Sandwichs",
        diabetes_friendly_score=66,
        best_for="Repas modulable",
        notes="Sandwichs personnalisables; privilégiez les légumes, une protéine simple et une sauce légère.",
        price_range="10-16 CHF",
        image_url="",
    ),
    CuratedRestaurant(
        id=9005,
        thefork_restaurant_id="chain-chic-chicken",
        name="Chic Chicken",
        area="Autour de vous",
        cuisine_type="Poulet",
        diabetes_friendly_score=54,
        best_for="Option rapide",
        notes="Restaurant de poulet à garder occasionnel; préférez les portions simples, l'eau et évitez les boissons sucrées.",
        price_range="10-18 CHF",
        image_url="",
    ),
]


def list_restaurants(
    lat: float = 46.2044,
    lon: float = 6.1432,
    radius_m: int = 2500,
    limit: int = 20,
    q: str | None = None,
) -> list[CuratedRestaurant]:
    """Return diabetes-friendly restaurant recommendations near a location."""
    chain_matches = _filter_restaurants(CHAIN_RESTAURANTS, q)
    if q and chain_matches:
        return chain_matches[:limit]

    overpass_restaurants = _list_restaurants_from_overpass(lat, lon, radius_m, limit, q)
    if overpass_restaurants:
        if not q:
            healthy_overpass = [restaurant for restaurant in overpass_restaurants if restaurant.diabetes_friendly_score >= 70]
            return _merge_restaurants([*HEALTHY_RESTAURANTS, *healthy_overpass])[:limit]
        return overpass_restaurants

    try:
        response = (
            supabase_client.table("curated_restaurants")
            .select("*")
            .order("diabetes_friendly_score", desc=True)
            .execute()
        )
        if response.data:
            return _filter_restaurants([CuratedRestaurant(**row) for row in response.data], q)
    except Exception:
        pass

    fallback_pool = [*CHAIN_RESTAURANTS, *FALLBACK_RESTAURANTS] if q else FALLBACK_RESTAURANTS
    return _filter_restaurants(_merge_restaurants(fallback_pool), q)[:limit]


def _list_restaurants_from_overpass(
    lat: float,
    lon: float,
    radius_m: int,
    limit: int,
    q: str | None = None,
) -> list[CuratedRestaurant]:
    radius = max(250, min(radius_m, 10000))
    max_items = max(1, min(limit, 50))
    search = (q or "").strip()
    if search:
        regex = _overpass_regex(search)
        query = f"""
        [out:json][timeout:1];
        (
          node["amenity"~"^(restaurant|cafe|fast_food)$"]["name"~"{regex}",i](around:{radius},{lat},{lon});
          way["amenity"~"^(restaurant|cafe|fast_food)$"]["name"~"{regex}",i](around:{radius},{lat},{lon});
          relation["amenity"~"^(restaurant|cafe|fast_food)$"]["name"~"{regex}",i](around:{radius},{lat},{lon});
          node["amenity"~"^(restaurant|cafe|fast_food)$"]["brand"~"{regex}",i](around:{radius},{lat},{lon});
          way["amenity"~"^(restaurant|cafe|fast_food)$"]["brand"~"{regex}",i](around:{radius},{lat},{lon});
          relation["amenity"~"^(restaurant|cafe|fast_food)$"]["brand"~"{regex}",i](around:{radius},{lat},{lon});
          node["amenity"~"^(restaurant|cafe|fast_food)$"]["cuisine"~"{regex}",i](around:{radius},{lat},{lon});
          way["amenity"~"^(restaurant|cafe|fast_food)$"]["cuisine"~"{regex}",i](around:{radius},{lat},{lon});
          relation["amenity"~"^(restaurant|cafe|fast_food)$"]["cuisine"~"{regex}",i](around:{radius},{lat},{lon});
        );
        out center tags {max_items};
        """
    else:
        query = f"""
        [out:json][timeout:1];
        (
          node["amenity"~"^(restaurant|cafe|fast_food)$"](around:{radius},{lat},{lon});
          way["amenity"~"^(restaurant|cafe|fast_food)$"](around:{radius},{lat},{lon});
          relation["amenity"~"^(restaurant|cafe|fast_food)$"](around:{radius},{lat},{lon});
        );
        out center tags {max_items};
        """

    try:
        response = httpx.post(
            settings.overpass_api_url,
            data={"data": query},
            timeout=httpx.Timeout(2.0, connect=1.0),
            headers={"User-Agent": "Yalla diabetes prevention student app"},
        )
        response.raise_for_status()
        elements = response.json().get("elements", [])
    except Exception:
        return []

    restaurants = []
    seen_names = set()
    for element in elements:
        tags = element.get("tags") or {}
        name = tags.get("name")
        if not name or name.lower() in seen_names:
            continue

        seen_names.add(name.lower())
        restaurants.append(_overpass_element_to_restaurant(element, tags))

    restaurants.sort(key=lambda item: item.diabetes_friendly_score, reverse=True)
    return restaurants[:max_items]


def _overpass_regex(value: str) -> str:
    tokens = _search_tokens(value)
    if not tokens:
        return re.escape(value)[:80].replace('"', '\\"')
    return "|".join(re.escape(token) for token in tokens[:4])[:120].replace('"', '\\"')


def _overpass_element_to_restaurant(element: dict, tags: dict) -> CuratedRestaurant:
    cuisine = (tags.get("cuisine") or "").replace(";", ", ")
    area = tags.get("addr:city") or tags.get("addr:suburb") or tags.get("addr:street") or "Autour de vous"
    amenity = tags.get("amenity", "restaurant")
    score = _score_restaurant(tags)

    return CuratedRestaurant(
        id=int(element["id"]),
        thefork_restaurant_id=f"osm-{element['type']}-{element['id']}",
        name=tags.get("name", "Restaurant"),
        area=area,
        cuisine_type=cuisine or _amenity_label(amenity),
        diabetes_friendly_score=score,
        best_for=_best_for(tags, score),
        notes=_restaurant_notes(tags, score),
        price_range=_price_range(tags, score),
        image_url="",
    )


def _amenity_label(amenity: str) -> str:
    if amenity == "cafe":
        return "Café"
    if amenity == "fast_food":
        return "Restauration rapide"
    return "Restaurant"


def _filter_restaurants(restaurants: list[CuratedRestaurant], q: str | None) -> list[CuratedRestaurant]:
    if not q:
        return restaurants

    tokens = _search_tokens(q)
    if not tokens:
        return restaurants

    normalized_query = " ".join(tokens)
    scored = []
    for restaurant in restaurants:
        haystack = _restaurant_search_text(restaurant)
        token_hits = sum(1 for token in tokens if token in haystack)
        fuzzy_score = SequenceMatcher(None, normalized_query, haystack).ratio()
        name_score = SequenceMatcher(None, normalized_query, _normalize_search(restaurant.name)).ratio()

        if token_hits or name_score >= 0.72 or fuzzy_score >= 0.78:
            scored.append((token_hits, name_score, fuzzy_score, restaurant.diabetes_friendly_score, restaurant))

    scored.sort(reverse=True, key=lambda item: item[:4])
    return [item[-1] for item in scored]


def _merge_restaurants(restaurants: list[CuratedRestaurant]) -> list[CuratedRestaurant]:
    seen = set()
    merged = []
    for restaurant in restaurants:
        key = (restaurant.thefork_restaurant_id or restaurant.name).lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(restaurant)
    return merged


def _restaurant_search_text(restaurant: CuratedRestaurant) -> str:
    return _normalize_search(
        " ".join(
            [
                restaurant.name,
                restaurant.area,
                restaurant.cuisine_type,
                restaurant.best_for,
                restaurant.notes,
                restaurant.price_range,
            ]
        )
    )


def _search_tokens(value: str) -> list[str]:
    normalized = _normalize_search(value)
    return [
        token
        for token in re.split(r"\s+", normalized)
        if len(token) >= 3 and token not in SEARCH_STOPWORDS
    ]


def _normalize_search(value: str) -> str:
    without_accents = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", without_accents.lower()).strip()


def _score_restaurant(tags: dict) -> int:
    cuisine = (tags.get("cuisine") or "").lower()
    name = (tags.get("name") or "").lower()
    amenity = tags.get("amenity")
    text = f"{amenity or ''} {cuisine} {name}"
    score = 68

    positive_terms = [
        "salad",
        "vegetarian",
        "vegan",
        "mediterranean",
        "japanese",
        "lebanese",
        "greek",
        "fish",
        "bowl",
        "healthy",
    ]
    cautious_terms = ["burger", "pizza", "fast_food", "kebab", "fried", "dessert", "ice_cream"]

    score += sum(5 for term in positive_terms if term in text)
    score -= sum(6 for term in cautious_terms if term in text)

    if tags.get("diet:vegetarian") in {"yes", "only"}:
        score += 6
    if tags.get("diet:vegan") in {"yes", "only"}:
        score += 4
    if tags.get("outdoor_seating") == "yes":
        score += 2

    return max(45, min(score, 96))


def _best_for(tags: dict, score: int) -> str:
    cuisine = (tags.get("cuisine") or "").lower()
    if score >= 86:
        return "Repas équilibré"
    if tags.get("amenity") == "cafe":
        return "Pause légère"
    if tags.get("amenity") == "fast_food":
        return "Option rapide"
    if "mediterranean" in cuisine or "lebanese" in cuisine or "greek" in cuisine:
        return "Assiette méditerranéenne"
    return "Sortie encadrée"


def _restaurant_notes(tags: dict, score: int) -> str:
    cuisine = (tags.get("cuisine") or "").replace(";", ", ")
    amenity = tags.get("amenity")

    if amenity == "cafe":
        base = "Adresse pratique pour une pause simple, avec des options faciles à ajuster selon l'appétit."
    elif amenity == "fast_food":
        base = "Option rapide à utiliser ponctuellement; privilégiez l'eau, les petites portions et un accompagnement plus léger quand c'est possible."
    elif score >= 85:
        base = "Bon choix pour composer un repas équilibré avec protéines, légumes et accompagnement complet."
    elif score >= 72:
        base = "Restaurant intéressant pour une sortie accompagnée, surtout en choisissant des portions modulables."
    else:
        base = "Adresse possible pour manger dehors, avec un choix attentif sur les boissons, sauces et accompagnements."

    if cuisine:
        base += f" Cuisine proposée : {cuisine}."
    return base


def _price_range(tags: dict, score: int) -> str:
    price = (tags.get("price") or tags.get("price:range") or "").strip()
    if price and "CHF" in price.upper():
        return price

    cuisine = (tags.get("cuisine") or "").lower()
    amenity = tags.get("amenity")
    text = f"{amenity or ''} {cuisine}"

    if amenity == "cafe" or any(term in text for term in ["coffee", "tea", "bakery"]):
        return "8-15 CHF"
    if any(term in text for term in ["fast_food", "kebab", "burger", "pizza", "sandwich"]):
        return "10-18 CHF"
    if any(term in text for term in ["japanese", "sushi", "fish", "steak", "french"]):
        return "20-35 CHF"
    if any(term in text for term in ["bowl", "salad", "vegetarian", "vegan", "mediterranean", "lebanese"]):
        return "14-24 CHF"
    if score >= 85:
        return "16-28 CHF"
    return "15-25 CHF"


def get_restaurant(restaurant_id: int) -> CuratedRestaurant:
    """Fetch a single curated restaurant or raise 404."""
    response = (
        supabase_client.table("curated_restaurants")
        .select("*")
        .eq("id", restaurant_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found.",
        )
    return CuratedRestaurant(**response.data[0])


# --- Pools ---


def create_pool(creator_id: int, payload: PoolCreate) -> PoolResponse:
    """Create a new dining pool and add the creator as the first participant."""
    restaurant = get_restaurant(payload.restaurant_id)

    pool_data = {
        "creator_id": creator_id,
        "restaurant_id": payload.restaurant_id,
        "scheduled_for": payload.scheduled_for.isoformat(),
        "capacity": payload.capacity,
        "status": PoolStatus.OPEN,
        "customer_note": payload.customer_note,
    }
    pool_resp = supabase_client.table("restaurant_pools").insert(pool_data).execute()
    pool_row = pool_resp.data[0]

    # Add creator as the first participant
    supabase_client.table("pool_participants").insert({
        "pool_id": pool_row["id"],
        "user_id": creator_id,
    }).execute()

    return _build_pool_response(pool_row, restaurant)


def join_pool(pool_id: int, user_id: int) -> PoolJoinResult:
    """Join an existing pool. Triggers auto-booking when capacity is reached."""
    pool_row = _get_pool_row(pool_id)

    if pool_row["status"] != PoolStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot join a pool with status '{pool_row['status']}'.",
        )

    # Check if already joined
    existing = (
        supabase_client.table("pool_participants")
        .select("id")
        .eq("pool_id", pool_id)
        .eq("user_id", user_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already joined this pool.",
        )

    # Add participant
    supabase_client.table("pool_participants").insert({
        "pool_id": pool_id,
        "user_id": user_id,
    }).execute()

    # Count participants
    participants = (
        supabase_client.table("pool_participants")
        .select("id")
        .eq("pool_id", pool_id)
        .execute()
    )
    enrolled_count = len(participants.data)

    auto_booked = False
    if enrolled_count >= pool_row["capacity"]:
        # Update status to full, then trigger auto-booking
        supabase_client.table("restaurant_pools").update(
            {"status": PoolStatus.FULL}
        ).eq("id", pool_id).execute()

        auto_booked = _auto_book(pool_id)

    # Reload latest state
    pool_row = _get_pool_row(pool_id)
    restaurant = get_restaurant(pool_row["restaurant_id"])
    pool_response = _build_pool_response(pool_row, restaurant)

    return PoolJoinResult(pool=pool_response, auto_booked=auto_booked)


def leave_pool(pool_id: int, user_id: int) -> PoolResponse:
    """Leave a pool (only allowed while status is 'open')."""
    pool_row = _get_pool_row(pool_id)

    if pool_row["status"] != PoolStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot leave a pool that is no longer open.",
        )

    if pool_row["creator_id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The pool creator cannot leave. Cancel the pool instead.",
        )

    supabase_client.table("pool_participants").delete().eq(
        "pool_id", pool_id
    ).eq("user_id", user_id).execute()

    pool_row = _get_pool_row(pool_id)
    restaurant = get_restaurant(pool_row["restaurant_id"])
    return _build_pool_response(pool_row, restaurant)


def cancel_pool(pool_id: int, user_id: int) -> PoolResponse:
    """Cancel a pool (creator only). Cancels TheFork reservation if already booked."""
    pool_row = _get_pool_row(pool_id)

    if pool_row["creator_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the pool creator can cancel.",
        )

    if pool_row["status"] in (PoolStatus.CANCELLED, PoolStatus.EXPIRED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pool is already {pool_row['status']}.",
        )

    # Cancel TheFork reservation if it exists
    if pool_row.get("thefork_reservation_id"):
        restaurant = get_restaurant(pool_row["restaurant_id"])
        asyncio.run(
            thefork_client.cancel_reservation(
                restaurant.thefork_restaurant_id,
                pool_row["thefork_reservation_id"],
            )
        )

    supabase_client.table("restaurant_pools").update(
        {"status": PoolStatus.CANCELLED}
    ).eq("id", pool_id).execute()

    pool_row = _get_pool_row(pool_id)
    restaurant = get_restaurant(pool_row["restaurant_id"])
    return _build_pool_response(pool_row, restaurant)


def list_pools(status_filter: str | None = None) -> list[PoolResponse]:
    """List all pools, optionally filtered by status."""
    # First expire any overdue open pools
    _expire_overdue_pools()

    query = supabase_client.table("restaurant_pools").select("*").order("scheduled_for", desc=False)
    if status_filter:
        query = query.eq("status", status_filter)
    response = query.execute()

    result = []
    for row in response.data:
        restaurant = get_restaurant(row["restaurant_id"])
        result.append(_build_pool_response(row, restaurant))
    return result


def get_pool(pool_id: int) -> PoolResponse:
    """Get a single pool with full details."""
    pool_row = _get_pool_row(pool_id)
    restaurant = get_restaurant(pool_row["restaurant_id"])
    return _build_pool_response(pool_row, restaurant)


# --- Internal helpers ---


def _get_pool_row(pool_id: int) -> dict:
    response = (
        supabase_client.table("restaurant_pools")
        .select("*")
        .eq("id", pool_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pool not found.",
        )
    return response.data[0]


def _build_pool_response(pool_row: dict, restaurant: CuratedRestaurant) -> PoolResponse:
    """Build a PoolResponse from a database row and restaurant object."""
    # Fetch participants with profile names
    participants_resp = (
        supabase_client.table("pool_participants")
        .select("user_id, joined_at")
        .eq("pool_id", pool_row["id"])
        .order("joined_at", desc=False)
        .execute()
    )

    participants = []
    for p in participants_resp.data:
        profile = supabase_client.table("profiles").select("full_name").eq("id", p["user_id"]).execute()
        name = profile.data[0]["full_name"] if profile.data else "Unknown"
        joined_at_str = p["joined_at"]
        joined_at = (
            datetime.fromisoformat(joined_at_str.replace("Z", "+00:00"))
            if joined_at_str
            else datetime.now(tz=timezone.utc)
        )
        participants.append(PoolParticipant(user_id=p["user_id"], full_name=name, joined_at=joined_at))

    scheduled_str = pool_row["scheduled_for"]
    scheduled_for = datetime.fromisoformat(scheduled_str.replace("Z", "+00:00")) if scheduled_str else datetime.now(tz=timezone.utc)

    created_str = pool_row["created_at"]
    created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00")) if created_str else datetime.now(tz=timezone.utc)

    # Resolve creator name
    creator_profile = supabase_client.table("profiles").select("full_name").eq("id", pool_row["creator_id"]).execute()
    creator_name = creator_profile.data[0]["full_name"] if creator_profile.data else "Unknown"

    return PoolResponse(
        id=pool_row["id"],
        creator_id=pool_row["creator_id"],
        creator_name=creator_name,
        restaurant=restaurant,
        scheduled_for=scheduled_for,
        capacity=pool_row["capacity"],
        enrolled_count=len(participants),
        status=PoolStatus(pool_row["status"]),
        customer_note=pool_row.get("customer_note") or "",
        thefork_reservation_id=pool_row.get("thefork_reservation_id"),
        participants=participants,
        created_at=created_at,
    )


def _auto_book(pool_id: int) -> bool:
    """Trigger TheFork reservation when pool reaches capacity."""
    pool_row = _get_pool_row(pool_id)
    restaurant = get_restaurant(pool_row["restaurant_id"])

    scheduled_str = pool_row["scheduled_for"]
    meal_date = datetime.fromisoformat(scheduled_str.replace("Z", "+00:00")) if scheduled_str else datetime.now(tz=timezone.utc)

    result = asyncio.run(
        thefork_client.create_reservation(
            restaurant_id=restaurant.thefork_restaurant_id,
            meal_date=meal_date,
            party_size=pool_row["capacity"],
            customer_note=pool_row.get("customer_note") or "",
        )
    )

    if result.success:
        supabase_client.table("restaurant_pools").update({
            "status": PoolStatus.BOOKED,
            "thefork_reservation_id": result.reservation_id,
        }).eq("id", pool_id).execute()
        return True

    # If booking fails, revert to open so users can retry or adjust
    supabase_client.table("restaurant_pools").update(
        {"status": PoolStatus.OPEN}
    ).eq("id", pool_id).execute()
    return False


def _expire_overdue_pools() -> None:
    """Mark open pools past their scheduled date as expired."""
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    supabase_client.table("restaurant_pools").update(
        {"status": PoolStatus.EXPIRED}
    ).eq("status", PoolStatus.OPEN).lt("scheduled_for", now_iso).execute()
