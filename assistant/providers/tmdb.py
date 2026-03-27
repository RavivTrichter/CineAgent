"""TMDB API provider for movie search and discovery."""

import logging

import httpx

from assistant.exceptions import TMDBError
from assistant.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class TMDBProvider(BaseProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.themoviedb.org/3"):
        super().__init__(base_url)
        self.api_key = api_key

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self._client

    async def search_movies(self, query: str, year: int | None = None) -> list[dict]:
        try:
            client = await self.get_client()
            params: dict = {"query": query}
            if year:
                params["year"] = year
            resp = await client.get("/search/movie", params=params)
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "id": m["id"],
                    "title": m["title"],
                    "overview": m.get("overview", ""),
                    "release_date": m.get("release_date", ""),
                    "vote_average": m.get("vote_average", 0),
                    "poster_path": m.get("poster_path"),
                }
                for m in data.get("results", [])[:10]
            ]
        except httpx.HTTPStatusError as e:
            raise TMDBError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TMDBError(f"Connection error: {e}") from e

    async def get_movie_details(self, movie_id: int) -> dict:
        try:
            client = await self.get_client()
            resp = await client.get(f"/movie/{movie_id}", params={"append_to_response": "credits"})
            resp.raise_for_status()
            m = resp.json()

            # Extract top cast
            cast = []
            for member in m.get("credits", {}).get("cast", [])[:8]:
                cast.append({"name": member["name"], "character": member.get("character", "")})

            # Extract director
            directors = [
                c["name"]
                for c in m.get("credits", {}).get("crew", [])
                if c.get("job") == "Director"
            ]

            return {
                "id": m["id"],
                "title": m["title"],
                "overview": m.get("overview", ""),
                "release_date": m.get("release_date", ""),
                "runtime": m.get("runtime"),
                "genres": [g["name"] for g in m.get("genres", [])],
                "vote_average": m.get("vote_average", 0),
                "budget": m.get("budget", 0),
                "revenue": m.get("revenue", 0),
                "tagline": m.get("tagline", ""),
                "poster_path": m.get("poster_path"),
                "imdb_id": m.get("imdb_id"),
                "cast": cast,
                "directors": directors,
            }
        except httpx.HTTPStatusError as e:
            raise TMDBError(f"HTTP {e.response.status_code} for movie {movie_id}") from e
        except httpx.RequestError as e:
            raise TMDBError(f"Connection error: {e}") from e

    async def get_similar_movies(self, movie_id: int) -> list[dict]:
        try:
            client = await self.get_client()
            resp = await client.get(f"/movie/{movie_id}/similar")
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "id": m["id"],
                    "title": m["title"],
                    "overview": m.get("overview", ""),
                    "release_date": m.get("release_date", ""),
                    "vote_average": m.get("vote_average", 0),
                }
                for m in data.get("results", [])[:10]
            ]
        except httpx.HTTPStatusError as e:
            raise TMDBError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TMDBError(f"Connection error: {e}") from e

    async def get_trending_movies(self, time_window: str = "week") -> list[dict]:
        try:
            client = await self.get_client()
            resp = await client.get(f"/trending/movie/{time_window}")
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "id": m["id"],
                    "title": m["title"],
                    "overview": m.get("overview", ""),
                    "release_date": m.get("release_date", ""),
                    "vote_average": m.get("vote_average", 0),
                }
                for m in data.get("results", [])[:10]
            ]
        except httpx.HTTPStatusError as e:
            raise TMDBError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TMDBError(f"Connection error: {e}") from e
