"""
Custom exceptions for picture and picture set operations.
"""


class PictureUploadError(Exception):
    """Raised when picture upload fails."""

    pass


class PictureNotFoundError(Exception):
    """Raised when a picture is not found."""

    pass


class PictureSetCreationError(Exception):
    """Raised when picture set creation fails."""

    pass


class PictureSetNotFoundError(Exception):
    """Raised when a picture set is not found."""

    pass


class PictureUpdateError(Exception):
    """Raised when picture update operation fails."""

    pass


class GetPictureSetError(Exception):
    """Raised when retrieving picture sets fails."""

    pass


class GetPictureError(Exception):
    """Raised when retrieving pictures fails."""

    pass


class PictureSetDeleteError(Exception):
    """Raised when picture set deletion fails."""

    pass
