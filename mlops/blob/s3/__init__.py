"""
S3-compatible blob storage module for Apache Ozone.

This module provides an implementation of the BlobStorageInterface for
S3-compatible storage systems, specifically targeting Apache Ozone S3 Gateway.
"""

from app.blob.s3.storage import S3BlobStorage
from app.blob.s3.client import create_s3_client

__all__ = ["S3BlobStorage", "create_s3_client"]
