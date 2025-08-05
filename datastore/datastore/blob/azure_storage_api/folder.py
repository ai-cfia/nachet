"""
Folder operations for Azure Storage API.
"""

import datetime
import json
from azure.storage.blob import ContainerClient

from .exceptions import (
    CreateDirectoryError,
    UploadImageError,
    FolderListError,
    GetFolderUUIDError,
    UploadInferenceResultError,
    # GetBlobError,
)
from .utils import build_blob_name
from .blob import get_blob


async def upload_image(
    container_client, folder_name, folder_uuid, image: str, image_uuid
):
    """
    uploads the image to the specified folder within the user's container,
    if the specified folder doesnt exist, it creates it with a uuid

    Parameters:
    - container_client: the Azure container client
    - folder_name: the name of the destination folder
    - folder_uuid : uuid of the picture_set
    - image:
    """
    try:
        if not await is_a_folder(container_client, folder_name):
            raise CreateDirectoryError(f"Folder:{folder_name} does not exist")
        else:
            blob_name = build_blob_name(str(folder_name), str(image_uuid))
            metadata = {
                "picture_uuid": f"{str(image_uuid)}",
                "picture_set_uuid": f"{str(folder_uuid)}",
            }
            blob_client = container_client.upload_blob(blob_name, image, overwrite=True)
            blob_client.set_blob_tags(metadata)
            return blob_name
    except CreateDirectoryError or UploadImageError as e:
        raise e
    except Exception as error:
        print(error)
        raise Exception("Datastore.blob.azure_storage unHandled Error")


async def is_a_folder(container_client, folder_name):
    """
    This function checks if a folder exists in the container

    Parameters:
    - container_client: the Azure container client
    - folder_name: the name of the folder to check

    Returns: True if the folder exists, False otherwise
    """
    try:
        directories = await get_directories(container_client)
        if str(folder_name) in directories:
            return True
        else:
            return False
    except FolderListError as e:
        print(e)
        raise FolderListError(
            "Error getting folder list, could not check if its a folder"
        )
    except Exception:
        raise Exception("Datastore.blob.azure_storage : Unhandled Error")


