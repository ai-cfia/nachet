# Temporary MLOps copy of `app.blob`

This package copies the provider-independent interface, exceptions, models,
validation, factory and S3/Azure implementations from `backend/app/blob/` at
repository revision `88212e11aca9b76d93025e4ce89b0e38b82d681f`.
The backend originals are unchanged. This package ships as the standalone `nachet-blob` distribution. Installing
`mlops/blob/` installs `mlops_blob` without backend or dataset release code.

The application-specific manager, account registry, health checks, backend
logging service and backend tests are deliberately excluded. Providers are
created through `create_blob_storage_client(provider, config)` and implement
`BlobStorageInterface`. Provider implementations expose async methods around synchronous SDKs. Consumers
that need non-blocking execution must run those calls in workers. The dataset
adapter and its worker execution remain in the separate dataset release PR.

## Differences to preserve when extracting the shared package

- Imports refer to `mlops_blob`; a standard-library logging shim replaces
  `app.service.logs`. No application startup, FastAPI dependency or backend
  storage manager is imported.
- S3 `overwrite=False` uses `IfNoneMatch="*"` on the PUT itself. A 412 response
  becomes the common `BlobAlreadyExistsError`. Unsupported conditions, access
  failures and 409 conditional-write conflicts propagate as failures; there is
  no retry that removes the condition.
- S3 upload/download do not issue existence checks before the actual request.
  Missing-object responses retain the common exception. Downloaded response
  streams are closed after reading, including on read failure.
- S3 credentials can be omitted to use boto3's normal credential chain. Explicit
  access/secret keys must be paired; explicit session tokens are supported. Client
  construction does not call `ListBuckets`, allowing bucket-scoped credentials.
- Azure accepts an explicit connection string as well as the original config
  dictionary. `overwrite=False` uses the Azure SDK's create-only behavior, and
  its `ResourceExistsError` becomes the same common `BlobAlreadyExistsError`.
- Both providers implement the added `close()` interface method to release SDK
  connection pools. Imports/formatting were normalized with the project's lint
  settings; provider operations unrelated to dataset releases remain copied.

The next extraction can move this package to `nachet/common`, including these
fixes and their contract tests, then switch both backend and MLOps imports to
the shared package. Do that packaging/import migration in a separate PR.
Until then, fixes to either copy need an explicit comparison against the other.

Provider tests run independently of backend and dataset release code. They use
real copied providers with deterministic fake SDK transports to verify conflicts,
non-overwriting requests, missing objects, stream/client cleanup and configuration.
Live service behavior and provider operations outside those tests remain unverified.
