from fastapi import APIRouter, Depends

from src.core.security import get_current_user
from src.modules.restaurants.schemas import (
    CuratedRestaurant,
    PoolCreate,
    PoolJoinResult,
    PoolResponse,
)
from src.modules.restaurants.service import (
    cancel_pool,
    create_pool,
    get_pool,
    join_pool,
    leave_pool,
    list_pools,
    list_restaurants,
)

# Secure all restaurant endpoints via global dependency
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/recommendations", response_model=list[CuratedRestaurant])
def read_restaurants(
    lat: float = 46.2044,
    lon: float = 6.1432,
    radius_m: int = 2500,
    limit: int = 20,
    q: str | None = None,
):
    """List diabetes-friendly restaurants near a location."""
    return list_restaurants(lat=lat, lon=lon, radius_m=radius_m, limit=limit, q=q)


@router.post("/pools", response_model=PoolResponse)
def create_dining_pool(creator_id: int, payload: PoolCreate):
    """Create a new group dining pool."""
    return create_pool(creator_id, payload)


@router.get("/pools", response_model=list[PoolResponse])
def read_pools(status: str | None = None):
    """List all pools, optionally filtered by status (open, full, booked, etc.)."""
    return list_pools(status_filter=status)


@router.get("/pools/{pool_id}", response_model=PoolResponse)
def read_pool(pool_id: int):
    """Get details of a specific pool including participants."""
    return get_pool(pool_id)


@router.post("/pools/{pool_id}/join", response_model=PoolJoinResult)
def join_dining_pool(pool_id: int, user_id: int):
    """Join an open pool. Auto-books via TheFork when capacity is reached."""
    return join_pool(pool_id, user_id)


@router.delete("/pools/{pool_id}/leave", response_model=PoolResponse)
def leave_dining_pool(pool_id: int, user_id: int):
    """Leave an open pool (non-creators only)."""
    return leave_pool(pool_id, user_id)


@router.delete("/pools/{pool_id}", response_model=PoolResponse)
def cancel_dining_pool(pool_id: int, user_id: int):
    """Cancel a pool (creator only). Cancels TheFork reservation if booked."""
    return cancel_pool(pool_id, user_id)
