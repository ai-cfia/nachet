"""
Pydantic models for blob storage operations.

This module defines the data models used throughout the blob storage interface,
providing validation, serialization, and type safety for all blob operations.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Dict, List, Optional
import re


class BlobInfo(BaseModel):
    """Information about a blob in storage."""

    name: str = Field(..., description="Name of the blob")
    container: str = Field(..., description="Container name")
    size: int = Field(..., ge=0, description="Blob size in bytes")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    etag: str = Field(..., description="Entity tag for the blob")
    content_type: str = Field(..., description="MIME content type")
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Custom metadata"
    )
    tags: Dict[str, str] = Field(default_factory=dict, description="Blob tags")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate blob name is not empty."""
        if not v or v.strip() == "":
            raise ValueError("Blob name cannot be empty")
        return v.strip()

    @field_validator("container")
    @classmethod
    def validate_container(cls, v):
        """Validate container name follows Azure naming rules."""
        if not v or v.strip() == "":
            raise ValueError("Container name cannot be empty")
        return v.strip().lower()


class ContainerInfo(BaseModel):
    """Information about a container in storage."""

    name: str = Field(..., description="Container name")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    etag: str = Field(..., description="Entity tag for the container")
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Custom metadata"
    )
    public_access: Optional[str] = Field(None, description="Public access level")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate container name follows Azure naming rules."""
        if not v or v.strip() == "":
            raise ValueError("Container name cannot be empty")

        # Azure container naming rules:
        # - Must be lowercase
        # - 3-63 characters
        # - Start with letter or number
        # - Can contain letters, numbers, and hyphens
        # - Cannot have consecutive hyphens
        # - Cannot end with hyphen
        v = v.strip().lower()

        if not (3 <= len(v) <= 63):
            raise ValueError("Container name must be between 3 and 63 characters")

        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", v):
            raise ValueError(
                "Container name must start and end with alphanumeric characters "
                "and can only contain lowercase letters, numbers, and hyphens"
            )

        if "--" in v:
            raise ValueError("Container name cannot contain consecutive hyphens")

        return v


class UploadResult(BaseModel):
    """Result of a blob upload operation."""

    container: str = Field(..., description="Container name")
    name: str = Field(..., description="Blob name")
    etag: str = Field(..., description="Entity tag from upload")
    last_modified: datetime = Field(..., description="Upload timestamp")
    url: str = Field(..., description="Blob URL")
    size: int = Field(..., ge=0, description="Uploaded blob size in bytes")
    content_md5: Optional[str] = Field(None, description="MD5 hash of the content")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must be a valid HTTP/HTTPS URL")
        return v


class BlobListResult(BaseModel):
    """Result of a blob listing operation."""

    blobs: List[BlobInfo] = Field(..., description="List of blobs")
    continuation_token: Optional[str] = Field(None, description="Token for pagination")
    prefix: Optional[str] = Field(None, description="Filter prefix used")
    container: str = Field(..., description="Container name")
    total_count: Optional[int] = Field(None, ge=0, description="Total number of blobs")


class ContainerListResult(BaseModel):
    """Result of a container listing operation."""

    containers: List[ContainerInfo] = Field(..., description="List of containers")
    continuation_token: Optional[str] = Field(None, description="Token for pagination")
    total_count: Optional[int] = Field(
        None, ge=0, description="Total number of containers"
    )


class SASTokenInfo(BaseModel):
    """Information about a generated SAS token."""

    token: str = Field(..., description="The SAS token")
    url: str = Field(..., description="Full URL with SAS token")
    expiry: datetime = Field(..., description="Token expiration time")
    permissions: List[str] = Field(..., description="Granted permissions")

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v):
        """Validate SAS permissions."""
        valid_permissions = {
            "read",
            "write",
            "delete",
            "list",
            "add",
            "create",
            "update",
            "tag",
            "filter_by_tag",
        }
        for perm in v:
            if perm not in valid_permissions:
                raise ValueError(f"Invalid permission: {perm}")
        return v


class BlobProperties(BaseModel):
    """Extended properties of a blob."""

    name: str = Field(..., description="Blob name")
    container: str = Field(..., description="Container name")
    size: int = Field(..., ge=0, description="Blob size in bytes")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    creation_time: Optional[datetime] = Field(
        None, description="Blob creation timestamp"
    )
    etag: str = Field(..., description="Entity tag")
    content_type: str = Field(..., description="MIME content type")
    content_encoding: Optional[str] = Field(None, description="Content encoding")
    content_language: Optional[str] = Field(None, description="Content language")
    cache_control: Optional[str] = Field(None, description="Cache control header")
    content_disposition: Optional[str] = Field(
        None, description="Content disposition header"
    )
    content_md5: Optional[str] = Field(None, description="MD5 hash of content")
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Custom metadata"
    )
    tags: Dict[str, str] = Field(default_factory=dict, description="Blob tags")
    blob_type: str = Field(
        ..., description="Type of blob (BlockBlob, PageBlob, AppendBlob)"
    )
    lease_status: Optional[str] = Field(None, description="Lease status")
    lease_state: Optional[str] = Field(None, description="Lease state")
    server_encrypted: Optional[bool] = Field(
        None, description="Whether blob is encrypted on server"
    )
    blob_tier: Optional[str] = Field(None, description="Access tier (Hot, Cool)")
    blob_tier_change_time: Optional[datetime] = Field(
        None, description="Timestamp when tier was last changed"
    )
    blob_tier_inferred: Optional[bool] = Field(
        None, description="Whether tier was inferred or explicitly set"
    )
    last_accessed_on: Optional[datetime] = Field(
        None, description="Last access timestamp for lifecycle management"
    )


class UploadOptions(BaseModel):
    """Options for blob upload operations."""

    content_type: Optional[str] = Field(None, description="MIME content type")
    content_encoding: Optional[str] = Field(None, description="Content encoding")
    content_language: Optional[str] = Field(None, description="Content language")
    cache_control: Optional[str] = Field(None, description="Cache control header")
    content_disposition: Optional[str] = Field(
        None, description="Content disposition header"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Custom metadata"
    )
    tags: Dict[str, str] = Field(default_factory=dict, description="Blob tags")
    overwrite: bool = Field(True, description="Whether to overwrite existing blob")
    validate_content: bool = Field(True, description="Whether to validate content MD5")
    timeout: Optional[int] = Field(
        None, gt=0, description="Operation timeout in seconds"
    )


class DownloadOptions(BaseModel):
    """Options for blob download operations."""

    offset: Optional[int] = Field(
        None, ge=0, description="Byte offset to start download"
    )
    length: Optional[int] = Field(None, gt=0, description="Number of bytes to download")
    validate_content: bool = Field(True, description="Whether to validate content MD5")
    timeout: Optional[int] = Field(
        None, gt=0, description="Operation timeout in seconds"
    )


class ListOptions(BaseModel):
    """Options for blob/container listing operations."""

    prefix: Optional[str] = Field(None, description="Filter by prefix")
    max_results: Optional[int] = Field(
        None, gt=0, le=5000, description="Maximum results per page"
    )
    include_metadata: bool = Field(False, description="Include metadata in results")
    include_tags: bool = Field(False, description="Include tags in results")
    include_versions: bool = Field(False, description="Include blob versions")
    include_snapshots: bool = Field(False, description="Include blob snapshots")
    timeout: Optional[int] = Field(
        None, gt=0, description="Operation timeout in seconds"
    )


class BlobTierInfo(BaseModel):
    """Information about blob tier operation."""

    container: str = Field(..., description="Container name")
    name: str = Field(..., description="Blob name")
    tier: str = Field(..., description="Access tier (Hot, Cool)")
    tier_change_time: Optional[datetime] = Field(
        None, description="When the tier was last changed"
    )

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v):
        """Validate blob tier value."""
        valid_tiers = {"Hot", "Cool"}
        if v not in valid_tiers:
            raise ValueError(f"Invalid tier: {v}. Must be one of {valid_tiers}")
        return v
