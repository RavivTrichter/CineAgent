"""Film endpoints."""

from fastapi import APIRouter, Request

from cinema_api.exceptions import FilmNotFoundError
from cinema_api.models import Film

router = APIRouter(prefix="/films", tags=["films"])


@router.get("", response_model=list[Film])
async def list_films(request: Request, search: str | None = None):
    db = request.app.state.db
    if search:
        cursor = await db.execute(
            "SELECT * FROM films WHERE LOWER(title) LIKE LOWER(?)",
            (f"%{search}%",),
        )
    else:
        cursor = await db.execute("SELECT * FROM films")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/{film_id}", response_model=Film)
async def get_film(request: Request, film_id: int):
    db = request.app.state.db
    cursor = await db.execute("SELECT * FROM films WHERE id = ?", (film_id,))
    row = await cursor.fetchone()
    if not row:
        raise FilmNotFoundError(film_id)
    return dict(row)
