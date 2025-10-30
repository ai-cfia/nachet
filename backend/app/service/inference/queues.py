"""
DBOS Queue Configuration

This module defines DBOS queue configurations for image processing workflows.
Queues handle concurrency limits, rate limiting, and partitioning.
"""

from dbos import Queue


# Image processing queue with sequential processing (FIFO)
image_processing_queue = Queue(
    name="image-processing",
    concurrency=10,  # Process one workflow at a time globally
    limiter={
        "limit": 50,  # Max 50 workflow starts
        "period": 60,  # Per 60 seconds
    },
    worker_concurrency=10,  # Process one workflow at a time per worker
    partition_queue=False,  # Disable partitioning - process in submission order
)
