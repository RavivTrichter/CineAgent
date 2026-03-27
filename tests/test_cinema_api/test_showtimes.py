"""Tests for showtime endpoints."""

import pytest


class TestListShowtimes:
    @pytest.mark.asyncio
    async def test_list_all_showtimes(self, cinema_client):
        resp = await cinema_client.get("/showtimes")
        assert resp.status_code == 200
        showtimes = resp.json()
        assert len(showtimes) > 0

    @pytest.mark.asyncio
    async def test_filter_by_film_id(self, cinema_client):
        resp = await cinema_client.get("/showtimes", params={"film_id": 1})
        assert resp.status_code == 200
        showtimes = resp.json()
        assert all(s["film_id"] == 1 for s in showtimes)

    @pytest.mark.asyncio
    async def test_filter_by_cinema_id(self, cinema_client):
        resp = await cinema_client.get("/showtimes", params={"cinema_id": 1})
        assert resp.status_code == 200
        showtimes = resp.json()
        assert all(s["cinema_id"] == 1 for s in showtimes)

    @pytest.mark.asyncio
    async def test_filter_combined(self, cinema_client):
        resp = await cinema_client.get(
            "/showtimes", params={"film_id": 1, "cinema_id": 1}
        )
        assert resp.status_code == 200
        showtimes = resp.json()
        for s in showtimes:
            assert s["film_id"] == 1
            assert s["cinema_id"] == 1


class TestGetShowtime:
    @pytest.mark.asyncio
    async def test_get_existing_showtime(self, cinema_client):
        # First get a valid showtime ID
        resp = await cinema_client.get("/showtimes")
        showtimes = resp.json()
        first_id = showtimes[0]["id"]

        resp = await cinema_client.get(f"/showtimes/{first_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == first_id
        assert "cinema_name" in resp.json()

    @pytest.mark.asyncio
    async def test_get_nonexistent_showtime(self, cinema_client):
        resp = await cinema_client.get("/showtimes/99999")
        assert resp.status_code == 404
