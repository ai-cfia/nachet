"""Periodic INFO logs for preparation loops."""

from collections.abc import Iterable, Iterator
from logging import Logger
from time import monotonic

PROGRESS_INTERVAL_SECONDS = 300


def log_progress[Item](
    items: Iterable[Item], logger: Logger, *, stage: str, total: int
) -> Iterator[Item]:
    """Report items handled between iterations, leaving the final count to the caller."""
    last_report = monotonic()
    for completed, item in enumerate(items):
        if completed:
            now = monotonic()
            if now - last_report >= PROGRESS_INTERVAL_SECONDS:
                logger.info("%s progress: %d/%d", stage, completed, total)
                last_report = now
        yield item
