# DatasetController

Standalone uv package for the reviewed dataset release workflow. It reuses
[`nachet-blob`](../blob/README.md) without importing the backend application or
the `dataset_release` consumer.

The public `DatasetController` facade exposes `publish`, `registration`, `resolve`
and `read_file`. Its constructor takes a blob storage implementation, an async
SQLAlchemy session factory and an existing container name. The caller provisions
the registry and owns the lifetime of the storage client and database engine.
The calling project also supplies its database driver (`psycopg` for PostgreSQL
or `aiosqlite` for SQLite); the existing release consumer includes both.

```python
from dataset_controller import Dataset, DatasetController
from dataset_controller.config.dataset_config import Settings
from dataset_controller.repositories.blob_repository import BlobStorageAdapter
from dataset_controller.repositories.registry import registry_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

settings = Settings.from_environment()
engine = registry_engine(settings.database_url, settings.registry_schema)
storage = BlobStorageAdapter.from_environment()
controller = DatasetController(storage, async_sessionmaker(engine), "datasets")
```

Use the controller's async methods from an async job; close `storage` and dispose
`engine` when that job finishes. The existing release command handles this
lifecycle and runs synchronous storage work in workers.

```text
mlops/DatasetController/
  dataset_controller.py          # main controller facade
  models/
    dataset.py                  # Dataset, DatasetMember and release registration
    manifest.py                 # manifest, file inventory and crop models
  services/
    dataset_service.py          # publication, retry and registration lifecycle
    manifest_service.py         # deterministic identities and manifest generation
    validation_service.py       # ML image, membership and integrity validation
    query_service.py            # release metadata lookup and pinned resolution
  repositories/
    blob_repository.py          # thin wrapper around the existing blob providers
    registry.py                 # unchanged release table mapping
  config/dataset_config.py      # explicit registry environment configuration
  utility/crop.py               # existing PNG validation and crop implementation
```

The services retain atomic non-overwriting writes, recoverable staging
registrations, manifest pinning, checksums, split/provenance validation and
optional crop generation. Blob providers remain in `mlops/blob/`. The command,
FiftyOne export, training reader, examples and Alembic migrations remain in
[`mlops/datasets/`](../datasets/README.md), which installs this package as a local
editable dependency. No database schema or release file format changed.

This extraction only covers releases. It does not add dataset discovery,
arbitrary metadata search or sampling. `QueryService` looks up release metadata
by name/version, checks container ownership and resolves a pinned release.
`Dataset` describes the reviewed COCO release and its members are `DatasetMember`
models. `ReleaseSpec` and `CocoImage` remain aliases for existing release callers;
their serialized data, hashes and manifest format are unchanged.

The source layout follows the proposal directly. Packaging maps this project
root to the `dataset_controller` import namespace, including editable installs
and wheels; there is no nested source package. Use isolated Python (`python -I`)
when running from this directory so the facade file does not shadow that package.

Keep this project beside `mlops/blob/` when installing from source. From here:

```sh
uv sync --locked
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync python -I -m pytest
uv build --wheel
```

Wheel deployments also need the separate `nachet-blob` wheel. To use this API
from another uv project, add `nachet-dataset-controller` as a dependency and
point its `[tool.uv.sources]` entry at this directory.
