"""Configuration for the Cinema API service."""

from pydantic_settings import BaseSettings


class CinemaSettings(BaseSettings):
    database_path: str = "cinema.db"
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_prefix = "CINEMA_"
