"""Showtime endpoints."""

from fastapi import APIRouter, Request

from cinema_api.exceptions import ShowtimeNotFoundError
from cinema_api.models import ShowtimeDetail

router = APIRouter(prefix="/showtimes", tags=["showtimes"])


@router.get("", response_model=list[ShowtimeDetail])
async def list_showtimes(
    request: Request,
    film_id: int | None = None,
    cinema_id: int | None = None,
    date: str | None = None,
):
    db = request.app.state.db
    query = """
        SELECT s.*, c.name as cinema_name
        FROM showtimes s
        JOIN cinemas c ON s.cinema_id = c.id
        WHERE 1=1
    """
    params: list = []

    if film_id:
        query += " AND s.film_id = ?"
        params.append(film_id)
    if cinema_id:
        query += " AND s.cinema_id = ?"
        params.append(cinema_id)
    if date:
        query += " AND DATE(s.start_time) = ?"
        params.append(date)

    query += " ORDER BY s.start_time"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/{showtime_id}", response_model=ShowtimeDetail)
async def get_showtime(request: Request, showtime_id: int):
    db = request.app.state.db
    cursor = await db.execute(
        """SELECT s.*, c.name as cinema_name
           FROM showtimes s
           JOIN cinemas c ON s.cinema_id = c.id
           WHERE s.id = ?""",
        (showtime_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise ShowtimeNotFoundError(showtime_id)
    return dict(row)
