"""
Azure Storage API for blob and container operations.

---- user-container based structure -----
- container name is user id
- whenever a new user is created, a new container is created with the user uuid
- inside the container, there are project folders (project name = project uuid)
- for each project folder, there is a json file with the project info and creation
date, in the container
- inside the project folder, there is an image file and a json file with
the image inference results
"""

# Import all exceptions
from .exceptions import (
    GenerateHashError,
    MountContainerError,
    GetBlobError,
    UploadImageError,
    UploadInferenceResultError,
    GetFolderUUIDError,
    FolderListError,
    CreateDirectoryError,
    ConnectionStringError,
)

# Import utility functions
from .utils import (
    generate_hash,
    build_container_name,
    build_blob_name,
)

# Import container operations
from .container import (
    mount_container,
    download_container,
)

# Import blob operations
from .blob import (
    get_blob,
    get_blobs_from_tag,
    move_blob,
)

# Import folder operations
from .folder import (
    upload_image,
    is_a_folder,
    create_folder,
    create_dev_container_folder,
    upload_inference_result,
    get_folder_uuid,
    get_image_count,
    get_directories,
    delete_folder,
)

# Make all imports available at package level for backward compatibility
__all__ = [
    # Exceptions
    "GenerateHashError",
    "MountContainerError",
    "GetBlobError",
    "UploadImageError",
    "UploadInferenceResultError",
    "GetFolderUUIDError",
    "FolderListError",
    "CreateDirectoryError",
    "ConnectionStringError",
    # Utilities
    "generate_hash",
    "build_container_name",
    "build_blob_name",
    # Container operations
    "mount_container",
    "download_container",
    # Blob operations
    "get_blob",
    "get_blobs_from_tag",
    "move_blob",
    # Folder operations
    "upload_image",
    "is_a_folder",
    "create_folder",
    "create_dev_container_folder",
    "upload_inference_result",
    "get_folder_uuid",
    "get_image_count",
    "get_directories",
    "delete_folder",
]
