from azure.storage.blob import (
    BlobServiceClient,
    generate_account_sas,
    ResourceTypes,
    AccountSasPermissions,
)
from datetime import timedelta, datetime


class ConnectionStringError(Exception):
    pass


# Module-level logger
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from app.service.logs import LogService
        _logger = LogService.get_logger()
    return _logger


def create_blob_service_client(storage_url):
    """
    This function creates a BlobServiceClient object

    Parameters:
    - storage_url: the url of the storage account

    Returns: BlobServiceClient object
    """
    try:
        # Create a blob service client
        blob_service_client = BlobServiceClient.from_connection_string(
            conn_str=storage_url
        )
        return blob_service_client
    except ValueError as e:
        _get_logger().error("Invalid connection string", error=str(e), error_type="ValueError")
        raise ConnectionStringError(
            "The connection string is invalid. Please check the connection string."
        )
    except Exception as e:
        _get_logger().error("Unhandled exception in blob client creation", error=str(e), error_type=type(e).__name__)
        raise Exception("Datastore.blob Unhandled Exception")


def create_container_client(blob_service_client, container_name):
    """
    This function creates a container client object

    Parameters:
    - blob_service_client: the BlobServiceClient object
    - container_name: the name of the container

    Returns: ContainerClient object
    """
    try:
        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()
        return container_client
    except Exception as e:
        _get_logger().error("Failed to create container client", container=container_name, error=str(e), error_type=type(e).__name__)
        raise Exception("Datastore.blob Unhandled Exception")


def create_blob_client(container_client, blob_name):
    """
    This function creates a blob client object

    Parameters:
    - container_client: the ContainerClient object
    - blob_name: the name of the blob

    Returns: BlobClient object
    """
    try:
        # Get the blob client
        blob_client = container_client.get_blob_client(blob_name)
        return blob_client
    except Exception as e:
        _get_logger().error("Failed to create blob client", blob_name=blob_name, error=str(e), error_type=type(e).__name__)
        raise Exception("Datastore.blob Unhandled Exception")


def get_account_sas(account_name: str, key: str):
    """
    This function returns the account sas token

    Parameters:
    - name: the name of the storage account
    - key: the key of the storage account

    Returns: str
    """
    # Get the account sas token
    account_sas = generate_account_sas(
        account_name=account_name,
        account_key=key,
        resource_types=ResourceTypes(service=True, container=True, object=True),
        permission=AccountSasPermissions(
            read=True,
            write=True,
            delete=True,
            list=True,
            add=True,
            create=True,
            update=True,
            tag=True,
            filter_by_tag=True,
        ),
        expiry=datetime.now() + timedelta(minutes=5),
    )
    return account_sas
