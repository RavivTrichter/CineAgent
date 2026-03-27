"""Pydantic models for the Cinema API."""

from datetime import datetime
from pydantic import BaseModel, Field


class Cinema(BaseModel):
    id: int
    name: str
    address: str
    city: str
    latitude: float
    longitude: float


class Film(BaseModel):
    id: int
    title: str
    year: int
    tmdb_id: int | None = None
    imdb_id: str | None = None
    genre: str
    runtime_minutes: int | None = None
    poster_url: str | None = None
    oscar_nominations: int = 0


class Showtime(BaseModel):
    id: int
    cinema_id: int
    film_id: int
    movie_title: str
    start_time: datetime
    price_ils: float
    hall: str
    available_seats: int
    total_seats: int


class ShowtimeDetail(BaseModel):
    id: int
    cinema_id: int
    cinema_name: str
    film_id: int
    movie_title: str
    start_time: datetime
    price_ils: float
    hall: str
    available_seats: int
    total_seats: int


class BookingRequest(BaseModel):
    showtime_id: int
    num_tickets: int = Field(gt=0, le=10)
    customer_name: str = Field(min_length=1)
    customer_email: str = Field(min_length=1)


class BookingResponse(BaseModel):
    id: int
    showtime_id: int
    num_tickets: int
    customer_name: str
    customer_email: str
    total_price: float
    booking_ref: str
    status: str
    created_at: datetime
    movie_title: str | None = None
    cinema_name: str | None = None
    start_time: datetime | None = None
