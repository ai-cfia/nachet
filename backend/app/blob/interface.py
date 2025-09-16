"""
Abstract base classes and interfaces for blob storage providers.

This module defines the contract that all blob storage implementations must follow,
ensuring consistency across different cloud storage providers.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Union, BinaryIO, Dict, Any
from datetime import timedelta


class BlobStorageInterface(ABC):
    """Abstract base class for blob storage providers."""

    @abstractmethod
    async def upload_blob(
        self, container: str, name: str, data: Union[bytes, str, BinaryIO], **kwargs
    ) -> Dict[str, Any]:
        """Upload a blob to storage."""
        pass

    @abstractmethod
    async def download_blob(self, container: str, name: str, **kwargs) -> bytes:
        """Download a blob from storage."""
        pass

    @abstractmethod
    async def download_blob_stream(
        self, container: str, name: str, **kwargs
    ) -> AsyncIterator[bytes]:
        """Download a blob as a stream."""
        pass

    @abstractmethod
    async def delete_blob(self, container: str, name: str) -> bool:
        """Delete a blob from storage."""
        pass

    @abstractmethod
    async def blob_exists(self, container: str, name: str) -> bool:
        """Check if a blob exists."""
        pass

    @abstractmethod
    async def get_blob_properties(self, container: str, name: str) -> Dict[str, Any]:
        """Get detailed properties of a blob."""
        pass

    @abstractmethod
    async def list_blobs(self, container: str, **kwargs) -> Dict[str, Any]:
        """List blobs in a container."""
        pass

    @abstractmethod
    async def copy_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Copy a blob within or across containers."""
        pass

    @abstractmethod
    async def move_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Move a blob within or across containers."""
        pass

    # Container operations
    @abstractmethod
    async def create_container(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new container."""
        pass

    @abstractmethod
    async def delete_container(self, name: str) -> bool:
        """Delete a container."""
        pass

    @abstractmethod
    async def container_exists(self, name: str) -> bool:
        """Check if a container exists."""
        pass

    @abstractmethod
    async def list_containers(self, **kwargs) -> Dict[str, Any]:
        """List all containers."""
        pass

    @abstractmethod
    async def get_container_properties(self, name: str) -> Dict[str, Any]:
        """Get properties of a container."""
        pass

    # Security and access control
    @abstractmethod
    async def generate_sas_token(
        self,
        container: str,
        name: str,
        permissions: List[str],
        expiry: timedelta,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a SAS token for a specific blob."""
        pass

    @abstractmethod
    async def generate_container_sas_token(
        self, container: str, permissions: List[str], expiry: timedelta, **kwargs
    ) -> Dict[str, Any]:
        """Generate a SAS token for a container."""
        pass

    # Metadata operations
    @abstractmethod
    async def set_blob_metadata(
        self, container: str, name: str, metadata: Dict[str, str]
    ) -> None:
        """Set metadata for a blob."""
        pass

    @abstractmethod
    async def get_blob_metadata(self, container: str, name: str) -> Dict[str, str]:
        """Get metadata for a blob."""
        pass

    @abstractmethod
    async def set_blob_tags(
        self, container: str, name: str, tags: Dict[str, str]
    ) -> None:
        """Set tags for a blob."""
        pass

    @abstractmethod
    async def get_blob_tags(self, container: str, name: str) -> Dict[str, str]:
        """Get tags for a blob."""
        pass

    # Utility methods
    @abstractmethod
    async def get_blob_url(self, container: str, name: str, **kwargs) -> str:
        """Get the URL for a blob."""
        pass

    @abstractmethod
    async def set_blob_tier(
        self, container: str, name: str, tier: str, **kwargs
    ) -> bool:
        """Set the access tier for a blob (Hot, Cool)."""
        pass
