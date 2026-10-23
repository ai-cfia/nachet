"""Publish, inspect, or validate a reviewed dataset release (administrative job)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.datasets.contract import ReleaseSpec
from app.datasets.release import DatasetController, ReleaseConflict, ReleaseNotReady


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--container", required=True, help="Existing dataset bucket/container"
    )
    actions = parser.add_subparsers(dest="action", required=True)
    publish = actions.add_parser(
        "publish", help="Validate and publish a release specification"
    )
    publish.add_argument("spec", type=Path)
    for command in ("inspect", "validate"):
        action = actions.add_parser(command)
        action.add_argument("name")
        action.add_argument("version")
        action.add_argument("--expected-manifest-sha256")
    return parser.parse_args(argv)


async def execute(args: argparse.Namespace) -> dict:
    # Use the existing provider and connection configuration. No bucket/schema
    # creation, app upload flow, or production migration is performed by this CLI.
    from app.api.config import Settings
    from app.blob import create_blob_storage_client

    settings = Settings()
    storage = create_blob_storage_client("s3", settings.s3_storage_config)
    engine = create_async_engine(settings.db_conn_info["url"])
    try:
        controller = DatasetController(
            storage, async_sessionmaker(engine), args.container
        )
        if args.action == "publish":
            spec = ReleaseSpec.model_validate_json(args.spec.read_bytes())
            registration = await controller.publish(spec)
        else:
            registration, manifest, coco = await controller.resolve(
                args.name, args.version, args.expected_manifest_sha256
            )
            if args.action == "inspect":
                return {
                    **registration.training_reference(),
                    "images": len(coco.images),
                    "annotations": len(coco.annotations),
                    "crops": len(manifest.crops),
                    "classifier_ready": manifest.crop_recipe is not None,
                    "splits": {
                        split: sum(image.split == split for image in coco.images)
                        for split in ("train", "validation", "test")
                    },
                }
        return registration.training_reference()
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    # Match other backend command-line tools while keeping --help import-light.
    args = parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv(os.environ.get("NACHET_ENV_FILE", ".env"))
    try:
        result = asyncio.run(execute(args))
    except (ReleaseConflict, ReleaseNotReady) as error:
        raise SystemExit(f"Dataset release failed: {error}") from None
    except Exception as error:
        # Do not echo settings or connection strings (which include credentials).
        raise SystemExit(f"Dataset release failed: {type(error).__name__}") from error
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
