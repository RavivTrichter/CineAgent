"""Tests for OMDB provider."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from assistant.exceptions import OMDBError
from assistant.providers.omdb import OMDBProvider


def _mock_response(json_data, status_code=200):
    return httpx.Response(status_code, json=json_data, request=httpx.Request("GET", "http://test"))


class TestOMDBProvider:
    @pytest.mark.asyncio
    async def test_get_ratings_by_title(self):
        provider = OMDBProvider("test-key")
        mock_data = {
            "Response": "True",
            "Title": "Sinners",
            "Year": "2025",
            "Rated": "R",
            "Runtime": "137 min",
            "Genre": "Horror, Drama",
            "Director": "Ryan Coogler",
            "Actors": "Michael B. Jordan",
            "Plot": "A horror story",
            "Awards": "16 Oscar nominations",
            "BoxOffice": "$200,000,000",
            "imdbID": "tt1234567",
            "Ratings": [
                {"Source": "Internet Movie Database", "Value": "8.1/10"},
                {"Source": "Rotten Tomatoes", "Value": "92%"},
                {"Source": "Metacritic", "Value": "81/100"},
            ],
        }

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(mock_data))
            mock_client.return_value = client

            result = await provider.get_movie_ratings(title="Sinners")

        assert result["title"] == "Sinners"
        assert result["imdb_rating"] == "8.1/10"
        assert result["rotten_tomatoes"] == "92%"
        assert result["metacritic"] == "81/100"
        assert result["box_office"] == "$200,000,000"

    @pytest.mark.asyncio
    async def test_movie_not_found(self):
        provider = OMDBProvider("test-key")

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(
                return_value=_mock_response({"Response": "False", "Error": "Movie not found!"})
            )
            mock_client.return_value = client

            with pytest.raises(OMDBError, match="Movie not found"):
                await provider.get_movie_ratings(title="Nonexistent")

    @pytest.mark.asyncio
    async def test_no_params_raises_error(self):
        provider = OMDBProvider("test-key")
        with pytest.raises(OMDBError, match="Either title or imdb_id"):
            await provider.get_movie_ratings()

    @pytest.mark.asyncio
    async def test_get_ratings_by_imdb_id(self):
        provider = OMDBProvider("test-key")
        mock_data = {
            "Response": "True",
            "Title": "Sinners",
            "Year": "2025",
            "Ratings": [],
        }

        with patch.object(provider, "get_client") as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(mock_data))
            mock_client.return_value = client

            result = await provider.get_movie_ratings(imdb_id="tt1234567")

        assert result["title"] == "Sinners"
