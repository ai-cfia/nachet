# Blob controller

The `blob-controller` project is a standalone temporary copy of backend
`app.blob` for preparation and dataset release consumers. Backend code is
unchanged. A later PR will consolidate the copies into `nachet/common`.

Provider sources live directly in `azure/` and `s3/`, with the shared interface,
models, exceptions and helpers at this project root. Packaging maps this flat
source layout to the `blob_controller` import namespace for both editable
installs and wheels; there is no nested `blob_controller/` source directory.

From this directory:

```sh
uv sync --locked
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync python -I -m pytest
uv build --wheel
```

Other uv projects can install this project as a local editable dependency:
`uv add --editable ../blob` from a sibling project such as `mlops/datasets`.
The Python import is `blob_controller`.

When running Python from this source directory, use `uv run python -I` so the
local `azure/` provider directory does not shadow the installed Azure SDK.
Consumers installed in other projects import `blob_controller` directly.

When integrating the dataset release branch, keep its `dataset_release` package
and adapter there, remove its embedded blob copy, and change its wheel package
list to `["dataset_release"]`. Depend on `blob-controller` through the local project
path and regenerate the dataset lockfile. Keep dataset adapter/integration tests
in that project; provider tests and their CI checks belong here.

See [copy provenance and provider differences](PROVENANCE.md).
