import logging

import pytest

import progress_logging


@pytest.mark.parametrize(
    ("durations", "expected"),
    [
        ([10, 20], []),
        (
            [299, 1, 1, 298, 1, 300],
            ["Conversion progress: 2/6", "Conversion progress: 5/6"],
        ),
        ([900, 1], ["Conversion progress: 1/2"]),
    ],
)
def test_progress_logs_at_item_boundaries(monkeypatch, caplog, durations, expected):
    elapsed = 0
    monkeypatch.setattr(progress_logging, "monotonic", lambda: elapsed)
    logger = logging.getLogger(__name__)
    caplog.set_level(logging.INFO, logger=logger.name)

    for duration in progress_logging.log_progress(
        durations, logger, stage="Conversion", total=len(durations)
    ):
        elapsed += duration

    assert caplog.messages == expected
