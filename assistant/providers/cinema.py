"""Cinema API client provider for showtimes and bookings."""

import logging

import httpx

from assistant.exceptions import CinemaAPIError
from assistant.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class CinemaProvider(BaseProvider):
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)

    async def get_cinemas(self, city: str | None = None) -> list[dict]:
        try:
            client = await self.get_client()
            params = {}
            if city:
                params["city"] = city
            resp = await client.get("/cinemas", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise CinemaAPIError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise CinemaAPIError(f"Connection error: {e}") from e

    async def get_showtimes(
        self,
        film_title: str | None = None,
        cinema_id: int | None = None,
        date: str | None = None,
    ) -> list[dict]:
        try:
            client = await self.get_client()
            params: dict = {}

            # If film_title given, resolve to film_id first
            if film_title:
                film = await self._find_film(film_title)
                if film:
                    params["film_id"] = film["id"]
                else:
                    return []  # Film not found in cinema DB

            if cinema_id:
                params["cinema_id"] = cinema_id
            if date:
                params["date"] = date

            resp = await client.get("/showtimes", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise CinemaAPIError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise CinemaAPIError(f"Connection error: {e}") from e

    async def book_tickets(
        self,
        showtime_id: int,
        num_tickets: int,
        customer_name: str,
        customer_email: str,
    ) -> dict:
        try:
            client = await self.get_client()
            resp = await client.post(
                "/bookings",
                json={
                    "showtime_id": showtime_id,
                    "num_tickets": num_tickets,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            body = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else {}
            error_msg = body.get("error", f"HTTP {e.response.status_code}")
            raise CinemaAPIError(error_msg) from e
        except httpx.RequestError as e:
            raise CinemaAPIError(f"Connection error: {e}") from e

    async def get_booking(self, booking_ref: str) -> dict:
        try:
            client = await self.get_client()
            resp = await client.get(f"/bookings/{booking_ref}")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise CinemaAPIError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise CinemaAPIError(f"Connection error: {e}") from e

    async def _find_film(self, title: str) -> dict | None:
        """Search for a film by title in the Cinema API."""
        try:
            client = await self.get_client()
            resp = await client.get("/films", params={"search": title})
            resp.raise_for_status()
            films = resp.json()
            return films[0] if films else None
        except (httpx.HTTPStatusError, httpx.RequestError):
            return None
