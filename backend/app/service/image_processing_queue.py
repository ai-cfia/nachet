"""DBOS Queue definitions for image processing."""

from dbos import Queue

# Image processing queue with concurrency and rate limits
image_processing_queue = Queue(
    name="image-processing",
    concurrency=10,  # Max 10 concurrent workflows globally
    limiter={
        "limit": 50,  # Max 50 workflow starts
        "period": 60,  # Per 60 seconds
    },
    worker_concurrency=5,  # Max 5 concurrent per worker process
    partition_queue=True,  # Enable partitioning by org_id
)
