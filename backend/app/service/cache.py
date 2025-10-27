"""
Generic Cache Service

Simple in-memory cache for application data to avoid repeated database queries.
Provides three core operations: store, retrieve, and update data structures.
"""

from beartype.typing import Dict, Any, Optional
from datetime import datetime, timedelta


class CacheService:
    """
    Global singleton cache for application data.

    Simple key-value store with namespace support and TTL (time-to-live).
    Domain-specific logic should be in the appropriate service layer.

    Cache Structure:
    {
        "pipelines": {
            "data": <any data structure>,
            "expires_at": <datetime>
        },
        "seeds": {
            "data": <any data structure>,
            "expires_at": <datetime>
        }
    }
    """

    # Global cache storage
    _cache: Dict[str, Dict[str, Any]] = {}

    # Default TTL: 5 minutes
    DEFAULT_TTL_SECONDS = 300

    @classmethod
    def set(cls, namespace: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Store data in a namespace with TTL.

        Args:
            namespace: Cache namespace (e.g., "pipelines", "models")
            data: Data to cache (any structure)
            ttl_seconds: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        if ttl_seconds is None:
            ttl_seconds = cls.DEFAULT_TTL_SECONDS

        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        cls._cache[namespace] = {"data": data, "expires_at": expires_at}

    @classmethod
    def get(cls, namespace: str) -> Optional[Any]:
        """
        Retrieve data from a namespace.

        Returns None if namespace doesn't exist or data has expired.

        Args:
            namespace: Cache namespace

        Returns:
            Cached data or None if not found or expired
        """
        if namespace not in cls._cache:
            return None

        cache_entry = cls._cache[namespace]

        # Check if expired
        if datetime.utcnow() > cache_entry["expires_at"]:
            # Auto-cleanup expired entry
            del cls._cache[namespace]
            return None

        return cache_entry["data"]

    @classmethod
    def update(
        cls, namespace: str, data: Any, ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Update data in a namespace with new TTL.

        Args:
            namespace: Cache namespace
            data: New data to cache
            ttl_seconds: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        cls.set(namespace, data, ttl_seconds)
