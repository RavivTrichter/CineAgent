"""Tests for TMDB provider."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from assistant.exceptions import TMDBError
from assistant.providers.tmdb import TMDBProvider


def _mock_response(json_data, status_code=200):
    resp = httpx.Response(status_code, json=json_data, request=httpx.Request("GET", "http://test"))
    return resp


class TestTMDBProvider:
    @pytest.mark.asyncio
    async def test_search_movies(self):
        provider = TMDBProvider("test-key")
        mock_data = {
            "results": [
                {
                    "id": 1,
                    "title": "Sinners",
                    "overview": "A horror film",
                    "release_date": "2025-04-18",
                    "vote_average": 8.0,
                    "poster_path": "/poster.jpg",
                }
            ]
        }

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(mock_data))
            mock_client.return_value = client

            results = await provider.search_movies("Sinners")

        assert len(results) == 1
        assert results[0]["title"] == "Sinners"
        assert results[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_search_movies_with_year(self):
        provider = TMDBProvider("test-key")

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response({"results": []}))
            mock_client.return_value = client

            results = await provider.search_movies("Sinners", year=2025)

        assert results == []
        client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_movie_details(self):
        provider = TMDBProvider("test-key")
        mock_data = {
            "id": 1,
            "title": "Sinners",
            "overview": "Horror",
            "release_date": "2025-04-18",
            "runtime": 137,
            "genres": [{"id": 27, "name": "Horror"}],
            "vote_average": 8.0,
            "budget": 90000000,
            "revenue": 300000000,
            "tagline": "A tagline",
            "poster_path": "/poster.jpg",
            "imdb_id": "tt1234567",
            "credits": {
                "cast": [{"name": "Actor 1", "character": "Role 1"}],
                "crew": [{"name": "Director 1", "job": "Director"}],
            },
        }

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(mock_data))
            mock_client.return_value = client

            result = await provider.get_movie_details(1)

        assert result["title"] == "Sinners"
        assert result["directors"] == ["Director 1"]
        assert len(result["cast"]) == 1

    @pytest.mark.asyncio
    async def test_http_error_raises_tmdb_error(self):
        provider = TMDBProvider("test-key")

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            error_resp = httpx.Response(404, request=httpx.Request("GET", "http://test"))
            client.get = AsyncMock(side_effect=httpx.HTTPStatusError("Not found", request=error_resp.request, response=error_resp))
            mock_client.return_value = client

            with pytest.raises(TMDBError):
                await provider.search_movies("Nonexistent")

    @pytest.mark.asyncio
    async def test_connection_error_raises_tmdb_error(self):
        provider = TMDBProvider("test-key")

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.return_value = client

            with pytest.raises(TMDBError):
                await provider.search_movies("Sinners")
