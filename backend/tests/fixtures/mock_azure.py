"""Mock Azure services for testing DBOS workflows."""

from typing import Dict, Any, AsyncIterator, List, Union, BinaryIO
from datetime import timedelta
from app.blob.interface import BlobStorageInterface


class MockBlobStorage(BlobStorageInterface):
    """Mock Azure Blob Storage for testing."""

    def __init__(self):
        self.uploaded_blobs: Dict[str, bytes] = {}
        self.blob_tags: Dict[str, Dict[str, str]] = {}
        self.blob_metadata: Dict[str, Dict[str, str]] = {}
        self.attempt_count = 0
        self.failure_count = 0
        self.malware_detected = False

    def set_failure_count(self, count: int):
        """Set number of times to fail before succeeding."""
        self.failure_count = count
        self.attempt_count = 0

    def set_malware_detected(self, detected: bool):
        """Configure mock to simulate malware detection."""
        self.malware_detected = detected

    async def upload_blob(
        self,
        container: str,
        name: str,
        data: Union[bytes, str, BinaryIO],
        **kwargs
    ) -> Dict[str, Any]:
        """Mock blob upload with optional failure simulation."""
        self.attempt_count += 1

        if self.attempt_count <= self.failure_count:
            raise Exception("Simulated upload failure")

        # Convert container to string if it's an Enum
        container_name = str(container.value if hasattr(container, 'value') else container)

        # Convert data to bytes if needed
        if isinstance(data, str):
            data = data.encode()
        elif isinstance(data, BinaryIO):
            data = data.read()

        self.uploaded_blobs[f"{container_name}/{name}"] = data

        # Store metadata if provided
        metadata = kwargs.get('metadata', {})
        if metadata:
            self.blob_metadata[f"{container_name}/{name}"] = metadata

        # Automatically set Defender scan tags (simulate instant scan)
        self.blob_tags[f"{container_name}/{name}"] = {
            "defender_scan_complete": "true",
            "malware_detected": "true" if self.malware_detected else "false",
            "scan_timestamp": "2025-10-20T00:00:00Z",
        }

        url = f"https://test.blob.core.windows.net/{container_name}/{name}"
        return {"url": url}

    async def download_blob(self, container: str, name: str, **kwargs) -> bytes:
        """Mock blob download."""
        key = f"{container}/{name}"
        if key not in self.uploaded_blobs:
            raise Exception(f"Blob not found: {key}")
        return self.uploaded_blobs[key]

    async def download_blob_stream(
        self, container: str, name: str, **kwargs
    ) -> AsyncIterator[bytes]:
        """Mock blob download as stream."""
        key = f"{container}/{name}"
        if key not in self.uploaded_blobs:
            raise Exception(f"Blob not found: {key}")

        # Yield data in chunks
        data = self.uploaded_blobs[key]
        chunk_size = 1024
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]

    async def get_blob_tags(self, container: str, name: str) -> Dict[str, str]:
        """Mock getting blob tags (for Defender scan results)."""
        # Convert container to string if it's an Enum
        container_name = str(container.value if hasattr(container, 'value') else container)
        key = f"{container_name}/{name}"
        return self.blob_tags.get(key, {
            "defender_scan_complete": "true",
            "malware_detected": "true" if self.malware_detected else "false",
        })

    async def set_blob_tags(
        self, container: str, name: str, tags: Dict[str, str]
    ) -> None:
        """Mock setting blob tags."""
        key = f"{container}/{name}"
        self.blob_tags[key] = tags

    async def get_blob_metadata(self, container: str, name: str) -> Dict[str, str]:
        """Mock getting blob metadata."""
        key = f"{container}/{name}"
        return self.blob_metadata.get(key, {})

    async def set_blob_metadata(
        self, container: str, name: str, metadata: Dict[str, str]
    ) -> None:
        """Mock setting blob metadata."""
        key = f"{container}/{name}"
        self.blob_metadata[key] = metadata

    async def blob_exists(self, container: str, name: str) -> bool:
        """Mock blob existence check."""
        key = f"{container}/{name}"
        return key in self.uploaded_blobs

    async def delete_blob(self, container: str, name: str) -> bool:
        """Mock blob deletion."""
        key = f"{container}/{name}"
        if key in self.uploaded_blobs:
            del self.uploaded_blobs[key]
            if key in self.blob_tags:
                del self.blob_tags[key]
            if key in self.blob_metadata:
                del self.blob_metadata[key]
            return True
        return False

    async def get_blob_properties(self, container: str, name: str) -> Dict[str, Any]:
        """Mock getting blob properties."""
        key = f"{container}/{name}"
        if key not in self.uploaded_blobs:
            raise Exception(f"Blob not found: {key}")

        return {
            "name": name,
            "container": container,
            "size": len(self.uploaded_blobs[key]),
            "content_type": "image/png",
            "created_on": "2025-10-20T00:00:00Z",
            "last_modified": "2025-10-20T00:00:00Z",
        }

    async def list_blobs(self, container: str, **kwargs) -> Dict[str, Any]:
        """Mock listing blobs in a container."""
        prefix = kwargs.get('name_starts_with', '')
        blobs = []

        for key in self.uploaded_blobs.keys():
            if key.startswith(f"{container}/"):
                name = key.replace(f"{container}/", "", 1)
                if name.startswith(prefix):
                    blobs.append({
                        "name": name,
                        "size": len(self.uploaded_blobs[key]),
                    })

        return {"blobs": blobs}

    async def copy_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Mock blob copy."""
        source_key = f"{source_container}/{source_name}"
        dest_key = f"{dest_container}/{dest_name}"

        if source_key not in self.uploaded_blobs:
            raise Exception(f"Source blob not found: {source_key}")

        self.uploaded_blobs[dest_key] = self.uploaded_blobs[source_key]

        return {"url": f"https://test.blob.core.windows.net/{dest_container}/{dest_name}"}

    async def move_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Mock blob move."""
        result = await self.copy_blob(source_container, source_name, dest_container, dest_name, **kwargs)
        await self.delete_blob(source_container, source_name)
        return result

    async def create_container(self, name: str, **kwargs) -> Dict[str, Any]:
        """Mock container creation."""
        return {"name": name, "created": True}

    async def delete_container(self, name: str) -> bool:
        """Mock container deletion."""
        return True

    async def container_exists(self, name: str) -> bool:
        """Mock container existence check."""
        return True

    async def list_containers(self, **kwargs) -> Dict[str, Any]:
        """Mock listing containers."""
        return {"containers": ["nachet-original", "nachet-sanitized"]}

    async def get_container_properties(self, name: str) -> Dict[str, Any]:
        """Mock getting container properties."""
        return {"name": name, "exists": True}

    async def generate_sas_token(
        self,
        container: str,
        name: str,
        permissions: List[str],
        expiry: timedelta,
        **kwargs,
    ) -> Dict[str, Any]:
        """Mock SAS token generation."""
        return {
            "url": f"https://test.blob.core.windows.net/{container}/{name}?sv=2021-06-08&se=2025-10-21T00:00:00Z&sr=b&sp=r&sig=mock_signature"
        }

    async def generate_container_sas_token(
        self, container: str, permissions: List[str], expiry: timedelta, **kwargs
    ) -> Dict[str, Any]:
        """Mock container SAS token generation."""
        return {
            "url": f"https://test.blob.core.windows.net/{container}?sv=2021-06-08&se=2025-10-21T00:00:00Z&sr=c&sp=rl&sig=mock_signature"
        }

    async def get_blob_url(self, container: str, name: str, **kwargs) -> str:
        """Mock getting blob URL."""
        return f"https://test.blob.core.windows.net/{container}/{name}"

    async def set_blob_tier(
        self, container: str, name: str, tier: str, **kwargs
    ) -> bool:
        """Mock setting blob tier."""
        return True


class MockDefender:
    """Mock Azure Defender for testing."""

    def __init__(self):
        self.malware_detected = False
        self.scan_delay_seconds = 0

    def set_malware_detected(self, detected: bool):
        """Configure mock to simulate malware detection."""
        self.malware_detected = detected

    def set_scan_delay(self, seconds: int):
        """Configure mock to simulate scan delay."""
        self.scan_delay_seconds = seconds

    def get_scan_result(self) -> Dict[str, str]:
        """Get mock scan result tags."""
        return {
            "defender_scan_complete": "true",
            "malware_detected": "true" if self.malware_detected else "false",
            "scan_timestamp": "2025-10-20T00:00:00Z",
        }
