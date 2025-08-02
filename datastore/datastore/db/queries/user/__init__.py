"""
This module contains the queries related to the user table.

The module is organized into the following sub-modules:
- exceptions: Custom exception classes
- validation: User validation functions
- user_management: Core user operations
- container_management: Container-related operations
- picture_set_management: Picture set operations
"""

from uuid import UUID

# Import exceptions
from .exceptions import (
    UserCreationError,
    UserNotFoundError,
    ContainerNotSetError,
    SecurityValidationError,
)

# Import validation functions
from .validation import (
    is_user_registered,
    is_a_user_id,
)

# Import user management functions
from .user_management import (
    get_user_id,
    register_user,
)

# Import container management functions
from .container_management import (
    link_container,
    get_container_url,
)

# Import picture set management functions
from .picture_set_management import (
    set_default_picture_set,
    get_default_picture_set,
)

# Define what should be exported when someone does "from user import *"
__all__ = [
    # Exceptions
    "UserCreationError",
    "UserNotFoundError",
    "ContainerNotSetError",
    "SecurityValidationError",
    # Validation functions
    "is_user_registered",
    "is_a_user_id",
    # User management functions
    "get_user_id",
    "register_user",
    # Container management functions
    "link_container",
    "get_container_url",
    # Picture set management functions
    "set_default_picture_set",
    "get_default_picture_set",
]
