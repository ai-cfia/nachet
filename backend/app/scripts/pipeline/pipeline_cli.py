#!/usr/bin/env python3
"""
Pipeline CLI Tool - Create models and pipelines from YAML configuration.

Usage:
    uv run app/scripts/pipeline/pipeline_cli.py --create --file config.yaml
    uv run app/scripts/pipeline/pipeline_cli.py --create --file config.yaml --dry-run
    uv run app/scripts/pipeline/pipeline_cli.py --help
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, date
from uuid import UUID

import yaml
from dotenv import load_dotenv
from sqlalchemy import select

from app.db.utils import sessionmanager
from app.db.model import Model, Pipeline, PipelineModel
from app.api.config import get_settings

VALID_REQUEST_FUNCTIONS = {
    "triton_detector",
    "triton_classifier",
    "triton_segmenter",
    "triton_classifier_batch",
    "triton_ensemble_a",
    "triton_ensemble_b",
}


def load_yaml_config(file_path: Path) -> dict:
    """Load YAML configuration file."""
    try:
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"YAML parse error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        sys.exit(1)


def validate_config(config: dict) -> list[str]:
    """Validate configuration structure. Returns list of errors."""
    errors = []

    # Collect all model names to check for duplicates
    all_model_names: set[str] = set()

    # Validate existing_models (optional section)
    for i, entry in enumerate(config.get("existing_models", [])):
        prefix = f"existing_models[{i}]"
        if "name" not in entry:
            errors.append(f"{prefix}: missing required field 'name'")
        if "id" not in entry:
            errors.append(f"{prefix}: missing required field 'id'")
        else:
            # Validate UUID format
            try:
                UUID(entry["id"])
            except ValueError:
                errors.append(f"{prefix}: invalid UUID format for 'id': {entry['id']}")
        if "name" in entry:
            if entry["name"] in all_model_names:
                errors.append(f"{prefix}: duplicate model name '{entry['name']}'")
            all_model_names.add(entry["name"])

    # Validate models
    for i, model in enumerate(config.get("models", [])):
        prefix = f"models[{i}]"
        for field in [
            "name",
            "task",
            "endpoint_name",
            "api_url",
            "api_key",
            "created_by",
            "date_model_training",
        ]:
            if field not in model:
                errors.append(f"{prefix}: missing required field '{field}'")
        # Check for duplicate names (including conflicts with existing_models)
        if "name" in model:
            if model["name"] in all_model_names:
                errors.append(f"{prefix}: duplicate model name '{model['name']}'")
            all_model_names.add(model["name"])

    # Validate pipelines
    for i, pipeline in enumerate(config.get("pipelines", [])):
        prefix = f"pipelines[{i}]"
        if "name" not in pipeline:
            errors.append(f"{prefix}: missing required field 'name'")
        if "steps" not in pipeline or not pipeline["steps"]:
            errors.append(f"{prefix}: missing or empty 'steps'")
        else:
            for j, step in enumerate(pipeline["steps"]):
                step_prefix = f"{prefix}.steps[{j}]"
                for field in ["model", "step", "request_function"]:
                    if field not in step:
                        errors.append(
                            f"{step_prefix}: missing required field '{field}'"
                        )
                if (
                    "request_function" in step
                    and step["request_function"] not in VALID_REQUEST_FUNCTIONS
                ):
                    errors.append(
                        f"{step_prefix}: invalid request_function '{step['request_function']}'. "
                        f"Valid: {', '.join(sorted(VALID_REQUEST_FUNCTIONS))}"
                    )

    return errors


async def resolve_existing_models(
    session, existing_models: list[dict], dry_run: bool
) -> dict[str, UUID] | None:
    """Resolve existing model UUIDs and return alias->UUID map."""
    model_map: dict[str, UUID] = {}
    for entry in existing_models:
        alias = entry["name"]
        model_id = UUID(entry["id"])

        # Verify model exists and is active
        stmt = select(Model).where(Model.id == model_id, Model.active.is_(True))
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            print(f"  Error: Model not found or inactive: {model_id}")
            return None

        if dry_run:
            print(f"  Found existing model: {alias} -> {model.name} ({model_id})")
        else:
            print(f"  Using existing model: {alias} -> {model.name} ({model_id})")

        model_map[alias] = model_id

    return model_map


async def create_model(session, model_config: dict, dry_run: bool) -> UUID | None:
    """Create a model from configuration. Returns model UUID."""
    name = model_config["name"]
    task_id = int(model_config["task"])

    # Check if model already exists
    stmt = select(Model).where(Model.name == name, Model.active.is_(True))
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  Model already exists: {name} -> {existing.id}")
        return UUID(str(existing.id))

    if dry_run:
        print(f"  Would create model: {name} (task_id={task_id})")
        return None

    # Parse training date
    date_str = model_config["date_model_training"]
    if isinstance(date_str, str):
        training_date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        training_date = date_str

    model = Model(
        name=name,
        task_id=task_id,
        endpoint_name=model_config["endpoint_name"],
        api_url=model_config["api_url"],
        api_key=model_config["api_key"],
        created_by=model_config["created_by"],
        date_model_training=training_date,
        version=model_config.get("version"),
        description=model_config.get("description"),
        deployment_platform=model_config.get("deployment_platform", "on-prem"),
        content_type=model_config.get("content_type", "application/json"),
        job_name=model_config.get("job_name"),
        dataset=model_config.get("dataset"),
        artifacts_url=model_config.get("artifacts_url"),
        sha256=model_config.get("sha256"),
    )
    session.add(model)
    await session.flush()
    print(f"  Created model: {name} -> {model.id}")
    return UUID(str(model.id))


async def create_pipeline(
    session, pipeline_config: dict, model_map: dict[str, UUID], dry_run: bool
) -> UUID | None:
    """Create a pipeline with its steps. Returns pipeline UUID."""
    name = pipeline_config["name"]

    # Check if pipeline already exists
    stmt = select(Pipeline).where(Pipeline.name == name, Pipeline.active.is_(True))
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  Pipeline already exists: {name} -> {existing.id}")
        return UUID(str(existing.id))

    # Validate all model references exist
    for step in pipeline_config["steps"]:
        model_name = step["model"]
        if model_name not in model_map:
            print(f"  Error: Model '{model_name}' not found for pipeline '{name}'")
            return None

    if dry_run:
        print(f"  Would create pipeline: {name}")
        for step in pipeline_config["steps"]:
            print(
                f"    Step {step['step']}: {step['model']} ({step['request_function']})"
            )
        return None

    # Parse creation_date if provided
    creation_date_value = None
    if "creation_date" in pipeline_config:
        date_str = pipeline_config["creation_date"]
        if isinstance(date_str, str):
            creation_date_value = datetime.strptime(date_str, "%Y-%m-%d").date()
        elif isinstance(date_str, date):
            creation_date_value = date_str

    # Create pipeline
    pipeline = Pipeline(
        name=name,
        created_by=pipeline_config.get("created_by"),
        description=pipeline_config.get("description"),
        version=pipeline_config.get("version"),
        default=pipeline_config.get("default", False),
        creation_date=creation_date_value,
        job_name=pipeline_config.get("job_name"),
        dataset=pipeline_config.get("dataset"),
        identifiable=pipeline_config.get("identifiable"),
        metrics=pipeline_config.get("metrics"),
        data={},  # Required legacy field
    )
    session.add(pipeline)
    await session.flush()

    # Create pipeline steps
    for step_config in pipeline_config["steps"]:
        model_id = model_map[step_config["model"]]
        pipeline_model = PipelineModel(
            pipeline_id=pipeline.id,
            model_id=model_id,
            step=step_config["step"],
            request_function=step_config["request_function"],
        )
        session.add(pipeline_model)

    await session.flush()
    print(f"  Created pipeline: {name} -> {pipeline.id}")
    for step in pipeline_config["steps"]:
        print(f"    Step {step['step']}: {step['model']} ({step['request_function']})")
    return UUID(str(pipeline.id))


async def process_config(config: dict, dry_run: bool) -> bool:
    """Process YAML configuration and create entities."""
    existing_model_aliases = [m["name"] for m in config.get("existing_models", [])]
    model_names = [m["name"] for m in config.get("models", [])]
    pipeline_names = [p["name"] for p in config.get("pipelines", [])]

    # Show summary and confirm
    if not dry_run:
        print("\nWill create:")
        if existing_model_aliases:
            print(
                f"  Existing models to reference: {len(existing_model_aliases)} "
                f"({', '.join(existing_model_aliases)})"
            )
        if model_names:
            print(f"  New models: {len(model_names)} ({', '.join(model_names)})")
        if pipeline_names:
            print(f"  Pipelines: {len(pipeline_names)} ({', '.join(pipeline_names)})")
        print()

        confirmation = input("Proceed? (yes/no): ")
        if confirmation.lower() not in ["yes", "y"]:
            print("Cancelled.")
            return False

    async with sessionmanager.get_session() as session:
        model_map: dict[str, UUID] = {}

        # Step 1: Resolve existing models by UUID
        if config.get("existing_models"):
            print("\nResolving existing models...")
            existing_map = await resolve_existing_models(
                session, config["existing_models"], dry_run
            )
            if existing_map is None:
                return False
            model_map.update(existing_map)

        # Step 2: Create new models
        if config.get("models"):
            print("\nProcessing new models...")
            for model_config in config["models"]:
                model_id = await create_model(session, model_config, dry_run)
                if model_id is not None:
                    model_map[model_config["name"]] = model_id

        # For dry-run, also include any models referenced by pipelines that might exist
        if dry_run and config.get("pipelines"):
            for pipeline_config in config["pipelines"]:
                for step in pipeline_config["steps"]:
                    model_name = step["model"]
                    if model_name not in model_map:
                        stmt = select(Model).where(
                            Model.name == model_name, Model.active.is_(True)
                        )
                        result = await session.execute(stmt)
                        existing = result.scalar_one_or_none()
                        if existing:
                            model_map[model_name] = UUID(str(existing.id))

        # Step 3: Create pipelines
        if config.get("pipelines"):
            print("\nProcessing pipelines...")
            for pipeline_config in config["pipelines"]:
                pipeline_id = await create_pipeline(
                    session, pipeline_config, model_map, dry_run
                )
                if pipeline_id is None and not dry_run:
                    await session.rollback()
                    return False

        if not dry_run:
            await session.commit()

    # Summary
    print("\nDone.")
    if dry_run:
        print("(dry-run: no changes made)")
    else:
        created = []
        if model_names:
            created.append(f"{len(model_names)} model(s)")
        if pipeline_names:
            created.append(f"{len(pipeline_names)} pipeline(s)")
        if created:
            print(f"Created: {', '.join(created)}")

    return True


async def disable_model_cmd(model_id: UUID) -> bool:
    """Disable a model and cascade to related pipelines."""
    async with sessionmanager.get_session() as session:
        # Find the model
        stmt = select(Model).where(Model.id == model_id)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            print(f"Model not found: {model_id}")
            return False

        if not model.active:
            print(f"Model already disabled: {model.name} ({model_id})")
            return True

        # Find affected pipelines via PipelineModel
        stmt = select(PipelineModel).where(
            PipelineModel.model_id == model_id, PipelineModel.active.is_(True)
        )
        result = await session.execute(stmt)
        pipeline_models = result.scalars().all()

        # Get unique pipeline IDs
        pipeline_ids = {pm.pipeline_id for pm in pipeline_models}

        # Fetch pipeline details for display
        affected_pipelines: list[Pipeline] = []
        for pid in pipeline_ids:
            stmt = select(Pipeline).where(Pipeline.id == pid, Pipeline.active.is_(True))
            result = await session.execute(stmt)
            pipeline = result.scalar_one_or_none()
            if pipeline:
                affected_pipelines.append(pipeline)

        # Show confirmation
        print("\nWill disable:")
        print(f"  Model: {model.name} ({model_id})")
        if affected_pipelines:
            print(f"  Affected pipelines: {len(affected_pipelines)}")
            for p in affected_pipelines:
                print(f"    - {p.name} ({p.id})")
        print()

        confirmation = input("Proceed? (yes/no): ")
        if confirmation.lower() not in ["yes", "y"]:
            print("Cancelled.")
            return False

        # Disable model
        model.active = False
        print(f"\n  Model: {model.name} -> disabled")

        # Disable PipelineModel entries
        for pm in pipeline_models:
            pm.active = False

        # Disable affected pipelines
        for p in affected_pipelines:
            p.active = False
            print(f"  Pipeline: {p.name} -> disabled")

        await session.commit()

    print(f"\nDone. Disabled 1 model, {len(affected_pipelines)} pipeline(s).")
    return True


async def disable_pipeline_cmd(pipeline_id: UUID) -> bool:
    """Disable a pipeline (models unaffected)."""
    async with sessionmanager.get_session() as session:
        # Find the pipeline
        stmt = select(Pipeline).where(Pipeline.id == pipeline_id)
        result = await session.execute(stmt)
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            print(f"Pipeline not found: {pipeline_id}")
            return False

        if not pipeline.active:
            print(f"Pipeline already disabled: {pipeline.name} ({pipeline_id})")
            return True

        # Show confirmation
        print("\nWill disable:")
        print(f"  Pipeline: {pipeline.name} ({pipeline_id})")
        print()

        confirmation = input("Proceed? (yes/no): ")
        if confirmation.lower() not in ["yes", "y"]:
            print("Cancelled.")
            return False

        # Disable pipeline
        pipeline.active = False
        print(f"\n  Pipeline: {pipeline.name} -> disabled")

        # Disable PipelineModel entries
        stmt = select(PipelineModel).where(
            PipelineModel.pipeline_id == pipeline_id, PipelineModel.active.is_(True)
        )
        result = await session.execute(stmt)
        pipeline_models = result.scalars().all()

        for pm in pipeline_models:
            pm.active = False

        await session.commit()

    print("\nDone.")
    return True


async def enable_model_cmd(model_id: UUID) -> bool:
    """Enable a model."""
    async with sessionmanager.get_session() as session:
        # Find the model
        stmt = select(Model).where(Model.id == model_id)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            print(f"Model not found: {model_id}")
            return False

        if model.active:
            print(f"Model already enabled: {model.name} ({model_id})")
            return True

        # Show confirmation
        print("\nWill enable:")
        print(f"  Model: {model.name} ({model_id})")
        print()

        confirmation = input("Proceed? (yes/no): ")
        if confirmation.lower() not in ["yes", "y"]:
            print("Cancelled.")
            return False

        # Enable model
        model.active = True
        print(f"\n  Model: {model.name} -> enabled")

        await session.commit()

    print("\nDone.")
    return True


async def enable_pipeline_cmd(pipeline_id: UUID) -> bool:
    """Enable a pipeline and cascade to related models."""
    async with sessionmanager.get_session() as session:
        # Find the pipeline
        stmt = select(Pipeline).where(Pipeline.id == pipeline_id)
        result = await session.execute(stmt)
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            print(f"Pipeline not found: {pipeline_id}")
            return False

        if pipeline.active:
            print(f"Pipeline already enabled: {pipeline.name} ({pipeline_id})")
            return True

        # Find PipelineModel entries (active or not)
        stmt = select(PipelineModel).where(PipelineModel.pipeline_id == pipeline_id)
        result = await session.execute(stmt)
        pipeline_models = result.scalars().all()

        # Get unique model IDs and fetch models
        model_ids = {pm.model_id for pm in pipeline_models}
        affected_models: list[Model] = []
        for mid in model_ids:
            stmt = select(Model).where(Model.id == mid)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model and not model.active:
                affected_models.append(model)

        # Show confirmation
        print("\nWill enable:")
        print(f"  Pipeline: {pipeline.name} ({pipeline_id})")
        if affected_models:
            print(f"  Related models: {len(affected_models)}")
            for m in affected_models:
                print(f"    - {m.name} ({m.id})")
        print()

        confirmation = input("Proceed? (yes/no): ")
        if confirmation.lower() not in ["yes", "y"]:
            print("Cancelled.")
            return False

        # Enable pipeline
        pipeline.active = True
        print(f"\n  Pipeline: {pipeline.name} -> enabled")

        # Enable PipelineModel entries
        for pm in pipeline_models:
            pm.active = True

        # Enable affected models
        for m in affected_models:
            m.active = True
            print(f"  Model: {m.name} -> enabled")

        await session.commit()

    print("\nDone.")
    return True


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Pipeline CLI Tool - Manage models and pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create from YAML file
  uv run app/scripts/pipeline/pipeline_cli.py --create --file config.yaml

  # Validate without creating (dry-run)
  uv run app/scripts/pipeline/pipeline_cli.py --create --file config.yaml --dry-run

  # Disable a model (cascades to pipelines)
  uv run app/scripts/pipeline/pipeline_cli.py --disable-model <uuid>

  # Disable a pipeline
  uv run app/scripts/pipeline/pipeline_cli.py --disable-pipeline <uuid>

  # Enable a model
  uv run app/scripts/pipeline/pipeline_cli.py --enable-model <uuid>

  # Enable a pipeline (cascades to models)
  uv run app/scripts/pipeline/pipeline_cli.py --enable-pipeline <uuid>
        """,
    )
    parser.add_argument(
        "--create", action="store_true", help="Create models and pipelines from YAML"
    )
    parser.add_argument(
        "--file", metavar="FILE", help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate only, no database writes"
    )
    parser.add_argument(
        "--disable-model",
        metavar="UUID",
        help="Disable a model by UUID (cascades to pipelines)",
    )
    parser.add_argument(
        "--disable-pipeline", metavar="UUID", help="Disable a pipeline by UUID"
    )
    parser.add_argument("--enable-model", metavar="UUID", help="Enable a model by UUID")
    parser.add_argument(
        "--enable-pipeline",
        metavar="UUID",
        help="Enable a pipeline by UUID (cascades to models)",
    )

    args = parser.parse_args()

    # Check if any action specified
    has_action = (
        args.create
        or args.disable_model
        or args.disable_pipeline
        or args.enable_model
        or args.enable_pipeline
    )
    if not has_action:
        parser.print_help()
        return

    if args.create and not args.file:
        parser.error("--create requires --file")

    # Load environment
    if not os.getenv("NACHET_SCHEMA"):
        load_dotenv(".env.local")
        print("Loaded .env.local")

    # Initialize database
    try:
        settings = get_settings()
        if settings is None:
            raise ValueError("Settings could not be created")
        db_conn_info = settings.db_conn_info.copy()
        db_conn_info["echo"] = False
        sessionmanager.init(**db_conn_info)
        print(f"Connected to database: {settings.db_name}")
    except Exception as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)

    try:
        # Handle disable-model command
        if args.disable_model:
            try:
                model_uuid = UUID(args.disable_model)
            except ValueError:
                print(f"Invalid UUID: {args.disable_model}")
                sys.exit(1)
            success = await disable_model_cmd(model_uuid)
            sys.exit(0 if success else 1)

        # Handle disable-pipeline command
        if args.disable_pipeline:
            try:
                pipeline_uuid = UUID(args.disable_pipeline)
            except ValueError:
                print(f"Invalid UUID: {args.disable_pipeline}")
                sys.exit(1)
            success = await disable_pipeline_cmd(pipeline_uuid)
            sys.exit(0 if success else 1)

        # Handle enable-model command
        if args.enable_model:
            try:
                model_uuid = UUID(args.enable_model)
            except ValueError:
                print(f"Invalid UUID: {args.enable_model}")
                sys.exit(1)
            success = await enable_model_cmd(model_uuid)
            sys.exit(0 if success else 1)

        # Handle enable-pipeline command
        if args.enable_pipeline:
            try:
                pipeline_uuid = UUID(args.enable_pipeline)
            except ValueError:
                print(f"Invalid UUID: {args.enable_pipeline}")
                sys.exit(1)
            success = await enable_pipeline_cmd(pipeline_uuid)
            sys.exit(0 if success else 1)

        # Handle create command
        if args.create:
            file_path = Path(args.file)
            print(f"Loading {file_path}...")
            config = load_yaml_config(file_path)

            errors = validate_config(config)
            if errors:
                print("\nValidation errors:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)

            success = await process_config(config, args.dry_run)
            sys.exit(0 if success else 1)

    finally:
        await sessionmanager.close()


if __name__ == "__main__":
    asyncio.run(main())
