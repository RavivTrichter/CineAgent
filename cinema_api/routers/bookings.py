"""Booking endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from cinema_api.exceptions import (
    InsufficientSeatsError,
    InvalidBookingError,
    ShowtimeNotFoundError,
)
from cinema_api.models import BookingRequest, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse)
async def create_booking(request: Request, booking: BookingRequest):
    db = request.app.state.db

    # Check showtime exists and has enough seats
    cursor = await db.execute(
        """SELECT s.*, c.name as cinema_name
           FROM showtimes s
           JOIN cinemas c ON s.cinema_id = c.id
           WHERE s.id = ?""",
        (booking.showtime_id,),
    )
    showtime = await cursor.fetchone()
    if not showtime:
        raise ShowtimeNotFoundError(booking.showtime_id)

    if showtime["available_seats"] < booking.num_tickets:
        raise InsufficientSeatsError(showtime["available_seats"], booking.num_tickets)

    if not booking.customer_email or "@" not in booking.customer_email:
        raise InvalidBookingError("Invalid email address")

    # Transactional: decrement seats and create booking
    total_price = showtime["price_ils"] * booking.num_tickets
    booking_ref = str(uuid.uuid4())[:8].upper()
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "UPDATE showtimes SET available_seats = available_seats - ? WHERE id = ?",
        (booking.num_tickets, booking.showtime_id),
    )

    cursor = await db.execute(
        """INSERT INTO bookings
           (showtime_id, num_tickets, customer_name, customer_email, total_price, booking_ref, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?)""",
        (
            booking.showtime_id,
            booking.num_tickets,
            booking.customer_name,
            booking.customer_email,
            total_price,
            booking_ref,
            now,
        ),
    )
    await db.commit()

    return BookingResponse(
        id=cursor.lastrowid,
        showtime_id=booking.showtime_id,
        num_tickets=booking.num_tickets,
        customer_name=booking.customer_name,
        customer_email=booking.customer_email,
        total_price=total_price,
        booking_ref=booking_ref,
        status="confirmed",
        created_at=datetime.fromisoformat(now),
        movie_title=showtime["movie_title"],
        cinema_name=showtime["cinema_name"],
        start_time=datetime.fromisoformat(showtime["start_time"]),
    )


@router.get("/{booking_ref}", response_model=BookingResponse)
async def get_booking(request: Request, booking_ref: str):
    db = request.app.state.db
    cursor = await db.execute(
        """SELECT b.*, s.movie_title, c.name as cinema_name, s.start_time
           FROM bookings b
           JOIN showtimes s ON b.showtime_id = s.id
           JOIN cinemas c ON s.cinema_id = c.id
           WHERE b.booking_ref = ?""",
        (booking_ref,),
    )
    row = await cursor.fetchone()
    if not row:
        raise InvalidBookingError(f"Booking {booking_ref} not found")
    return dict(row)
