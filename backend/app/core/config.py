from pathlib import Path
from string import Formatter
from urllib.parse import urlsplit

from pydantic import Field, field_validator
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
    vasa_tile_url_template: str = (
        "https://atliekuaiksteles.vasa.lt/api/cluster/{z}/{x}/{y}"
    )
    vasa_bin_url_template: str = (
        "https://atliekuaiksteles.vasa.lt/vasa-api/api/v1/dumpsters/{external_id}"
    )
    vasa_history_url_template: str = "https://atliekuaiksteles.vasa.lt/vasa-api/api/v1/dumpsters-service-history/{external_id}"
    vasa_schedule_url_template: str = (
        "https://atliekuaiksteles.vasa.lt/vasa-api/api/v1/dumpsters-schedule/{external_id}"
    )
    bin_sync_http_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)

    @field_validator(
        "vasa_tile_url_template",
        "vasa_bin_url_template",
        "vasa_history_url_template",
        "vasa_schedule_url_template",
    )
    @classmethod
    def require_https_template(cls, value: str, info) -> str:
        required = (
            {"z", "x", "y"}
            if info.field_name == "vasa_tile_url_template"
            else {"external_id"}
        )
        try:
            parts = list(Formatter().parse(value))
            fields = {field for _, field, _, _ in parts if field is not None}
            if fields != required or any(
                spec or conversion for _, _, spec, conversion in parts
            ):
                raise ValueError
            url = urlsplit(value.format(**{key: 1 for key in required}))
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username
                or url.password
                or url.fragment
            ):
                raise ValueError
        except (ValueError, KeyError, IndexError):
            raise ValueError(
                "VASA URL must use HTTPS and the documented placeholders, without credentials or fragments"
            ) from None
        return value

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


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class DataDirSettings(BaseSettings):
    """Only the data directory, so CLIs need no database settings to find their files."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    viptop_data_dir: str | None = None


def data_dir() -> Path:
    """Directory with the CSV exports and density file.

    `VIPTOP_DATA_DIR` (environment or root `.env`) when set, relative values
    resolved from the repository root as Compose does; otherwise `backend/data/`.
    Inside the backend container the variable is not set and `/app/data` is the
    mounted folder.
    """
    configured = DataDirSettings().viptop_data_dir
    if not configured:
        return BACKEND_DATA_DIR
    return (REPO_ROOT / configured).resolve()
