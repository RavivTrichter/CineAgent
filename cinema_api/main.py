"""Cinema API — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cinema_api.config import CinemaSettings
from cinema_api.db import get_db, init_db, seed_db
from cinema_api.exceptions import CinemaServiceError
from cinema_api.routers import bookings, cinemas, films, showtimes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = CinemaSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Cinema API — initializing database...")
    await init_db(settings.database_path)
    await seed_db(settings.database_path)
    app.state.db = await get_db(settings.database_path)
    logger.info("Cinema API ready.")
    yield
    await app.state.db.close()
    logger.info("Cinema API shut down.")


app = FastAPI(title="Cinema API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(CinemaServiceError)
async def cinema_error_handler(request: Request, exc: CinemaServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )


app.include_router(cinemas.router)
app.include_router(films.router)
app.include_router(showtimes.router)
app.include_router(bookings.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cinema-api"}
