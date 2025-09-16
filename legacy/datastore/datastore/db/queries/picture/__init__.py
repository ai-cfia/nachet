"""
This module contains all the queries related to the Picture and PictureSet tables.
Refactored from monolithic structure to modular architecture for better maintainability.
"""

# Import exceptions
from .exceptions import (
    PictureUploadError,
    PictureNotFoundError,
    PictureSetCreationError,
    PictureSetNotFoundError,
    PictureUpdateError,
    GetPictureSetError,
    GetPictureError,
    PictureSetDeleteError,
)

# Import picture set operations
from .picture_set import (
    new_picture_set,
    get_picture_set,
    get_picture_set_name,
    get_user_picture_sets,
    get_user_latest_picture_set,
    get_picture_set_owner_id,
    delete_picture_set,
)

# Import picture operations
from .picture import (
    new_picture,
    new_picture_unknown,
    get_picture,
    count_pictures,
    get_picture_set_pictures,
    get_validated_pictures,
    is_picture_validated,
    check_picture_inference_exist,
    change_picture_set_id,
    update_picture_metadata,
    get_picture_picture_set_id,
    update_picture_picture_set_id,
    get_picture_in_picture_set,
)

# Import validation functions
from .validation import (
    is_a_picture_set_id,
    is_a_picture_id,
)

# Define what should be available when importing with "from picture import *"
__all__ = [
    # Exceptions
    "PictureUploadError",
    "PictureNotFoundError",
    "PictureSetCreationError",
    "PictureSetNotFoundError",
    "PictureUpdateError",
    "GetPictureSetError",
    "GetPictureError",
    "PictureSetDeleteError",
    # Picture set operations
    "new_picture_set",
    "get_picture_set",
    "get_picture_set_name",
    "get_user_picture_sets",
    "get_user_latest_picture_set",
    "get_picture_set_owner_id",
    "delete_picture_set",
    # Picture operations
    "new_picture",
    "new_picture_unknown",
    "get_picture",
    "count_pictures",
    "get_picture_set_pictures",
    "get_validated_pictures",
    "is_picture_validated",
    "check_picture_inference_exist",
    "change_picture_set_id",
    "update_picture_metadata",
    "get_picture_picture_set_id",
    "update_picture_picture_set_id",
    "get_picture_in_picture_set",
    # Validation functions
    "is_a_picture_set_id",
    "is_a_picture_id",
]
