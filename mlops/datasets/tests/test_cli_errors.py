"""Actionable configuration errors without exposing supplied credentials."""

from unittest.mock import AsyncMock

import pytest
from dataset_controller.config.dataset_config import Settings
from dataset_controller.errors import ConfigurationError
from dataset_controller.repositories.blob_repository import BlobStorageAdapter

from dataset_release import cli


def test_cli_reports_missing_database_setting(monkeypatch):
    monkeypatch.delenv("DATASET_DATABASE_URL", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args: None)
    with pytest.raises(SystemExit) as error:
        cli.main(["--container", "datasets", "inspect", "seeds", "v1"])
    assert (
        str(error.value) == "Dataset release failed: DATASET_DATABASE_URL is required"
    )


@pytest.mark.parametrize(
    ("setting", "value", "message"),
    [
        (
            "DATASET_DATABASE_URL",
            "secret-not-a-url",
            "DATASET_DATABASE_URL must be a valid SQLAlchemy database URL",
        ),
        (
            "DATASET_DATABASE_URL",
            "mysql://user:secret@localhost/db",
            "DATASET_DATABASE_URL must use postgresql+psycopg or sqlite+aiosqlite",
        ),
        (
            "DATASET_REGISTRY_SCHEMA",
            "secret;schema",
            "DATASET_REGISTRY_SCHEMA must be a lowercase PostgreSQL schema name",
        ),
        (
            "DATASET_BLOB_PROVIDER",
            "secret-provider",
            "DATASET_BLOB_PROVIDER must be s3 or azure",
        ),
        ("S3_VERIFY", "secret-value", "S3_VERIFY must be true or false"),
    ],
)
def test_cli_reports_safe_configuration_messages(monkeypatch, setting, value, message):
    monkeypatch.setenv("DATASET_DATABASE_URL", "postgresql+psycopg://user@localhost/db")
    monkeypatch.setenv("DATASET_REGISTRY_SCHEMA", "nachet_datasets")
    monkeypatch.setenv("DATASET_BLOB_PROVIDER", "s3")
    monkeypatch.delenv("S3_ACCESS_KEY", raising=False)
    monkeypatch.delenv("S3_SECRET_KEY", raising=False)
    monkeypatch.setenv(setting, value)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args: None)

    async def validate_configuration(args):
        Settings.from_environment()
        BlobStorageAdapter.from_environment()

    monkeypatch.setattr(cli, "execute", validate_configuration)
    with pytest.raises(SystemExit) as error:
        cli.main(["--container", "datasets", "inspect", "seeds", "v1"])
    assert str(error.value) == f"Dataset release failed: {message}"
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "error", [ValueError("password=secret"), RuntimeError("token=secret")]
)
def test_cli_keeps_unexpected_errors_redacted(monkeypatch, error):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args: None)
    monkeypatch.setattr(cli, "execute", AsyncMock(side_effect=error))
    with pytest.raises(SystemExit) as result:
        cli.main(["--container", "datasets", "inspect", "seeds", "v1"])
    assert str(result.value) == f"Dataset release failed: {type(error).__name__}"
    assert "secret" not in str(result.value)


def test_configuration_error_remains_a_value_error():
    assert isinstance(ConfigurationError("Safe configuration message"), ValueError)
