# MLOps blob storage

Standalone temporary copy of backend `app.blob` for preparation and dataset
release consumers. Backend code is unchanged. A later PR will consolidate the
copies into `nachet/common`.

From this directory:

```sh
uv sync --locked
uv run --no-sync ruff check mlops_blob tests
uv run --no-sync ruff format --check mlops_blob tests
uv run --no-sync pytest
uv build --wheel
```

Other uv projects can install this project as a local editable dependency:
`uv add --editable ../blob` from a sibling project such as `mlops/datasets`.
The Python import remains `mlops_blob`.

When integrating the dataset release branch, keep its `dataset_release` package
and adapter there, remove its embedded blob copy, and change its wheel package
list to `["dataset_release"]`. Depend on `nachet-blob` through the local project
path and regenerate the dataset lockfile. Keep dataset adapter/integration tests
in that project; provider tests and their CI checks belong here.

See [copy provenance and provider differences](mlops_blob/README.md).
