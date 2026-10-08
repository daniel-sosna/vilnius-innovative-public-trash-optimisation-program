from pathlib import Path

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: str = Field(repr=False)
    bin_sync_source_url: HttpUrl
    bin_sync_http_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("database_url")
    @classmethod
    def require_psycopg_postgresql(cls, value: str) -> str:
        try:
            driver = make_url(value).drivername
        except ArgumentError:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from None
        if driver != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value
