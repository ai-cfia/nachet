"""Verify independent installation and provider construction without live storage."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import blob
from blob import BlobStorageInterface, create_blob_storage_client


def test_editable_install_resolves_to_mlops_copy(tmp_path):
    package_root = Path(__file__).resolve().parents[1]
    assert Path(blob.__file__).resolve().parent == package_root
    result = subprocess.run(
        [sys.executable, "-I", str(Path(__file__).with_name("check_install.py"))],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert str(package_root) in result.stdout
    assert "no backend imports" in result.stdout


def test_factory_constructs_copied_azure_provider(monkeypatch):
    from blob.azure import storage

    client = MagicMock()
    create_client = MagicMock(return_value=client)
    monkeypatch.setattr(storage, "create_blob_service_client", create_client)
    config = {
        "blob_storage_name": "testaccount",
        "blob_storage_key": "test-key",
        "blob_storage_endpoint_protocol": "https",
        "blob_storage_endpoint_suffix": "core.windows.net",
        "blob_storage_endpoint_base": "https://testaccount.blob.core.windows.net",
    }
    provider = create_blob_storage_client("azure", config)
    assert isinstance(provider, BlobStorageInterface)
    assert type(provider).__module__ == "blob.azure.storage"
    assert provider._blob_service_client is client
    create_client.assert_called_once()


def test_factory_constructs_copied_s3_provider(monkeypatch):
    from blob.s3 import client as client_module

    client = MagicMock()
    monkeypatch.setattr(client_module.boto3, "client", MagicMock(return_value=client))
    config = {"s3_access_key": "test-access", "s3_secret_key": "test-secret"}
    provider = create_blob_storage_client("s3", config)
    assert isinstance(provider, BlobStorageInterface)
    assert type(provider).__module__ == "blob.s3.storage"
    assert provider._s3_client is client
    client.list_buckets.assert_called_once()
