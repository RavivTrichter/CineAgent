"""Tests for cinema endpoints."""

import pytest


class TestListCinemas:
    @pytest.mark.asyncio
    async def test_list_all_cinemas(self, cinema_client):
        resp = await cinema_client.get("/cinemas")
        assert resp.status_code == 200
        cinemas = resp.json()
        assert len(cinemas) == 4
        assert all("name" in c for c in cinemas)

    @pytest.mark.asyncio
    async def test_filter_by_city(self, cinema_client):
        resp = await cinema_client.get("/cinemas", params={"city": "Tel Aviv"})
        assert resp.status_code == 200
        cinemas = resp.json()
        assert len(cinemas) >= 1
        assert all("Tel Aviv" in c["city"] for c in cinemas)

    @pytest.mark.asyncio
    async def test_filter_no_results(self, cinema_client):
        resp = await cinema_client.get("/cinemas", params={"city": "Nowhere"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetCinema:
    @pytest.mark.asyncio
    async def test_get_existing_cinema(self, cinema_client):
        resp = await cinema_client.get("/cinemas/1")
        assert resp.status_code == 200
        cinema = resp.json()
        assert cinema["id"] == 1
        assert "name" in cinema

    @pytest.mark.asyncio
    async def test_get_nonexistent_cinema(self, cinema_client):
        resp = await cinema_client.get("/cinemas/999")
        assert resp.status_code == 404
        assert "error" in resp.json()
