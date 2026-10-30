"""The extracted API can publish releases without the command's project."""

import subprocess
import sys
from io import BytesIO

import pytest
from mlops_blob.exceptions import BlobAlreadyExistsError
from PIL import Image
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dataset_controller import (
    Dataset,
    DatasetController,
    DatasetMember,
    ReleaseConflict,
)
from dataset_controller.models.dataset import sha256
from dataset_controller.repositories.registry import Base


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.uploads = []

    async def upload_blob(self, container, name, data, **kwargs):
        key = (container, name)
        if key in self.objects and not kwargs.get("overwrite", True):
            raise BlobAlreadyExistsError(container, name)
        self.objects[key] = data
        self.uploads.append(name)
        return {}

    async def download_blob(self, container, name, **kwargs):
        return self.objects[container, name]


@pytest.mark.asyncio
async def test_standalone_publish_retry_pin_and_integrity(tmp_path):
    source = BytesIO()
    Image.new("RGB", (4, 3), "red").save(source, format="PNG")
    image = source.getvalue()
    key = f"png/detection/{sha256(image)}.png"
    storage = MemoryStorage()
    storage.objects["datasets", key] = image
    spec = Dataset.model_validate(
        {
            "name": "reviewed",
            "version": "v1",
            "author": "reviewer",
            "conversion": {"code_revision": "prepared-v1", "settings": {}},
            "coco": {
                "images": [
                    {
                        "id": 1,
                        "file_name": key,
                        "width": 4,
                        "height": 3,
                        "split": "train",
                    }
                ],
                "categories": [{"id": 1, "name": "seed"}],
                "annotations": [],
            },
        }
    )
    assert isinstance(spec.coco.images[0], DatasetMember)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'registry.sqlite'}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        controller = DatasetController(storage, async_sessionmaker(engine), "datasets")
        registration = await controller.publish(spec)
        assert registration.status == "ready"
        assert await controller.registration(spec.name, spec.version) == registration
        assert await controller.publish(spec) == registration
        resolved, manifest, coco = await controller.resolve(
            spec.name, spec.version, registration.manifest_sha256
        )
        assert resolved == registration
        assert coco == spec.coco
        assert manifest.crops == []
        assert await controller.read_file(manifest.images[0]) == image
        assert storage.uploads == [
            "releases/reviewed/v1/coco.json",
            "releases/reviewed/v1/release.json",
        ]
        with pytest.raises(ReleaseConflict, match="Pinned release"):
            await controller.resolve(spec.name, spec.version, "0" * 64)
        storage.objects["datasets", key] = b"corrupted"
        with pytest.raises(ReleaseConflict, match="checksum/size mismatch"):
            await controller.resolve(spec.name, spec.version)
    finally:
        await engine.dispose()


def test_imports_without_release_consumer_or_backend(tmp_path):
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; from dataset_controller import DatasetController, ReleaseSpec; "
            "assert not any(name in ('app', 'dataset_release', 'utility') "
            "or name.startswith(('app.', 'dataset_release.', 'utility.')) "
            "for name in sys.modules)",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
