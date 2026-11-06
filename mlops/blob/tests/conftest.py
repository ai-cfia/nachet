"""Make copied live-service tests explicit; normal CI requires no credentials."""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        help="Run copied Azure/S3 service tests against configured test storage.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    skip_service = pytest.mark.skip(
        reason="Use --run-integration for live storage tests"
    )
    for item in items:
        if item.get_closest_marker("integration") and not config.getoption(
            "--run-integration"
        ):
            item.add_marker(skip_service)
