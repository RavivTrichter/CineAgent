"""Custom exceptions for the Cinema API service."""


class CinemaServiceError(Exception):
    """Base exception for all Cinema API errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ShowtimeNotFoundError(CinemaServiceError):
    def __init__(self, showtime_id: int):
        super().__init__(f"Showtime {showtime_id} not found", 404)


class CinemaNotFoundError(CinemaServiceError):
    def __init__(self, cinema_id: int):
        super().__init__(f"Cinema {cinema_id} not found", 404)


class FilmNotFoundError(CinemaServiceError):
    def __init__(self, film_id: int):
        super().__init__(f"Film {film_id} not found", 404)


class InsufficientSeatsError(CinemaServiceError):
    def __init__(self, available: int, requested: int):
        super().__init__(
            f"Only {available} seats available, {requested} requested", 409
        )


class InvalidBookingError(CinemaServiceError):
    def __init__(self, reason: str):
        super().__init__(f"Invalid booking: {reason}", 400)


class DatabaseError(CinemaServiceError):
    def __init__(self, detail: str):
        super().__init__(f"Database error: {detail}", 500)
