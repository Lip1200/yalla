"""
TheFork API client abstraction.

Supports two modes:
- **Mock mode** (default): When THEFORK_API_KEY is empty, returns simulated
  responses so the full booking flow is demonstrable without real credentials.
- **Live mode**: When credentials are configured, performs real HTTP calls
  to the TheFork Partners API.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

import httpx

from src.core.config import settings


@dataclass
class ReservationResult:
    success: bool
    reservation_id: str
    status: str  # RECORDED, REJECTED, etc.
    message: str


class TheForkClient:
    """Abstracted client for the TheFork Partners API."""

    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._mock = not bool(api_key)

    @property
    def is_mock(self) -> bool:
        return self._mock

    async def create_reservation(
        self,
        restaurant_id: str,
        meal_date: datetime,
        party_size: int,
        customer_note: str = "",
    ) -> ReservationResult:
        """Create a reservation on TheFork for the given restaurant."""
        if self._mock:
            return self._mock_create(restaurant_id, meal_date, party_size)

        url = f"{self._base_url}/restaurants/{restaurant_id}/reservations"
        payload = {
            "mealDate": meal_date.isoformat(),
            "partySize": party_size,
            "customerNote": customer_note,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=15)

        if resp.status_code in (200, 201):
            data = resp.json()
            return ReservationResult(
                success=True,
                reservation_id=data.get("id", ""),
                status=data.get("status", "RECORDED"),
                message="Reservation confirmed by TheFork.",
            )

        return ReservationResult(
            success=False,
            reservation_id="",
            status="REJECTED",
            message=f"TheFork returned HTTP {resp.status_code}: {resp.text[:200]}",
        )

    async def cancel_reservation(
        self,
        restaurant_id: str,
        reservation_id: str,
    ) -> bool:
        """Cancel an existing reservation. Returns True on success."""
        if self._mock:
            return True

        url = f"{self._base_url}/restaurants/{restaurant_id}/reservations/{reservation_id}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=headers, timeout=15)

        return resp.status_code in (200, 204)

    # --- Mock helpers ---

    @staticmethod
    def _mock_create(
        restaurant_id: str,
        meal_date: datetime,
        party_size: int,
    ) -> ReservationResult:
        mock_id = f"mock-{uuid.uuid4().hex[:12]}"
        return ReservationResult(
            success=True,
            reservation_id=mock_id,
            status="RECORDED",
            message=(
                f"[MOCK] Reservation for {party_size} guests at restaurant "
                f"{restaurant_id} on {meal_date.date()} confirmed."
            ),
        )


# Singleton instance used across the application
thefork_client = TheForkClient(
    api_key=settings.thefork_api_key,
    base_url=settings.thefork_base_url,
)
