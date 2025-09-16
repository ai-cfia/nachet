"""
Custom exceptions for Azure Storage API operations.
"""


class GenerateHashError(Exception):
    pass


class MountContainerError(Exception):
    pass


class GetBlobError(Exception):
    pass


class UploadImageError(Exception):
    pass


class UploadInferenceResultError(Exception):
    pass


class GetFolderUUIDError(Exception):
    pass


class FolderListError(Exception):
    pass


class CreateDirectoryError(Exception):
    pass


class ConnectionStringError(Exception):
    pass
