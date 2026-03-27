"""Tests for film endpoints."""

import pytest


class TestListFilms:
    @pytest.mark.asyncio
    async def test_list_all_films(self, cinema_client):
        resp = await cinema_client.get("/films")
        assert resp.status_code == 200
        films = resp.json()
        assert len(films) == 10

    @pytest.mark.asyncio
    async def test_search_films(self, cinema_client):
        resp = await cinema_client.get("/films", params={"search": "Sinners"})
        assert resp.status_code == 200
        films = resp.json()
        assert len(films) == 1
        assert films[0]["title"] == "Sinners"

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, cinema_client):
        resp = await cinema_client.get("/films", params={"search": "sinners"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, cinema_client):
        resp = await cinema_client.get("/films", params={"search": "Nonexistent"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetFilm:
    @pytest.mark.asyncio
    async def test_get_existing_film(self, cinema_client):
        resp = await cinema_client.get("/films/1")
        assert resp.status_code == 200
        film = resp.json()
        assert film["id"] == 1
        assert film["title"] == "Sinners"

    @pytest.mark.asyncio
    async def test_get_nonexistent_film(self, cinema_client):
        resp = await cinema_client.get("/films/999")
        assert resp.status_code == 404
