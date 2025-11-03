import re
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from typing import Optional


class DirectoryRequest(BaseModel):
    container_name: str


class CreateOrGetFolderRequest(BaseModel):
    """Request model for creating or retrieving a folder.

    The normalized_path is a relative path (e.g., 'avena-fatua' or 'mycology/avena-fatua').
    The backend will prepend the user's organization prefix automatically.

    Validation is performed in the service layer via DirectoryService._validate_and_parse_fullpath().

    The description field is optional and defaults to empty string if not provided.
    """

    normalized_path: str
    description: str = ""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @field_validator("normalized_path")
    @classmethod
    def validate_normalized_path(cls, v: str) -> str:
        """
        Validate normalized_path format.

        This is a basic pre-check before service layer validation.
        Full validation happens in DirectoryService._validate_and_parse_fullpath().
        """
        # Strip whitespace first
        v = v.strip()

        if not v:
            raise ValueError("Path cannot be empty")

        # Basic character check: alphanumeric, slash, underscore, dash, period only
        if not re.match(r"^[a-zA-Z0-9/_.\-]+$", v):
            raise ValueError(
                "Path can only contain letters, numbers, slashes, underscores, dashes, and periods"
            )

        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """
        Validate description field: alphanumeric, periods, spaces only, max 500 chars.

        Matches InferenceRequest and BatchUploadImageRequest validation pattern.
        """
        # Allow empty but validate if provided
        if v:
            # Check character set: only alphanumeric, periods, and spaces allowed
            if not re.match(r"^[a-zA-Z0-9. ]*$", v):
                raise ValueError(
                    "Description can only contain letters, numbers, periods, and spaces"
                )

            if len(v) > 500:
                raise ValueError("Description exceeds 500 characters")

        return v


class UpdateFolderRequest(BaseModel):
    """Request model for updating a folder's name and/or description.

    Both fields are optional - update only the fields provided.
    Name validation is performed in the service layer.
    Description is sanitized on the client side.
    """

    name: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate folder name format.

        Folder names can contain alphanumeric, underscore, dash, and period.
        Must end with alphanumeric character.
        """
        if v is None:
            return v

        # Strip whitespace first
        v = v.strip()

        if not v:
            raise ValueError("Name cannot be empty")

        # Folder names: alphanumeric, underscore, dash, period
        if not re.match(r"^[a-zA-Z0-9_.\-]+$", v):
            raise ValueError(
                "Name can only contain letters, numbers, underscores, dashes, and periods"
            )

        # Must end with alphanumeric character
        if not re.match(r"^.*[a-zA-Z0-9]$", v):
            raise ValueError("Name must end with alphanumeric character")

        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate description field: alphanumeric, periods, spaces only, max 500 chars.

        Matches InferenceRequest and BatchUploadImageRequest validation pattern.
        """
        if v is None:
            return v

        # Allow empty but validate if provided
        if v:
            # Check character set: only alphanumeric, periods, and spaces allowed
            if not re.match(r"^[a-zA-Z0-9. ]*$", v):
                raise ValueError(
                    "Description can only contain letters, numbers, periods, and spaces"
                )

            if len(v) > 500:
                raise ValueError("Description exceeds 500 characters")

        return v


class UpdateFolderResponse(BaseModel):
    """Response model for folder update operations."""

    id: str
    message: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class CreateFolderResponse(BaseModel):
    """Response model for folder creation (get-or-create pattern)."""

    folder_id: str = Field(..., description="UUID of existing or newly created folder")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DeleteFolderResponse(BaseModel):
    """Response model for folder deletion (soft delete)."""

    id: str = Field(..., description="UUID of the deleted folder")
    message: str = Field(..., description="Success message")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
