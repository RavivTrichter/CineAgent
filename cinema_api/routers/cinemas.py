"""Cinema endpoints."""

from fastapi import APIRouter, Request

from cinema_api.exceptions import CinemaNotFoundError
from cinema_api.models import Cinema

router = APIRouter(prefix="/cinemas", tags=["cinemas"])


@router.get("", response_model=list[Cinema])
async def list_cinemas(request: Request, city: str | None = None):
    db = request.app.state.db
    if city:
        cursor = await db.execute(
            "SELECT * FROM cinemas WHERE LOWER(city) LIKE LOWER(?)",
            (f"%{city}%",),
        )
    else:
        cursor = await db.execute("SELECT * FROM cinemas")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/{cinema_id}", response_model=Cinema)
async def get_cinema(request: Request, cinema_id: int):
    db = request.app.state.db
    cursor = await db.execute("SELECT * FROM cinemas WHERE id = ?", (cinema_id,))
    row = await cursor.fetchone()
    if not row:
        raise CinemaNotFoundError(cinema_id)
    return dict(row)
