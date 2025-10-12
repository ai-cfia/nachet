import traceback

from fastapi.logger import logger


class UserError(Exception):
    pass


class UserNotFoundError(UserError):
    pass


class UserConflictError(UserError):
    pass


class UserDeletionError(UserError):
    pass


class MissingUserAttributeError(UserError):
    pass


class AnnotationError(Exception):
    pass


class AnnotationNotFoundError(AnnotationError):
    pass


class AnnotationCreationError(AnnotationError):
    pass


class AnnotationDeletionError(AnnotationError):
    pass


class InferenceError(Exception):
    pass


class InferenceNotFoundError(InferenceError):
    pass


class InferenceCreationError(InferenceError):
    pass


class InferenceDeletionError(InferenceError):
    pass


class FolderError(Exception):
    pass


class FolderReadError(FolderError):
    pass


class FolderNotFoundError(FolderError):
    pass


class FolderCreationError(FolderError):
    pass


class FolderDeletionError(FolderError):
    pass


class FileError(Exception):
    pass


class FileNotFoundError(FileError):
    pass


class FileCreationError(FileError):
    pass


class StorageError(Exception):
    pass


class StorageFileNotFound(StorageError):
    pass


class OrganizationError(Exception):
    pass


class OrganizationNotFoundError(OrganizationError):
    pass


class OrganizationCreationError(OrganizationError):
    pass


class OrganizationUpdateError(OrganizationError):
    pass


class OrganizationDeletionError(OrganizationError):
    pass


class OrganizationUnauthorizedError(OrganizationError):
    pass


class DeviceError(Exception):
    pass


class DeviceBrandNotFoundError(DeviceError):
    pass


class DeviceModelNotFoundError(DeviceError):
    pass


class DeviceLensNotFoundError(DeviceError):
    pass


class DeviceCreationError(DeviceError):
    pass


class DeviceUpdateError(DeviceError):
    pass


class DeviceDeletionError(DeviceError):
    pass


def log_error(error: Exception):
    """Logs the error message and traceback."""
    logger.error(f"Error occurred: {error}")
    logger.error("Traceback: " + traceback.format_exc())
