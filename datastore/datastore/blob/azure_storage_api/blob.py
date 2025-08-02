"""
Blob operations for Azure Storage API.
"""

from azure.storage.blob import ContainerClient, BlobProperties

from .exceptions import GetBlobError


async def get_blob(container_client, blob_name):
    """
    gets the contents of a specified blob in the user's container
    """
    try:
        blob_client = container_client.get_blob_client(str(blob_name))
        blob = blob_client.download_blob()
        blob_content = blob.readall()
        return blob_content
    except Exception as error:
        raise GetBlobError(str(error) + "\nError getting blob:" + blob_name)


async def get_blobs_from_tag(container_client: ContainerClient, tag: str):
    """
    This function gets the names of blobs in a picture set folder

    Parameters:
    - container_client: the Azure container client
    - tag: the tag to search for in the blobs ex: 'folder_name'

    Returns: the list of blobs
    """
    try:
        # The find_blobs_by_tags methods should return a list of blobs with the given tag
        # blob_list = list(container_client.find_blobs_by_tags(filter_expression=tag))

        # Without the find_blobs_by_tags method
        blob_list = list(container_client.list_blobs(include=["tags"]))
        result: list[BlobProperties] = []
        for blob in blob_list:
            if (
                blob.get("tags")
                and "picture_set_uuid" in blob.get("tags")
                and blob.get("tags").get("picture_set_uuid") == tag
            ):
                result.append(blob)

        if len(result) > 0:
            return result
        else:
            raise GetBlobError("No blobs found with the given tag")
    except Exception as e:
        print(f"Exception during find_blobs_by_tags: {e}")
        raise GetBlobError(f"Error getting blobs: {str(e)}")


async def move_blob(
    blob_name_source,
    blob_name_dest,
    folder_uuid,
    container_client_source,
    container_client_destination,
):
    """
    This function move a blob from a container to another

    Parameters:
    - blob_name: the name of the blob to move
    - container_client_source: the Azure container client where the blob is
    - container_client_destination : the Azure container client where the blob will be moved
    """
    try:
        blob_client = container_client_source.get_blob_client(blob_name_source)

        blob = blob_client.download_blob().readall()

        blob_client_destination = container_client_destination.get_blob_client(
            blob_name_dest
        )

        blob_client_destination.upload_blob(blob, overwrite=True)
        metadata = {"picture_set_uuid": f"{str(folder_uuid)}"}
        blob_client_destination.set_blob_tags(metadata)

        container_client_source.delete_blob(blob_name_source)
        return True
    except Exception as e:
        raise Exception(f"Error moving blob: {e}")
