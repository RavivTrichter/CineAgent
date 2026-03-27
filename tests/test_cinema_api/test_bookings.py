"""Tests for booking endpoints."""

import pytest


class TestCreateBooking:
    @pytest.mark.asyncio
    async def test_successful_booking(self, cinema_client):
        # Get a showtime
        resp = await cinema_client.get("/showtimes")
        showtime = resp.json()[0]

        resp = await cinema_client.post(
            "/bookings",
            json={
                "showtime_id": showtime["id"],
                "num_tickets": 2,
                "customer_name": "Test User",
                "customer_email": "test@example.com",
            },
        )
        assert resp.status_code == 200
        booking = resp.json()
        assert booking["num_tickets"] == 2
        assert booking["status"] == "confirmed"
        assert "booking_ref" in booking
        assert booking["total_price"] == showtime["price_ils"] * 2

    @pytest.mark.asyncio
    async def test_booking_decrements_seats(self, cinema_client):
        # Get a showtime and note seats
        resp = await cinema_client.get("/showtimes")
        showtime = resp.json()[0]
        original_seats = showtime["available_seats"]

        await cinema_client.post(
            "/bookings",
            json={
                "showtime_id": showtime["id"],
                "num_tickets": 3,
                "customer_name": "Test User",
                "customer_email": "test@example.com",
            },
        )

        # Check seats decreased
        resp = await cinema_client.get(f"/showtimes/{showtime['id']}")
        assert resp.json()["available_seats"] == original_seats - 3

    @pytest.mark.asyncio
    async def test_insufficient_seats(self, cinema_client):
        resp = await cinema_client.get("/showtimes")
        showtime = resp.json()[0]

        resp = await cinema_client.post(
            "/bookings",
            json={
                "showtime_id": showtime["id"],
                "num_tickets": 9999,
                "customer_name": "Test User",
                "customer_email": "test@example.com",
            },
        )
        assert resp.status_code == 422  # Pydantic validation (max 10 tickets)

    @pytest.mark.asyncio
    async def test_nonexistent_showtime(self, cinema_client):
        resp = await cinema_client.post(
            "/bookings",
            json={
                "showtime_id": 99999,
                "num_tickets": 1,
                "customer_name": "Test User",
                "customer_email": "test@example.com",
            },
        )
        assert resp.status_code == 404


class TestGetBooking:
    @pytest.mark.asyncio
    async def test_get_booking_by_ref(self, cinema_client):
        # Create a booking first
        resp = await cinema_client.get("/showtimes")
        showtime = resp.json()[0]

        resp = await cinema_client.post(
            "/bookings",
            json={
                "showtime_id": showtime["id"],
                "num_tickets": 1,
                "customer_name": "Lookup Test",
                "customer_email": "lookup@example.com",
            },
        )
        booking_ref = resp.json()["booking_ref"]

        resp = await cinema_client.get(f"/bookings/{booking_ref}")
        assert resp.status_code == 200
        assert resp.json()["booking_ref"] == booking_ref

    @pytest.mark.asyncio
    async def test_get_nonexistent_booking(self, cinema_client):
        resp = await cinema_client.get("/bookings/NONEXIST")
        assert resp.status_code == 400
