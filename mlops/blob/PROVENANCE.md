# Temporary copy of backend blob storage

The starting point is the complete `backend/app/blob/` copy in repository commit
`9d76d770fd757495f3e8c8d2ee46d9432fa18c08`. The backend files remain unchanged.
This directory installs as the `nachet-blob` distribution with Python imports
under `blob`. The flat `azure/` and `s3/` source layout is preserved.

## Changes needed to use the copy

- Internal absolute `app.blob` imports become relative imports. This keeps the
  provider implementation within this package and makes later relocation easier.
- Lazy `app.service.logs` imports point to local `logs.py`. Its small `LogService`
  facade returns the same process-wide Loguru logger used by the backend, without
  importing backend logging initialization or OpenTelemetry services. The consumer
  owns logging configuration.
- The copied manager's `Bucket` import points to `constants.py`, containing only
  the unchanged `Bucket` enum from `backend/app/service/constants.py`.
- Copied tests import `blob`; live-service tests use storage-only environment
  settings instead of importing the backend API application. They require explicit
  opt-in. The original test files, fixtures, and naming documents remain present.
- Packaging metadata, a dependency lockfile, installation checks, and CI are added.
  Tests and backend application code are excluded from the wheel.

## Behavior and future ownership

The interface, factory, manager, validation, models, exceptions, and provider
operation logic remain copied. This extraction does not change credential rules,
upload conditions, existence checks, connection-string handling, error mapping,
SDK cleanup, or the synchronous SDK calls behind the async provider methods.
The account manager and its backend-oriented startup helpers are retained for
copy parity; dataset consumers can construct providers through the factory.

A later PR can move the reusable package into `nachet/common`, update the package
mapping and consumer dependencies, and point both backend and MLOps to it.
Application-specific startup ownership can be settled in that PR. Keep provider
behavior fixes separate from the copy and import migration.

The `blob` import namespace is independent of its current MLOps source location.
Future MLOps-specific behavior belongs in consumer adapters using composition or
inheritance, keeping the shared provider implementation reusable by the backend.