async def create_folder(container_client, folder_uuid=None, folder_name=None):
    """
    creates a folder in the user's container

    Parameters:
    - container_client: the container client object to interact with the Azure storage account
    - folder_uuid: the uuid of the folder to be created
    - folder_name: the name of the folder to be created (usually it's uuid)
    """
    try:
        # We want to enable 2 types of folder creation
        if folder_uuid is None and folder_name is None:
            raise CreateDirectoryError("Folder name and uuid not provided")
        elif folder_uuid is None:
            raise CreateDirectoryError("Folder uuid not provided")
        # Until we allow user to manually create folder and name them
        if folder_name is None:
            folder_name = folder_uuid
        if not await is_a_folder(container_client, folder_name):
            folder_data = {
                "folder_name": folder_name,
                "date_created": str(
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
            }
            # Usually we create a folder named General after creating a container.
            # Those folder do not have a UUID and are used to store general data
            if folder_uuid is not None:
                folder_data["folder_uuid"] = str(folder_uuid)
            file_name = build_blob_name(str(folder_name), str(folder_name), "json")
            blob_client = container_client.upload_blob(
                file_name, json.dumps(folder_data), overwrite=True
            )
            metadata = {"picture_set_uuid": f"{str(folder_uuid)}"}
            blob_client.set_blob_tags(metadata)
            return True
        else:
            raise CreateDirectoryError("Folder already exists")

    except CreateDirectoryError as error:
        raise error
    except FolderListError as error:
        print(error)
        raise CreateDirectoryError("Error getting folder list, could not create folder")
    except Exception as error:
        print(error)
        raise Exception("Datastore unHandled Error")


async def create_dev_container_folder(
    dev_container_client, folder_uuid=None, folder_name=None, user_id=None
):
    """
    creates a folder in the dev user's container, this is used to archive data

    Parameters:
    - container_client: the container client object to interact with the Azure storage account
    - folder_uuid: the uuid of the folder to be created
    - folder_name: the name of the folder to be created (usually it's uuid)
    - user_id : the user id of the user archiving a folder
    """
    try:
        # We want to enable 2 types of folder creation
        if folder_uuid is None and folder_name is None:
            raise CreateDirectoryError("Folder name and uuid not provided")
        elif folder_uuid is None:
            raise CreateDirectoryError("Folder uuid not provided")
        if user_id is None:
            raise CreateDirectoryError("User id not provided")
        # Until we allow user to manually create folder and name them
        if folder_name is None:
            folder_name = folder_uuid
        if not await is_a_folder(
            dev_container_client, "{}/{}".format(user_id, folder_name)
        ):
            folder_data = {
                "folder_name": "{}/{}".format(user_id, folder_name),
                "date_created": str(
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
            }
            # Usually we create a folder named General after creating a container.
            # Those folder do not have a UUID and are used to store general data
            if folder_uuid is not None:
                folder_data["folder_uuid"] = str(folder_uuid)
            file_name = build_blob_name(
                "{}/{}".format(str(user_id), str(folder_name)), str(folder_name), "json"
            )  # file_name = "{}/{}/{}.json".format(user_id, folder_name, folder_name)
            blob_client = dev_container_client.upload_blob(
                file_name, json.dumps(folder_data), overwrite=True
            )
            metadata = {"picture_set_uuid": f"{str(folder_uuid)}"}
            blob_client.set_blob_tags(metadata)
            return True
        else:
            raise CreateDirectoryError("Folder already exists")

    except CreateDirectoryError as error:
        raise error
    except FolderListError as error:
        print(error)
        raise CreateDirectoryError("Error getting folder list, could not create folder")
    except Exception as error:
        print(error)
        raise Exception("Datastore unHandled Error")


async def upload_inference_result(container_client, folder_name, result, hash_value):
    """
    uploads the inference results json file to the specified folder
    in the users container
    """
    try:
        folder_uuid = await get_folder_uuid(container_client, folder_name)
        if folder_uuid:
            json_name = build_blob_name(str(folder_name), hash_value, "json")
            container_client.upload_blob(json_name, result, overwrite=True)
            return True

    except UploadInferenceResultError as error:
        print(error)
        return False


async def get_folder_uuid(container_client, folder_name):
    """
    gets the uuid of a folder in the user's container given the folder name by
    iterating through the folder json files and extracting the name
    to match given folder name
    """
    try:
        blob_list = container_client.list_blobs()
        for blob in blob_list:
            if (
                blob.name.split(".")[-1] == "json"
                and blob.name.count("/") == 1
                and blob.name.split("/")[0] == blob.name.split("/")[1].split(".")[0]
            ):
                folder_json = await get_blob(container_client, blob.name)

                if folder_json:
                    folder_json = json.loads(folder_json)

                    if folder_json["folder_name"] == folder_name:
                        if "folder_uuid" not in folder_json:
                            raise GetFolderUUIDError(
                                "Folder UUID not found in folder metadata"
                            )
                        return folder_json["folder_uuid"]
        raise GetFolderUUIDError(f"Folder '{folder_name}' not found")
    except GetFolderUUIDError as error:
        raise error
    except Exception as error:
        print(error)
        raise Exception("Datastore.blob.azure_storage unHandled Error")


async def get_image_count(container_client, folder_name):
    """
    gets the number of images in a folder in the user's container
    """
    try:
        folder_uuid = await get_folder_uuid(container_client, folder_name)
        if folder_uuid:
            blob_list = container_client.list_blobs()
            count = 0
            for blob in blob_list:
                if (blob.name.split("/")[0] == folder_name) and (
                    blob.name.split(".")[-1] != "json"
                ):
                    count += 1
            return count
        else:
            return False
    except GetFolderUUIDError as error:
        print(error)
        return False


async def get_directories(container_client):
    """
    returns a list of folder names in the user's container
    """
    try:
        directories = {}
        blob_list = container_client.list_blobs()
        for blob in blob_list:
            if (
                blob.name.split(".")[-1] == "json"
                and blob.name.count("/") == 1
                and blob.name.split("/")[0] == blob.name.split("/")[1].split(".")[0]
            ):
                json_blob = await get_blob(container_client, blob.name)
                if json_blob:
                    folder_json = json.loads(json_blob)
                    image_count = await get_image_count(
                        container_client, folder_json["folder_name"]
                    )
                    directories[folder_json["folder_name"]] = image_count
        return directories
    except FolderListError as error:
        raise error
    except Exception as error:
        print(error)
        raise FolderListError(f"Error getting directories: {str(error)}")


async def delete_folder(container_client: ContainerClient, picture_set_id):
    """
    This function deletes a folder in the user's container

    Parameters:
    - container_client: the Azure container client
    - picture_set_id: id of the picture set related to the folder to delete

    Returns: True if the folder is deleted, False otherwise
    """
    try:
        from .blob import get_blobs_from_tag

        blobs = await get_blobs_from_tag(container_client, picture_set_id)
        for blob in blobs:
            container_client.delete_blob(blob.name)
        return True

    except GetFolderUUIDError:
        return False
    except Exception:
        return False
