"""
S3-compatible blob storage module for Apache Ozone.

This module provides an implementation of the BlobStorageInterface for
S3-compatible storage systems, specifically targeting Apache Ozone S3 Gateway.
"""

from .storage import S3BlobStorage
from .client import create_s3_client

__all__ = ["S3BlobStorage", "create_s3_client"]
