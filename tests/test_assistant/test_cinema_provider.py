"""Tests for Cinema API client provider."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from assistant.exceptions import CinemaAPIError
from assistant.providers.cinema import CinemaProvider


def _mock_response(json_data, status_code=200):
    return httpx.Response(status_code, json=json_data, request=httpx.Request("GET", "http://test"))


class TestCinemaProvider:
    @pytest.mark.asyncio
    async def test_get_cinemas(self):
        provider = CinemaProvider("http://localhost:8000")
        mock_data = [{"id": 1, "name": "Lev Dizengoff", "city": "Tel Aviv"}]

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(mock_data))
            mock_client.return_value = client

            result = await provider.get_cinemas(city="Tel Aviv")

        assert len(result) == 1
        assert result[0]["name"] == "Lev Dizengoff"

    @pytest.mark.asyncio
    async def test_get_showtimes_by_title(self):
        provider = CinemaProvider("http://localhost:8000")
        films_data = [{"id": 1, "title": "Sinners"}]
        showtimes_data = [{"id": 1, "film_id": 1, "movie_title": "Sinners"}]

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            # First call: search films, second call: get showtimes
            client.get = AsyncMock(
                side_effect=[
                    _mock_response(films_data),
                    _mock_response(showtimes_data),
                ]
            )
            mock_client.return_value = client

            result = await provider.get_showtimes(film_title="Sinners")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_showtimes_film_not_found(self):
        provider = CinemaProvider("http://localhost:8000")

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response([]))
            mock_client.return_value = client

            result = await provider.get_showtimes(film_title="Nonexistent")

        assert result == []

    @pytest.mark.asyncio
    async def test_book_tickets(self):
        provider = CinemaProvider("http://localhost:8000")
        booking_data = {
            "id": 1,
            "booking_ref": "ABC123",
            "status": "confirmed",
            "total_price": 90.0,
        }

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=_mock_response(booking_data))
            mock_client.return_value = client

            result = await provider.book_tickets(
                showtime_id=1,
                num_tickets=2,
                customer_name="Test",
                customer_email="test@test.com",
            )

        assert result["booking_ref"] == "ABC123"

    @pytest.mark.asyncio
    async def test_connection_error(self):
        provider = CinemaProvider("http://localhost:8000")

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.return_value = client

            with pytest.raises(CinemaAPIError):
                await provider.get_cinemas()
