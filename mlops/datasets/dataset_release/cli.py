"""Publish, inspect, or validate a reviewed dataset release (administrative job)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from .contract import ConversionRecipe, ImageMembership, ReleaseDefinition, Source
from .errors import ConfigurationError
from .registry import registry_engine
from .release import DatasetController, ReleaseConflict, ReleaseNotReady
from .settings import Settings
from .storage import BlobStorageAdapter


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse release preparation, publication, and export commands for a container."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--container", required=True, help="Existing dataset bucket/container"
    )
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser(
        "create", help="Register release metadata as a database draft"
    )
    create.add_argument("name")
    create.add_argument("version")
    create.add_argument("--author", required=True)
    create.add_argument("--conversion-revision", required=True)
    create.add_argument(
        "--setting",
        action="append",
        default=[],
        help="PNG conversion setting KEY=VALUE (JSON or plain text)",
    )
    create.add_argument("--description")
    create.add_argument("--dataset-cutoff-date")
    create.add_argument("--previous-version")
    create.add_argument("--generate-crops", action="store_true")
    member = actions.add_parser(
        "add-image", help="Add an offline export's image membership to a draft"
    )
    member.add_argument("name")
    member.add_argument("version")
    member.add_argument(
        "--file-name", required=True, help="Exact exported COCO file_name"
    )
    member.add_argument("--sha256", required=True)
    member.add_argument(
        "--split", required=True, choices=("train", "validation", "test")
    )
    member.add_argument("--original-path")
    member.add_argument("--specimen-group")
    export = actions.add_parser(
        "export", help="Generate JSON on request from release records"
    )
    export.add_argument("name")
    export.add_argument("version")
    export.add_argument(
        "document", choices=("metadata", "membership", "spec", "coco", "manifest")
    )
    export.add_argument(
        "--output", type=Path, help="New output file (otherwise print JSON)"
    )
    for command in ("publish", "inspect", "validate"):
        action = actions.add_parser(command)
        action.add_argument("name")
        action.add_argument("version")
        if command != "publish":
            action.add_argument("--expected-manifest-sha256")
    return parser.parse_args(argv)


async def run_dataset_release_command(args: argparse.Namespace) -> dict | list:
    """Run the selected release command and return its JSON-compatible result.

    The registry must already be provisioned. Database and storage resources
    are released after the command, including when publication or validation fails.
    """
    # Registry provisioning is an explicit MLOps operation, separate from the
    # backend application's database and Alembic revision history.
    settings = Settings.from_environment()
    engine = registry_engine(settings.database_url, settings.registry_schema)
    storage = None
    try:
        if args.action in ("publish", "inspect", "validate") or (
            args.action == "export" and args.document == "manifest"
        ):
            storage = await asyncio.to_thread(BlobStorageAdapter.from_environment)
        controller = DatasetController(
            storage, async_sessionmaker(engine), args.container
        )
        if args.action == "create":
            conversion_settings = {}
            for setting in args.setting:
                key, separator, value = setting.partition("=")
                if not separator or not key or key in conversion_settings:
                    raise ConfigurationError(
                        "Each --setting must have a unique KEY=VALUE"
                    )
                try:
                    conversion_settings[key] = json.loads(value)
                except json.JSONDecodeError:
                    conversion_settings[key] = value
            registration = await controller.create_release(
                ReleaseDefinition(
                    name=args.name,
                    version=args.version,
                    author=args.author,
                    conversion=ConversionRecipe(
                        code_revision=args.conversion_revision,
                        settings=conversion_settings,
                    ),
                    description=args.description,
                    dataset_cutoff_date=args.dataset_cutoff_date,
                    previous_version=args.previous_version,
                    generate_crops=args.generate_crops,
                )
            )
            return {
                "name": registration.name,
                "version": registration.version,
                "status": registration.status,
            }
        elif args.action == "add-image":
            sources = []
            if args.original_path:
                sources = [
                    Source(
                        original_path=args.original_path,
                        specimen_group=args.specimen_group,
                    )
                ]
            elif args.specimen_group:
                raise ConfigurationError("--specimen-group requires --original-path")
            await controller.catalog.add_membership(
                args.name,
                args.version,
                ImageMembership(
                    file_name=args.file_name,
                    sha256=args.sha256,
                    split=args.split,
                    sources=sources,
                ),
            )
            return {
                "name": args.name,
                "version": args.version,
                "file_name": args.file_name,
            }
        elif args.action == "export":
            if (
                args.document == "coco"
                and not (
                    await controller.get_release_registration(args.name, args.version)
                ).database_backed
            ):
                storage = await asyncio.to_thread(BlobStorageAdapter.from_environment)
                controller.storage = storage
            data = await controller.export_json(args.name, args.version, args.document)
            if args.output:
                with args.output.open("xb") as output:
                    output.write(data)
                return {"output": str(args.output)}
            return json.loads(data)
        elif args.action == "publish":
            registration = await controller.publish_release(args.name, args.version)
        else:
            registration, manifest, coco = await controller.load_verified_release(
                args.name, args.version, args.expected_manifest_sha256
            )
            if args.action == "inspect":
                return {
                    **registration.training_reference(),
                    **registration.metadata().model_dump(mode="json"),
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
        if storage is not None:
            await asyncio.to_thread(storage.close)


def main(argv: Sequence[str] | None = None) -> int:
    """Load CLI settings, print the result, and report errors without credentials."""
    # Parse first so --help works without credentials or database configuration.
    args = parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv(os.environ.get("DATASET_ENV_FILE", ".env"))
    try:
        result = asyncio.run(run_dataset_release_command(args))
    except (ConfigurationError, ReleaseConflict, ReleaseNotReady) as error:
        raise SystemExit(f"Dataset release failed: {error}") from None
    except Exception as error:
        # Do not echo settings or connection strings (which include credentials).
        raise SystemExit(f"Dataset release failed: {type(error).__name__}") from error
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
