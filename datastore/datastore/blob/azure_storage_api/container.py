"""
Container operations for Azure Storage API.
"""

import os
from azure.storage.blob import BlobServiceClient

from .exceptions import MountContainerError, ConnectionStringError
from .utils import build_container_name, build_blob_name
from .folder import create_folder


async def mount_container(
    connection_string,
    container_uuid,
    create_container=True,
    tier="user",
    credentials="",
):
    """
    Creates a container_client as an object that can be used in other functions.

    Parameters:
    - connection_string: the connection string to the azure storage account
    - container_uuid: the uuid of the container (usually the user uuid)
    - create_container: a boolean value to specify if the container should be created if it doesnt exist (default is True)
    - tier: the tier of the container (default is user, should be changed if the structure changes to accomodate other type of containers)

    Returns:
    - container_client: the container client object
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            conn_str=connection_string, credential=credentials
        )
        if blob_service_client:
            container_name = build_container_name(str(container_uuid), tier)
            container_client = blob_service_client.get_container_client(container_name)
            if container_client.exists():
                return container_client
            elif create_container and not container_client.exists():
                container_client = blob_service_client.create_container(container_name)
                # create general directory for new user container
                response = await create_folder(container_client, "General")
                if response:
                    return container_client
                else:
                    raise MountContainerError("Error creating general directory")
            elif not create_container and not container_client.exists():
                raise MountContainerError("Container does not exist")
        else:
            raise ConnectionStringError("Invalid connection string")
    except ValueError as error:
        raise ConnectionStringError(
            "The given connection string is invalid: " + error.__str__()
        )
    except MountContainerError as error:
        raise error
    except ConnectionStringError as error:
        raise error
    except Exception as error:
        raise Exception("Unhandeled error:" + error.__str__())


async def download_container(container_client, container_name, local_dir):
    """
    This function downloads all the files from a container in a storage account
    to the local directory "test"

    This serves as a way to locally download the container files for processing and importing within the db

    Parameters:
    - container_client: the Azure container client
    - local_dir: the local directory to download the files to

    Returns: None
    """
    try:
        # List blobs in the container
        blob_list = container_client.list_blobs()
        # Iterate through each blob
        for i, blob in enumerate(blob_list):
            # Create a blob client
            blob_client = container_client.get_blob_client(
                container=container_name, blob=blob
            )
            # Download the blob
            local_file_path = build_blob_name(str(local_dir), str(blob.name))
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            with open(local_file_path, "wb") as file:
                blob_data = blob_client.download_blob(blob=blob.name)
                blob_data.readinto(file)
                #  nb_downloaded_files = i
    except Exception:
        raise Exception("Error downloading container")
