from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(hide_input_in_errors=True)

    database_url: str = Field(repr=False)
    bin_sync_source_url: HttpUrl = HttpUrl(
        "https://opencity.idvilnius.lt/gis/rest/services/"
        "Miesto_tvark/Miesto_tvarkymas_public/MapServer/29/query"
    )
    bin_sync_interval_seconds: float = Field(default=86_400, gt=0, allow_inf_nan=False)
    bin_sync_http_timeout_seconds: float = Field(default=30, gt=0, allow_inf_nan=False)

    @field_validator("database_url")
    @classmethod
    def require_psycopg_postgresql(cls, value: str) -> str:
        if make_url(value).drivername != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value
