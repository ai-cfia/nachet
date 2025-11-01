from pydantic import BaseModel
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


class UpdateFolderRequest(BaseModel):
    """Request model for updating a folder's name and/or description.

    Both fields are optional - update only the fields provided.
    Name validation is performed in the service layer.
    Description is sanitized on the client side.
    """

    name: Optional[str] = None
    description: Optional[str] = None


class UpdateFolderResponse(BaseModel):
    """Response model for folder update operations."""

    id: str
    message: str
