import traceback

from fastapi.logger import logger


class UserError(Exception):
    pass


class UserNotFoundError(UserError):
    pass


class UserConflictError(UserError):
    pass


class UserCreationError(UserError):
    pass


class UserUpdateError(UserError):
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


class AnnotationUpdateError(AnnotationError):
    pass


class AnnotationDeletionError(AnnotationError):
    pass


class ChangeLogError(Exception):
    pass


class ChangeLogNotFoundError(ChangeLogError):
    pass


class ChangeLogCreationError(ChangeLogError):
    pass


class ChangeLogUpdateError(ChangeLogError):
    pass


class ChangeLogDeletionError(ChangeLogError):
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


class ImageError(Exception):
    pass


class ImageNotFoundError(ImageError):
    pass


class ImageCreationError(ImageError):
    pass


class ImageUpdateError(ImageError):
    pass


class ImageDeletionError(ImageError):
    pass


class ImageObjectsError(Exception):
    pass


class ImageObjectsNotFoundError(ImageObjectsError):
    pass


class ImageObjectsCreationError(ImageObjectsError):
    pass


class ImageObjectsUpdateError(ImageObjectsError):
    pass


class ImageObjectsDeletionError(ImageObjectsError):
    pass


class DirectoryError(Exception):
    pass


class DirectoryNotFoundError(DirectoryError):
    pass


class DirectoryCreationError(DirectoryError):
    pass


class DirectoryUpdateError(DirectoryError):
    pass


class DirectoryDeletionError(DirectoryError):
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


class DeviceBrandCreationError(DeviceError):
    pass


class DeviceBrandUpdateError(DeviceError):
    pass


class DeviceBrandDeletionError(DeviceError):
    pass


class DeviceModelNotFoundError(DeviceError):
    pass


class DeviceModelCreationError(DeviceError):
    pass


class DeviceModelUpdateError(DeviceError):
    pass


class DeviceModelDeletionError(DeviceError):
    pass


class DeviceLensNotFoundError(DeviceError):
    pass


class DeviceLensCreationError(DeviceError):
    pass


class DeviceLensUpdateError(DeviceError):
    pass


class DeviceLensDeletionError(DeviceError):
    pass


class DeviceCreationError(DeviceError):
    pass


class DeviceUpdateError(DeviceError):
    pass


class DeviceDeletionError(DeviceError):
    pass


class ModelError(Exception):
    pass


class ModelNotFoundError(ModelError):
    pass


class ModelCreationError(ModelError):
    pass


class ModelUpdateError(ModelError):
    pass


class ModelDeletionError(ModelError):
    pass


class ModelTaskError(Exception):
    pass


class ModelTaskNotFoundError(ModelTaskError):
    pass


class ModelTaskCreationError(ModelTaskError):
    pass


class ModelTaskUpdateError(ModelTaskError):
    pass


class ModelTaskDeletionError(ModelTaskError):
    pass


class SeedError(Exception):
    pass


class SeedNotFoundError(SeedError):
    pass


class SeedCreationError(SeedError):
    pass


class SeedUpdateError(SeedError):
    pass


class SeedDeletionError(SeedError):
    pass


class PipelineError(Exception):
    pass


class PipelineNotFoundError(PipelineError):
    pass


class PipelineCreationError(PipelineError):
    pass


class PipelineUpdateError(PipelineError):
    pass


class PipelineDeletionError(PipelineError):
    pass


class PipelineDefaultError(Exception):
    pass


class PipelineDefaultNotFoundError(PipelineDefaultError):
    pass


class PipelineDefaultCreationError(PipelineDefaultError):
    pass


class PipelineDefaultUpdateError(PipelineDefaultError):
    pass


class PipelineDefaultDeletionError(PipelineDefaultError):
    pass


class PipelineModelError(Exception):
    pass


class PipelineModelNotFoundError(PipelineModelError):
    pass


class PipelineModelCreationError(PipelineModelError):
    pass


class PipelineModelUpdateError(PipelineModelError):
    pass


class PipelineModelDeletionError(PipelineModelError):
    pass


class RbacRoleError(Exception):
    pass


class RbacRoleNotFoundError(RbacRoleError):
    pass


class RbacRoleCreationError(RbacRoleError):
    pass


class RbacRoleUpdateError(RbacRoleError):
    pass


class RbacRoleDeletionError(RbacRoleError):
    pass


class RbacPermissionError(Exception):
    pass


class RbacPermissionNotFoundError(RbacPermissionError):
    pass


class RbacPermissionCreationError(RbacPermissionError):
    pass


class RbacPermissionUpdateError(RbacPermissionError):
    pass


class RbacPermissionDeletionError(RbacPermissionError):
    pass


class RbacResourceError(Exception):
    pass


class RbacResourceNotFoundError(RbacResourceError):
    pass


class RbacResourceCreationError(RbacResourceError):
    pass


class RbacResourceUpdateError(RbacResourceError):
    pass


class RbacResourceDeletionError(RbacResourceError):
    pass


class RbacRolePermissionResourceError(Exception):
    pass


class RbacRolePermissionResourceNotFoundError(RbacRolePermissionResourceError):
    pass


class RbacRolePermissionResourceCreationError(RbacRolePermissionResourceError):
    pass


class RbacRolePermissionResourceUpdateError(RbacRolePermissionResourceError):
    pass


class RbacRolePermissionResourceDeletionError(RbacRolePermissionResourceError):
    pass


class RbacUserRoleError(Exception):
    pass


class RbacUserRoleNotFoundError(RbacUserRoleError):
    pass


class RbacUserRoleCreationError(RbacUserRoleError):
    pass


class RbacUserRoleUpdateError(RbacUserRoleError):
    pass


class RbacUserRoleDeletionError(RbacUserRoleError):
    pass


class ImageProcessingError(Exception):
    """Base exception for image processing errors."""

    pass


class InvalidImageError(ImageProcessingError):
    """Image validation failed."""

    pass


class BlobUploadError(ImageProcessingError):
    """Failed to upload blob to Azure Storage."""

    pass


class BlobDownloadError(ImageProcessingError):
    """Failed to download blob from Azure Storage."""

    pass


class DefenderScanTimeoutError(ImageProcessingError):
    """Azure Defender scan timed out."""

    pass


class DefenderScanFailedError(ImageProcessingError):
    """Azure Defender scan detected malware or encountered an error."""

    pass


class DefenderScanNotScannedError(ImageProcessingError):
    """Azure Defender could not scan the blob (unsupported type, encryption, etc)."""

    pass


class SanitizationError(ImageProcessingError):
    """Sanitization operation failed."""

    pass


def log_error(error: Exception):
    """Logs the error message and traceback."""
    logger.error(f"Error occurred: {error}")
    logger.error("Traceback: " + traceback.format_exc())
