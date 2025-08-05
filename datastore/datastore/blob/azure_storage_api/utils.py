"""
Utility functions for Azure Storage API operations.
"""

import hashlib

from .exceptions import GenerateHashError


async def generate_hash(image):
    """
    generates a hash value for the image to be used as the image name in the container
    """
    try:
        hash = hashlib.sha256(image).hexdigest()
        return hash

    except TypeError as error:
        print(error.__str__())
        raise GenerateHashError("The image is not in the correct format")
    except Exception as error:
        print(error.__str__())
        raise Exception("Unhandeled Datastore.blob.azure_storage Error")


def build_container_name(name: str, tier: str = "user") -> str:
    """
    This function builds the container name based on the tier and the name.
    We include a tier to better structure the container names in the future. Other tiers could be 'dev' or 'test-user'

    Parameters:
    - name (str): the name of the container. Usually the user uuid
    - tier (str): the tier of the container; Default is 'user'
    """
    if not name or name.strip() == "":
        raise ValueError("Name is required")
    return "{}-{}".format(tier, name)


def build_blob_name(folder_path: str, blob_name: str, file_type: str = None) -> str:
    """
    This function builds the blob name based on the folder name and the image uuid

    Parameters:
    - folder_path (str): The path to the folder
    - blob_name (str): Usually the uuid of the image
    - file_type (str): the type of the file (ex: png, jpg, json)
    """
    if not folder_path or folder_path.strip() == "":
        raise ValueError("Folder name is required")
    if not blob_name or blob_name.strip() == "":
        raise ValueError("Image uuid is required (parameter: blob_name)")
    if file_type is not None and file_type.strip() != "":
        return "{}/{}.{}".format(folder_path, blob_name, file_type)
    else:
        return "{}/{}".format(folder_path, blob_name)
