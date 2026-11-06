"""Check dataset/blob integration in an editable or independent wheel install."""

import importlib.abc
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path


class BlockBackendImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"app", "blob_controller", "mlops_blob"}:
            raise AssertionError(f"Unexpected application or legacy import: {fullname}")
        return None


def check_install() -> None:
    sys.meta_path.insert(0, BlockBackendImports())
    import blob
    from blob.azure.storage import AzureBlobStorage
    from blob.s3.storage import S3BlobStorage

    import dataset_release
    import dataset_release.cli
    import dataset_release.reader
    from dataset_release.providers import (
        DatasetAzureBlobStorage,
        DatasetS3BlobStorage,
    )

    assert issubclass(DatasetS3BlobStorage, S3BlobStorage)
    assert issubclass(DatasetAzureBlobStorage, AzureBlobStorage)
    assert not any(name == "app" or name.startswith("app.") for name in sys.modules)
    subprocess.run(
        [sys.executable, "-I", "-m", "dataset_release", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    print(f"nachet-blob {version('nachet-blob')}: {Path(blob.__file__).resolve()}")
    print(
        f"nachet-dataset-release {version('nachet-dataset-release')}: "
        f"{Path(dataset_release.__file__).resolve()}"
    )
    print("Provider inheritance and CLI verified; no backend or legacy imports")


if __name__ == "__main__":
    check_install()
