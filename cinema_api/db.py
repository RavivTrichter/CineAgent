"""Database setup and seed data for the Cinema API."""

import calendar
import random
from datetime import date, datetime, timedelta

import aiosqlite

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS cinemas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    year INTEGER NOT NULL,
    tmdb_id INTEGER,
    imdb_id TEXT,
    genre TEXT NOT NULL,
    runtime_minutes INTEGER,
    poster_url TEXT,
    oscar_nominations INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS showtimes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cinema_id INTEGER NOT NULL,
    film_id INTEGER NOT NULL,
    movie_title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    price_ils REAL NOT NULL,
    hall TEXT NOT NULL,
    available_seats INTEGER NOT NULL,
    total_seats INTEGER NOT NULL,
    FOREIGN KEY (cinema_id) REFERENCES cinemas(id),
    FOREIGN KEY (film_id) REFERENCES films(id)
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    showtime_id INTEGER NOT NULL,
    num_tickets INTEGER NOT NULL,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    total_price REAL NOT NULL,
    booking_ref TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'confirmed',
    created_at TEXT NOT NULL,
    FOREIGN KEY (showtime_id) REFERENCES showtimes(id)
);
"""

SEED_CINEMAS = [
    ("Yes Planet Rishon LeZion", "Rothschild 50, Rishon LeZion", "Rishon LeZion", 31.9642, 34.8044),
    ("Cinema City Glilot", "Glilot Junction, Ramat HaSharon", "Ramat HaSharon", 32.1489, 34.7937),
    ("Lev Dizengoff", "Dizengoff 50, Tel Aviv", "Tel Aviv", 32.0753, 34.7748),
    ("Hot Cinema Ramat Aviv", "Einstein 40, Ramat Aviv", "Tel Aviv", 32.1133, 34.7983),
]

SEED_FILMS = [
    ("Sinners", 2025, None, None, "Horror, Drama", 137, 16),
    ("One Battle After Another", 2025, None, None, "Drama, War", 130, 13),
    ("Frankenstein", 2025, None, None, "Horror, Sci-Fi", 125, 9),
    ("Sentimental Value", 2025, None, None, "Comedy, Drama", 115, 9),
    ("Marty Supreme", 2025, None, None, "Drama, Biography", 120, 9),
    ("Hamnet", 2025, None, None, "Drama, History", 118, 8),
    ("Bugonia", 2025, None, None, "Sci-Fi, Thriller", 110, 0),
    ("F1", 2025, None, None, "Action, Drama, Sport", 135, 0),
    ("The Secret Agent", 2025, None, None, "Thriller, Drama", 112, 0),
    ("Train Dreams", 2025, None, None, "Drama, Western", 105, 0),
]

HALLS = ["Hall 1", "Hall 2", "Hall 3", "Hall 4", "Hall 5", "Hall 6", "Hall 7", "Hall 8"]
PRICES = [35.0, 39.0, 42.0, 45.0, 49.0, 55.0]
SHOW_HOURS = [(10, 30), (13, 0), (16, 0), (19, 0), (21, 30)]


async def init_db(db_path: str) -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()


async def seed_db(db_path: str) -> None:
    """Seed cinemas/films once; extend showtimes to cover through end of month."""
    async with aiosqlite.connect(db_path) as db:
        # Seed cinemas and films only if the DB is empty
        cursor = await db.execute("SELECT COUNT(*) FROM cinemas")
        row = await cursor.fetchone()
        if row[0] == 0:
            await db.executemany(
                "INSERT INTO cinemas (name, address, city, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
                SEED_CINEMAS,
            )
            await db.executemany(
                "INSERT INTO films (title, year, tmdb_id, imdb_id, genre, runtime_minutes, oscar_nominations) VALUES (?, ?, ?, ?, ?, ?, ?)",
                SEED_FILMS,
            )

        today = date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_of_month = date(today.year, today.month, last_day)

        # Find the last date that already has showtimes
        cursor = await db.execute("SELECT MAX(DATE(start_time)) FROM showtimes")
        row = await cursor.fetchone()
        last_covered = date.fromisoformat(row[0]) if row[0] else today - timedelta(days=1)

        # If already covered through end of month, nothing to do
        if last_covered >= end_of_month:
            await db.commit()
            return

        # Generate showtimes only for uncovered dates
        start_from = max(today, last_covered + timedelta(days=1))

        cursor = await db.execute("SELECT id FROM cinemas")
        cinema_ids = [row[0] for row in await cursor.fetchall()]

        cursor = await db.execute("SELECT id, title FROM films")
        films = await cursor.fetchall()

        current_date = start_from
        while current_date <= end_of_month:
            # Deterministic seed per date so results don't depend on startup day
            random.seed(42 + current_date.toordinal())

            for cinema_id in cinema_ids:
                for film_id, film_title in films:
                    # 1-2 showtimes per film per cinema per day
                    num_shows = random.randint(1, 2)
                    chosen_hours = random.sample(SHOW_HOURS, k=num_shows)

                    for hour, minute in chosen_hours:
                        start_time = datetime(
                            current_date.year, current_date.month, current_date.day,
                            hour, minute,
                        )
                        price = random.choice(PRICES)
                        hall = random.choice(HALLS)
                        total_seats = random.choice([80, 120, 150, 200])
                        available_seats = random.randint(
                            max(5, total_seats // 5), total_seats
                        )

                        await db.execute(
                            """INSERT INTO showtimes
                               (cinema_id, film_id, movie_title, start_time, price_ils, hall, available_seats, total_seats)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                cinema_id,
                                film_id,
                                film_title,
                                start_time.isoformat(),
                                price,
                                hall,
                                available_seats,
                                total_seats,
                            ),
                        )

            current_date += timedelta(days=1)

        await db.commit()


async def get_db(db_path: str) -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db
