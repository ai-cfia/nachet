# DatasetController

Standalone uv package for the reviewed dataset release workflow. It reuses
[`nachet-blob`](../blob/README.md) without importing the backend application or
the `dataset_release` consumer.

The public `DatasetController` facade exposes `create_release`, `prepare_coco`,
`export_json`, `publish`, `registration`, `resolve` and `read_file`. Its constructor
takes a blob storage implementation, an async
SQLAlchemy session factory and an existing container name. The caller provisions
the registry and owns the lifetime of the storage client and database engine.
The calling project also supplies its database driver (`psycopg` for PostgreSQL
or `aiosqlite` for SQLite); the existing release consumer includes both.
Metadata, membership and reviewed labels are database entities. New releases
generate JSON documents on request; existing blob snapshots remain readable.
Pass `storage=None` for database-only preparation and document exports.

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
    dataset.py                  # Dataset, release definitions, membership and metadata
    manifest.py                 # manifest, file inventory and crop models
  services/
    dataset_service.py          # draft preparation, publication and retry lifecycle
    manifest_service.py         # deterministic identities and manifest generation
    validation_service.py       # ML image, membership and integrity validation
    query_service.py            # release metadata lookup and pinned resolution
    preparation_service.py      # exact COCO-to-membership remapping
  repositories/
    blob_repository.py          # thin wrapper around the existing blob providers
    registry.py                 # release, membership and crop table mappings
    catalog.py                  # SQL preparation records and output inventories
  config/dataset_config.py      # explicit registry environment configuration
  utility/crop.py               # existing PNG validation and crop implementation
```

The services retain atomic non-overwriting writes, recoverable staging
registrations, manifest pinning, checksums, split/provenance validation and
optional crop generation. Blob providers remain in `mlops/blob/`. The command,
FiftyOne export, training reader and Alembic migrations remain in
[`mlops/datasets/`](../datasets/README.md), which installs this package as a local
editable dependency. The consumer has no duplicate controller, catalog or model
implementation. Apply its database migrations before using the new workflow;
see the [migration runbook](../datasets/README.md#migration-runbook).

This extraction only covers releases. It does not add dataset discovery,
arbitrary metadata search or sampling. `QueryService` looks up release metadata
by name/version, checks container ownership and resolves a pinned release.
`Dataset` describes the reviewed COCO release and its members are `DatasetMember`
models. `ReleaseSpec` and `CocoImage` remain aliases for existing release callers;
legacy serialized data and hashes remain supported. New database records retain
the reviewed release information needed to regenerate COCO and manifests.

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
