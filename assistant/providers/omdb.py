"""OMDB API provider for movie ratings, box office, and awards."""

import logging

import httpx

from assistant.exceptions import OMDBError
from assistant.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class OMDBProvider(BaseProvider):
    def __init__(self, api_key: str, base_url: str = "http://www.omdbapi.com"):
        super().__init__(base_url)
        self.api_key = api_key

    async def get_movie_ratings(
        self, title: str | None = None, imdb_id: str | None = None
    ) -> dict:
        try:
            client = await self.get_client()
            params: dict = {"apikey": self.api_key}
            if imdb_id:
                params["i"] = imdb_id
            elif title:
                params["t"] = title
            else:
                raise OMDBError("Either title or imdb_id must be provided")

            resp = await client.get("/", params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("Response") == "False":
                raise OMDBError(data.get("Error", "Movie not found"))

            # Normalize ratings
            ratings = {}
            for r in data.get("Ratings", []):
                source = r["Source"]
                if source == "Internet Movie Database":
                    ratings["imdb_rating"] = r["Value"]
                elif source == "Rotten Tomatoes":
                    ratings["rotten_tomatoes"] = r["Value"]
                elif source == "Metacritic":
                    ratings["metacritic"] = r["Value"]

            return {
                "title": data.get("Title", ""),
                "year": data.get("Year", ""),
                "rated": data.get("Rated", ""),
                "runtime": data.get("Runtime", ""),
                "genre": data.get("Genre", ""),
                "director": data.get("Director", ""),
                "actors": data.get("Actors", ""),
                "plot": data.get("Plot", ""),
                "awards": data.get("Awards", ""),
                "box_office": data.get("BoxOffice", "N/A"),
                "imdb_id": data.get("imdbID", ""),
                **ratings,
            }
        except httpx.HTTPStatusError as e:
            raise OMDBError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise OMDBError(f"Connection error: {e}") from e
