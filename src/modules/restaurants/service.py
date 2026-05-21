"""
Restaurant booking service — pool-based group reservations with TheFork integration.

Flow:
1. Patient creates a pool for a curated restaurant → status: open
2. Other patients join the pool
3. When enrolled_count == capacity → auto-book via TheFork → status: booked
4. Pools past their scheduled_for date with status open → expired
"""

import asyncio
from datetime import datetime, timezone

from fastapi import HTTPException, status

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


# --- Curated Restaurants ---


def list_restaurants() -> list[CuratedRestaurant]:
    """Return all curated diabetes-friendly restaurants."""
    response = (
        supabase_client.table("curated_restaurants")
        .select("*")
        .order("diabetes_friendly_score", desc=True)
        .execute()
    )
    return [CuratedRestaurant(**row) for row in response.data]


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
