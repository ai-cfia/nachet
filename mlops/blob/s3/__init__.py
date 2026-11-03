"""
S3-compatible blob storage module for Apache Ozone.

This module provides an implementation of the BlobStorageInterface for
S3-compatible storage systems, specifically targeting Apache Ozone S3 Gateway.
"""

from blob_controller.s3.client import create_s3_client
from blob_controller.s3.storage import S3BlobStorage

__all__ = ["S3BlobStorage", "create_s3_client"]
