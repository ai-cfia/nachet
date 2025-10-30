"""
Dev database seeding script using ORM syntax.

This script contains functions to seed the development database with initial data
using SQLAlchemy ORM models instead of raw SQL.
"""

import os
import uuid
from datetime import datetime

# from sqlalchemy.orm import sessionmaker
from app.db.utils import SessionManager
from app.service.logs import LogService

from app.db.model import (
    # Base,
    ModelTask,
    Model,
    Pipeline,
    PipelineModel,
    PipelineDefault,
    Organization,
    Users,
    Folder,
    RbacPermission,
    RbacResource,
    RbacRolePermissionResource,
    RbacUserRole,
    DeviceBrand,
    DeviceModel,
    DeviceLens,
    # Seed,
    # SchemaVersion, # should already have data
    # Picture,       # lets keep it empty at seed time
    # Annotation,    # lets keep it empty at seed time
    # Object,        # lets keep it empty at seed time
)

from app.db.data.data_constants import seed_rbac_constants

# Module-level logger
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        _logger = LogService.get_logger()
    return _logger


async def seed_test_data(sessionmanager: SessionManager) -> None:
    """
    Seed the development database with initial data using ORM models.

    Args:
        async_engine: SQLAlchemy async engine (for backward compatibility)
    """
    # print("Dev data compatible semver: 0.2.0")
    # Use SessionManager's factory for consistent session management
    async_session = sessionmanager.get_session_factory()

    # Get CFIA organization and admin role IDs from environment
    cfia_org_id = uuid.UUID(
        os.getenv("CFIA_ORGANIZATION_ID", "12345678-1234-1234-1234-123456789012")
    )
    cfia_admin_role_id = uuid.UUID(
        os.getenv("CFIA_ADMIN_ROLE_ID", "87654321-4321-4321-4321-210987654321")
    )

    # Add device brand and models
    async with async_session.begin() as session:
        device_brand = DeviceBrand(
            id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            name="Test Device Brand",
            description="Default test device brand for development",
            active=True,
        )
        session.add(device_brand)

        device_model = DeviceModel(
            id=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            device_brand_id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            name="Test Camera Model",
            description="Default test camera model",
            active=True,
        )
        session.add(device_model)

        device_lens = DeviceLens(
            id=uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            device_brand_id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            name="Test Lens Model",
            description="Default test lens model",
            active=True,
        )
        session.add(device_lens)
    _get_logger().info("Device brand and models added")

    async with async_session.begin() as session:
        # Create model tasks first
        detection_task = ModelTask(
            id=1,
            name="Detection",
            active=True,
        )
        classification_task = ModelTask(
            id=2,
            name="Classification",
            active=True,
        )
        segmentation_task = ModelTask(
            id=3,
            name="Segmentation",
            active=True,
        )
        session.add_all([detection_task, classification_task, segmentation_task])
    _get_logger().info("Model tasks added")

    async with async_session.begin() as session:
        # Create models
        swin_15_model = Model(
            id=uuid.UUID("ecef8395-e6d5-47a3-8f3d-8424b4dd3816"),
            name="swin-15e-spp",
            endpoint_name="swin-15-spp-endpoint-2025",
            task_id=2,
            date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
            api_url="http://nachet-15spp-classifier:5001/score",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="15spp-e",
            active=True,
        )

        swin_27_model = Model(
            id=uuid.UUID("e83ee51e-830e-403a-a48f-d216ae91abb9"),
            name="swin-27-spp",
            endpoint_name="swin-27-spp-endpoint-2025",
            task_id=2,
            date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
            api_url="http://nachet-27spp-classifier:8080/predictions/27spp_120250130",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="27spp",
            active=True,
        )

        seed_detector_model = Model(
            id=uuid.UUID("52fd7ca2-8101-4541-ae49-d6d92ac69196"),
            name="seed-detector-rcnn-1",
            endpoint_name="seed-detector-2024",
            task_id=1,
            date_model_training=datetime(2024, 11, 13, 7, 40, 25, 867369),
            api_url="http://nachet-detector:5001/score",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="",
            active=True,
        )

        # Local versions of models for testing (deployment_platform='local', 127.0.0.1)
        swin_15_model_local = Model(
            id=uuid.UUID("a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c4d"),
            deployment_platform="local",
            name="swin-15e-spp-local",
            endpoint_name="swin-15-spp-local-endpoint",
            task_id=2,
            date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
            api_url="http://127.0.0.1:12390/score",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="15spp-e local test endpoint",
            active=True,
        )

        swin_27_model_local = Model(
            id=uuid.UUID("b2c3d4e5-f6a7-4b5c-8d7e-9f0a1b2c3d4e"),
            deployment_platform="local",
            name="swin-27-spp-local",
            endpoint_name="swin-27-spp-local-endpoint",
            task_id=2,
            date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
            api_url="http://127.0.0.1:12360/predictions/27spp_120250130",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="27spp local test endpoint",
            active=True,
        )

        seed_detector_model_local = Model(
            id=uuid.UUID("c3d4e5f6-a7b8-4c5d-8e7f-9a0b1c2d3e4f"),
            deployment_platform="local",
            name="seed-detector-rcnn-1-local",
            endpoint_name="seed-detector-local",
            task_id=1,
            date_model_training=datetime(2024, 11, 13, 7, 40, 25, 867369),
            api_url="http://127.0.0.1:12380/score",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="Local test detector endpoint",
            active=True,
        )

        session.add_all(
            [
                swin_15_model,
                swin_27_model,
                seed_detector_model,
                swin_15_model_local,
                swin_27_model_local,
                seed_detector_model_local,
            ]
        )
    _get_logger().info("Models added (including local test models)")

    async with async_session.begin() as session:
        # Create pipeline
        from datetime import date

        pipeline = Pipeline(
            id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            name="27 spp RCNN SWIN",
            active=True,
            # Use new normalized columns
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="Use a Swin transformer to classify the seeds",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=True,
            # Keep data field for backward compatibility with existing structure
            data={
                "models": ["seed-detector-rcnn-1", "swin-27-spp", "swin-15e-spp"],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "Use a Swin transformer to classify the seeds",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline)
    _get_logger().info("Pipeline added")

    async with async_session.begin() as session:
        # Create pipeline
        from datetime import date

        pipeline = Pipeline(
            id=uuid.UUID("41852dde-beed-44bc-bd94-f36e3bd783b8"),
            name="15 spp RCNN SWIN",
            active=True,
            # Use new normalized columns
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="Use a Swin transformer to classify the seeds",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=True,
            # Keep data field for backward compatibility with existing structure
            data={
                "models": ["seed-detector-rcnn-1", "swin-15e-spp"],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "Use a Swin transformer to classify the seeds",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline)
    _get_logger().info("Pipeline added")

    async with async_session.begin() as session:
        # Create pipeline
        from datetime import date

        pipeline = Pipeline(
            id=uuid.UUID("3f2e39a0-d5db-44cc-a391-f4603333f721"),
            name="27 spp RCNN SWIN",
            active=True,
            # Use new normalized columns
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="Use a Swin transformer to classify the seeds",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=True,
            # Keep data field for backward compatibility with existing structure
            data={
                "models": ["seed-detector-rcnn-1", "swin-27-spp"],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "Use a Swin transformer to classify the seeds",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline)
    _get_logger().info("Pipeline added")

    # Local test pipelines using 127.0.0.1 endpoints
    async with async_session.begin() as session:
        from datetime import date

        pipeline_local_27spp = Pipeline(
            id=uuid.UUID("d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f4a"),
            name="27 spp RCNN SWIN (Local)",
            active=True,
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="Local test pipeline - 27spp with detector and two classifiers",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=False,
            data={
                "models": [
                    "seed-detector-rcnn-1-local",
                    "swin-27-spp-local",
                    "swin-15e-spp-local",
                ],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "Local test pipeline - 27spp",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline_local_27spp)
    _get_logger().info("Local test pipeline added (27spp)")

    async with async_session.begin() as session:
        from datetime import date

        pipeline_local_15spp = Pipeline(
            id=uuid.UUID("e5f6a7b8-c9d0-4e5f-8a7b-9c0d1e2f3a4b"),
            name="15 spp RCNN SWIN (Local)",
            active=True,
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="Local test pipeline - 15spp with detector and classifier",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=False,
            data={
                "models": ["seed-detector-rcnn-1-local", "swin-15e-spp-local"],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "Local test pipeline - 15spp",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline_local_15spp)
    _get_logger().info("Local test pipeline added (15spp)")

    # CI versions of models for testing (deployment_platform='ci', container names with unique ports)
    async with async_session.begin() as session:
        swin_15_model_ci = Model(
            id=uuid.UUID("a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c5d"),
            deployment_platform="ci",
            name="swin-15e-spp-ci",
            endpoint_name="swin-15-spp-ci-endpoint",
            task_id=2,
            date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
            api_url="http://nachet-15spp-classifier:5001/score",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="15spp-e CI test endpoint",
            active=True,
        )

        swin_27_model_ci = Model(
            id=uuid.UUID("b2c3d4e5-f6a7-4b5c-8d7e-9f0a1b2c3d5e"),
            deployment_platform="ci",
            name="swin-27-spp-ci",
            endpoint_name="swin-27-spp-ci-endpoint",
            task_id=2,
            date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
            api_url="http://nachet-27spp-classifier:5002/predictions/27spp_120250130",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="27spp CI test endpoint",
            active=True,
        )

        seed_detector_model_ci = Model(
            id=uuid.UUID("c3d4e5f6-a7b8-4c5d-8e7f-9a0b1c2d3e5f"),
            deployment_platform="ci",
            name="seed-detector-rcnn-1-ci",
            endpoint_name="seed-detector-ci",
            task_id=1,
            date_model_training=datetime(2024, 11, 13, 7, 40, 25, 867369),
            api_url="http://nachet-detector:5003/score",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="CI test detector endpoint",
            active=True,
        )

        session.add_all([swin_15_model_ci, swin_27_model_ci, seed_detector_model_ci])
    _get_logger().info("Models added (CI test models)")

    # CI test pipelines using container names with unique ports
    async with async_session.begin() as session:
        from datetime import date

        pipeline_ci_27spp = Pipeline(
            id=uuid.UUID("d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f5a"),
            name="27 spp RCNN SWIN (CI)",
            active=True,
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="CI test pipeline - 27spp with detector and two classifiers",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=False,
            data={
                "models": [
                    "seed-detector-rcnn-1-ci",
                    "swin-27-spp-ci",
                    "swin-15e-spp-ci",
                ],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "CI test pipeline - 27spp",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline_ci_27spp)
    _get_logger().info("CI test pipeline added (27spp)")

    async with async_session.begin() as session:
        from datetime import date

        pipeline_ci_15spp = Pipeline(
            id=uuid.UUID("e5f6a7b8-c9d0-4e5f-8a7b-9c0d1e2f3a5b"),
            name="15 spp RCNN SWIN (CI)",
            active=True,
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="CI test pipeline - 15spp with detector and classifier",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=False,
            data={
                "models": ["seed-detector-rcnn-1-ci", "swin-15e-spp-ci"],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "CI test pipeline - 15spp",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline_ci_15spp)
    _get_logger().info("CI test pipeline added (15spp)")

    async with async_session.begin() as session:
        from datetime import date

        pipeline_local_27spp_single = Pipeline(
            id=uuid.UUID("f6a7b8c9-d0e1-4f5a-8b7c-9d0e1f2a3b4c"),
            name="27 spp RCNN SWIN Single (Local)",
            active=True,
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="Local test pipeline - 27spp with detector only",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=False,
            data={
                "models": ["seed-detector-rcnn-1-local", "swin-27-spp-local"],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "Local test pipeline - 27spp single",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline_local_27spp_single)
    _get_logger().info("Local test pipeline added (27spp single)")

    # Add pipeline default
    async with async_session.begin() as session:
        pipeline_default = PipelineDefault(
            id=1,
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            active=True,
        )
        session.add(pipeline_default)
    _get_logger().info("Pipeline default added")

    async with async_session.begin() as session:
        # Create pipeline-model relationships
        pipeline_model_1 = PipelineModel(
            id=uuid.UUID("0704a8a6-7853-4530-a49a-d98a884a3f71"),
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            model_id=uuid.UUID("52fd7ca2-8101-4541-ae49-d6d92ac69196"),
            step=1,  # Detection model - first step
            request_function="rcnn_seed_detector",
            active=True,
        )

        pipeline_model_2 = PipelineModel(
            id=uuid.UUID("3dad6eb9-56c6-4bc1-b8ab-c683f186b874"),
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            model_id=uuid.UUID("e83ee51e-830e-403a-a48f-d216ae91abb9"),
            step=2,  # Classification model - second step
            request_function="ensemble_a",
            active=True,
        )

        pipeline_model_3 = PipelineModel(
            id=uuid.UUID("b2d0f715-7d64-48ed-8f5f-b3ce338918c4"),
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            model_id=uuid.UUID("ecef8395-e6d5-47a3-8f3d-8424b4dd3816"),
            step=3,  # Classification model - third step
            request_function="ensemble_b",
            active=True,
        )

        pipeline_model_4 = PipelineModel(
            id=uuid.UUID("e6d6c6fb-ba63-476b-9ced-e591e5bcccf4"),
            pipeline_id=uuid.UUID("41852dde-beed-44bc-bd94-f36e3bd783b8"),
            model_id=uuid.UUID("52fd7ca2-8101-4541-ae49-d6d92ac69196"),
            step=1,
            request_function="rcnn_seed_detector",
            active=True,
        )

        pipeline_model_5 = PipelineModel(
            id=uuid.UUID("20597e09-50b5-4191-97c1-24b8aeb05260"),
            pipeline_id=uuid.UUID("41852dde-beed-44bc-bd94-f36e3bd783b8"),
            model_id=uuid.UUID("ecef8395-e6d5-47a3-8f3d-8424b4dd3816"),
            step=2,
            request_function="swin_classifier",
            active=True,
        )

        pipeline_model_6 = PipelineModel(
            id=uuid.UUID("a487e3dd-a502-4c99-9998-0db91d36e98a"),
            pipeline_id=uuid.UUID("3f2e39a0-d5db-44cc-a391-f4603333f721"),
            model_id=uuid.UUID("52fd7ca2-8101-4541-ae49-d6d92ac69196"),
            step=1,
            request_function="rcnn_seed_detector",
            active=True,
        )

        pipeline_model_7 = PipelineModel(
            id=uuid.UUID("14852c5d-7751-4112-92cc-f199d50a1e39"),
            pipeline_id=uuid.UUID("3f2e39a0-d5db-44cc-a391-f4603333f721"),
            model_id=uuid.UUID("e83ee51e-830e-403a-a48f-d216ae91abb9"),
            step=2,
            request_function="swin_classifier",
            active=True,
        )

        # Local pipeline models (27spp with 3 steps)
        pipeline_model_local_1 = PipelineModel(
            id=uuid.UUID("a7b8c9d0-e1f2-4a5b-8c7d-9e0f1a2b3c4d"),
            pipeline_id=uuid.UUID("d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f4a"),
            model_id=uuid.UUID(
                "c3d4e5f6-a7b8-4c5d-8e7f-9a0b1c2d3e4f"
            ),  # detector-local
            step=1,
            request_function="rcnn_seed_detector",
            active=True,
        )

        pipeline_model_local_2 = PipelineModel(
            id=uuid.UUID("b8c9d0e1-f2a3-4b5c-8d7e-9f0a1b2c3d4e"),
            pipeline_id=uuid.UUID("d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f4a"),
            model_id=uuid.UUID("b2c3d4e5-f6a7-4b5c-8d7e-9f0a1b2c3d4e"),  # swin-27-local
            step=2,
            request_function="ensemble_a",
            active=True,
        )

        pipeline_model_local_3 = PipelineModel(
            id=uuid.UUID("c9d0e1f2-a3b4-4c5d-8e7f-9a0b1c2d3e4f"),
            pipeline_id=uuid.UUID("d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f4a"),
            model_id=uuid.UUID("a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c4d"),  # swin-15-local
            step=3,
            request_function="ensemble_b",
            active=True,
        )

        # Local pipeline models (15spp with 2 steps)
        pipeline_model_local_4 = PipelineModel(
            id=uuid.UUID("d0e1f2a3-b4c5-4d5e-8f7a-9b0c1d2e3f4a"),
            pipeline_id=uuid.UUID("e5f6a7b8-c9d0-4e5f-8a7b-9c0d1e2f3a4b"),
            model_id=uuid.UUID(
                "c3d4e5f6-a7b8-4c5d-8e7f-9a0b1c2d3e4f"
            ),  # detector-local
            step=1,
            request_function="rcnn_seed_detector",
            active=True,
        )

        pipeline_model_local_5 = PipelineModel(
            id=uuid.UUID("e1f2a3b4-c5d6-4e5f-8a7b-9c0d1e2f3a4b"),
            pipeline_id=uuid.UUID("e5f6a7b8-c9d0-4e5f-8a7b-9c0d1e2f3a4b"),
            model_id=uuid.UUID("a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c4d"),  # swin-15-local
            step=2,
            request_function="swin_classifier",
            active=True,
        )

        # Local pipeline models (27spp single with 2 steps)
        pipeline_model_local_6 = PipelineModel(
            id=uuid.UUID("f2a3b4c5-d6e7-4f5a-8b7c-9d0e1f2a3b4c"),
            pipeline_id=uuid.UUID("f6a7b8c9-d0e1-4f5a-8b7c-9d0e1f2a3b4c"),
            model_id=uuid.UUID(
                "c3d4e5f6-a7b8-4c5d-8e7f-9a0b1c2d3e4f"
            ),  # detector-local
            step=1,
            request_function="rcnn_seed_detector",
            active=True,
        )

        pipeline_model_local_7 = PipelineModel(
            id=uuid.UUID("a3b4c5d6-e7f8-4a5b-8c7d-9e0f1a2b3c4d"),
            pipeline_id=uuid.UUID("f6a7b8c9-d0e1-4f5a-8b7c-9d0e1f2a3b4c"),
            model_id=uuid.UUID("b2c3d4e5-f6a7-4b5c-8d7e-9f0a1b2c3d4e"),  # swin-27-local
            step=2,
            request_function="swin_classifier",
            active=True,
        )

        # CI pipeline models (27spp with 3 steps)
        pipeline_model_ci_1 = PipelineModel(
            id=uuid.UUID("a7b8c9d0-e1f2-4a5b-8c7d-9e0f1a2b3c5d"),
            pipeline_id=uuid.UUID(
                "d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f5a"
            ),  # CI 27spp pipeline
            model_id=uuid.UUID("c3d4e5f6-a7b8-4c5d-8e7f-9a0b1c2d3e5f"),  # detector-ci
            step=1,
            request_function="rcnn_seed_detector",
            active=True,
        )

        pipeline_model_ci_2 = PipelineModel(
            id=uuid.UUID("b8c9d0e1-f2a3-4b5c-8d7e-9f0a1b2c3d5e"),
            pipeline_id=uuid.UUID(
                "d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f5a"
            ),  # CI 27spp pipeline
            model_id=uuid.UUID("b2c3d4e5-f6a7-4b5c-8d7e-9f0a1b2c3d5e"),  # swin-27-ci
            step=2,
            request_function="ensemble_a",
            active=True,
        )

        pipeline_model_ci_3 = PipelineModel(
            id=uuid.UUID("c9d0e1f2-a3b4-4c5d-8e7f-9a0b1c2d3e5f"),
            pipeline_id=uuid.UUID(
                "d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f5a"
            ),  # CI 27spp pipeline
            model_id=uuid.UUID("a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c5d"),  # swin-15-ci
            step=3,
            request_function="ensemble_b",
            active=True,
        )

        # CI pipeline models (15spp with 2 steps)
        pipeline_model_ci_4 = PipelineModel(
            id=uuid.UUID("d0e1f2a3-b4c5-4d5e-8f7a-9b0c1d2e3f5a"),
            pipeline_id=uuid.UUID(
                "e5f6a7b8-c9d0-4e5f-8a7b-9c0d1e2f3a5b"
            ),  # CI 15spp pipeline
            model_id=uuid.UUID("c3d4e5f6-a7b8-4c5d-8e7f-9a0b1c2d3e5f"),  # detector-ci
            step=1,
            request_function="rcnn_seed_detector",
            active=True,
        )

        pipeline_model_ci_5 = PipelineModel(
            id=uuid.UUID("e1f2a3b4-c5d6-4e5f-8a7b-9c0d1e2f3a5b"),
            pipeline_id=uuid.UUID(
                "e5f6a7b8-c9d0-4e5f-8a7b-9c0d1e2f3a5b"
            ),  # CI 15spp pipeline
            model_id=uuid.UUID("a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c5d"),  # swin-15-ci
            step=2,
            request_function="swin_classifier",
            active=True,
        )

        session.add_all(
            [
                pipeline_model_1,
                pipeline_model_2,
                pipeline_model_3,
                pipeline_model_4,
                pipeline_model_5,
                pipeline_model_6,
                pipeline_model_7,
                pipeline_model_local_1,
                pipeline_model_local_2,
                pipeline_model_local_3,
                pipeline_model_local_4,
                pipeline_model_local_5,
                pipeline_model_local_6,
                pipeline_model_local_7,
                pipeline_model_ci_1,
                pipeline_model_ci_2,
                pipeline_model_ci_3,
                pipeline_model_ci_4,
                pipeline_model_ci_5,
            ]
        )
    _get_logger().info(
        "Pipeline models added (including local and CI test pipeline models)"
    )

    async with async_session.begin() as session:
        # Create organization first (required for foreign key references)
        # Use CFIA org ID from environment for test organization
        organization = Organization(
            id=cfia_org_id,
            name="Test Organization",
            description="Default test organization for development",
            folder_prefix="test-org",
            active=True,
        )
        session.add(organization)

        # Note: RBAC roles (admin, user, verifier) will be created by seed_rbac_constants below
        # The admin role ID will be: uuid.uuid5(cfia_org_id, "admin")

        # Add RBAC permissions

        read_permission = RbacPermission(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            name="read",
            description="Read access permission",
            active=True,
        )
        write_permission = RbacPermission(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            name="write",
            description="Write access permission",
            active=True,
        )
        admin_permission = RbacPermission(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            name="admin",
            description="Administrative access permission",
            active=True,
        )
        session.add_all([read_permission, write_permission, admin_permission])

        # Add RBAC resources

        pictures_resource = RbacResource(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            name="pictures",
            description="Picture management resource",
            active=True,
        )
        models_resource = RbacResource(
            id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            name="models",
            description="Model management resource",
            active=True,
        )
        users_resource = RbacResource(
            id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            name="users",
            description="User management resource",
            active=True,
        )
        session.add_all([pictures_resource, models_resource, users_resource])

        # Add role-permission-resource mappings
        # Admin role gets admin permission on all resources
        # Use the CFIA admin role ID from environment
        admin_pictures = RbacRolePermissionResource(
            role_id=cfia_admin_role_id,
            permission_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            resource_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            active=True,
        )
        admin_models = RbacRolePermissionResource(
            role_id=cfia_admin_role_id,
            permission_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            resource_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            active=True,
        )
        admin_users = RbacRolePermissionResource(
            role_id=cfia_admin_role_id,
            permission_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            resource_id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            active=True,
        )
        session.add_all([admin_pictures, admin_models, admin_users])

        # Seed RBAC constants (route-based permissions)
        # This will create admin, user, and verifier roles
        await seed_rbac_constants(session, cfia_org_id)
    _get_logger().info(
        "Organization, rbac roles, rbac permissions, rbac resources, and route policies added"
    )

    async with async_session.begin() as session:
        # Organization already created above

        # Create test user
        test_user = Users(
            id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
            email="test.user@inspection.gc.ca",
            date_created=datetime(2024, 10, 30, 19, 59, 56, 653932),
            date_updated=datetime(2024, 10, 30, 19, 59, 56, 653932),
            organization=cfia_org_id,
            active=True,
            registered_by=None,  # Pre-seeded test user has no registering admin
        )
        session.add(test_user)

        # Create default folder
        # Use admin role ID from environment for CFIA org
        admin_role_id = cfia_admin_role_id
        user_role_id = uuid.uuid5(cfia_org_id, "user")
        default_folder = Folder(
            id=uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
            user_id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
            org_admin_role_id=admin_role_id,
            org_user_role_id=user_role_id,
            name="default",
            folder_prefix="/test-org/test-user",
            description="Default folder for test user",
            active=True,
        )
        session.add(default_folder)

        # Update user's default folder (after folder is created)
        test_user.default_folder_id = uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")  # type: ignore[assignment]
    _get_logger().info("Test user and default folder added")

    # Add user-role mapping (assign test user to CFIA admin role)
    async with async_session.begin() as session:
        # Use admin role ID from environment for CFIA org
        user_role_mapping = RbacUserRole(
            user_id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
            role_id=cfia_admin_role_id,
            active=True,
        )
        session.add(user_role_mapping)
    _get_logger().info("User-role mapping added")

    # # Add schema version
    # async with async_session() as session:
    #     async with session.begin():
    #         schema_version = SchemaVersion(
    #             id=uuid.UUID("99999999-9999-9999-9999-999999999999"),
    #             semver="0.2.0",
    #         )
    #         session.add(schema_version)

    # # Add a sample picture
    # async with async_session() as session:
    #     async with session.begin():
    #         sample_picture = Picture(
    #             id=uuid.UUID("10101010-1010-1010-1010-101010101010"),
    #             folder_id=uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
    #             user_id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
    #             org_admin_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
    #             width=1024,
    #             height=768,
    #             sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    #             name="test_sample.jpg",
    #             blob_url_original="https://test.blob.core.windows.net/test/sample.jpg",
    #             format="JPEG",
    #             size_on_disk_original=150.5,
    #             device_model_id=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
    #             device_lens_id=uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
    #             description="Sample test picture for development",
    #         )
    #         session.add(sample_picture)

    # # Add a sample annotation
    # async with async_session() as session:
    #     async with session.begin():
    #         sample_annotation = Annotation(
    #             id=uuid.UUID("20202020-2020-2020-2020-202020202020"),
    #             user_id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
    #             org_admin_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
    #             picture_id=uuid.UUID("10101010-1010-1010-1010-101010101010"),
    #             pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
    #             raw_data={
    #                 "detection_results": [
    #                     {"bbox": [100, 100, 200, 200], "confidence": 0.95}
    #                 ],
    #                 "classification_results": [
    #                     {"class": "test_seed", "confidence": 0.89}
    #                 ],
    #             },
    #         )
    #         session.add(sample_annotation)

    # # Add a sample object (requires seed data to be available)
    # # Note: This will work after the ISTA seed data is loaded
    # async with async_session() as session:
    #     async with session.begin():
    #         sample_object = Object(
    #             id=uuid.UUID("30303030-3030-3030-3030-303030303030"),
    #             user_id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
    #             org_admin_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
    #             inference_id=uuid.UUID("20202020-2020-2020-2020-202020202020"),
    #             picture_id=uuid.UUID("10101010-1010-1010-1010-101010101010"),
    #             pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
    #             bot_y_abs=200,
    #             bot_x_abs=200,
    #             top_y_abs=100,
    #             top_x_abs=100,
    #             top_id=uuid.UUID(
    #                 "e3f7f887-4f90-4551-ba86-4463e3b495b6"
    #             ),  # "none" seed from ISTA data
    #             top_score=0.89,
    #         )
    #         session.add(sample_object)

    # async with async_session.begin() as session:
    #     # Create seed data using ORM models
    #     seeds = [
    #         Seed(
    #             id=uuid.UUID("e3f7f887-4f90-4551-ba86-4463e3b495b6"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T15:32:53.293053+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T15:32:53.297329+00:00"),
    #             name_code="none",
    #             family="none",
    #             genus="none",
    #             species="none",
    #             original_ista_2025="none",
    #         ),
    #         Seed(
    #             id=uuid.UUID("93e65ae9-7552-48eb-a05d-e3c28482da46"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T15:32:53.293053+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T15:32:53.297329+00:00"),
    #             name_code="multi",
    #             family="multi",
    #             genus="multi",
    #             species="multi",
    #             original_ista_2025="multi",
    #         ),
    #         Seed(
    #             id=uuid.UUID("93028161-e78d-490b-bc09-2d5680c27827"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.873696+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.873696+00:00"),
    #             name_code="LOLIU_BOU",
    #             family="Poaceae ",
    #             genus="Lolium",
    #             species="× hybridum",
    #             original_ista_2025="Lolium × hybridum Hausskn. [L. multiflorum Lam. × L. perenne L.] (Synonym: Lolium × boucheanum auct. non Kunth)",
    #         ),
    #         Seed(
    #             id=uuid.UUID("816f84b0-11a0-4954-8a0f-c44076cdd3f7"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ERYSI_ALL",
    #             family="Brassicaceae ",
    #             genus="Cheiranthus",
    #             species="× allionii",
    #             original_ista_2025="Cheiranthus × allionii hort. = Erysimum × marshallii (Henfr.) Bois",
    #         ),
    #         Seed(
    #             id=uuid.UUID("ee97b54d-9936-4d9f-b977-8be44b773ceb"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ERYSI_CHI",
    #             family="Brassicaceae ",
    #             genus="Cheiranthus",
    #             species="cheiri",
    #             original_ista_2025="Cheiranthus cheiri L. = Erysimum cheiri (L.) Crantz",
    #         ),
    #         Seed(
    #             id=uuid.UUID("d5ff2d9e-825d-4fe2-b6aa-ee77120339c4"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ERYSI_ALL",
    #             family="Brassicaceae ",
    #             genus="Cheiranthus",
    #             species="maritimus",
    #             original_ista_2025="Cheiranthus maritimus L. = Malcolmia maritima (L.) W. T. Aiton",
    #         ),
    #         Seed(
    #             id=uuid.UUID("1eca8ca9-60b6-4fd0-b64a-f60dd3d5c51a"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="CHENO_ALB",
    #             family="Chenopodiaceae ",
    #             genus="Chenopodium",
    #             species="album",
    #             original_ista_2025="Chenopodium album L.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("ab77460c-0b5e-4723-836c-162fa4031d77"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="CHENO_FIC",
    #             family="Chenopodiaceae ",
    #             genus="Chenopodium",
    #             species="ficifolium",
    #             original_ista_2025="Chenopodium ficifolium Sm.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("e513d618-d99b-4e7a-81e2-1f9a0737c1bb"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="CHENO_PAL",
    #             family="Chenopodiaceae ",
    #             genus="Chenopodium",
    #             species="pallidicaule",
    #             original_ista_2025="Chenopodium pallidicaule Aellen",
    #         ),
    #         Seed(
    #             id=uuid.UUID("6d0e9fd5-7ec9-4d69-af8f-542e29dcbbd2"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="CHENO_QUI",
    #             family="Chenopodiaceae ",
    #             genus="Chenopodium",
    #             species="quinoa",
    #             original_ista_2025="Chenopodium quinoa Willd.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("184f15ba-4baf-4156-9a5f-0ff8a35339d8"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="CHLRS_DIV",
    #             family="Poaceae ",
    #             genus="Chloris",
    #             species="divaricata",
    #             original_ista_2025="Chloris divaricata R. Br.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("05f3a89f-c1bb-46c5-859c-425946efd4a4"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="CHLRS_GAY",
    #             family="Poaceae ",
    #             genus="Chloris",
    #             species="gayana",
    #             original_ista_2025="Chloris gayana Kunth",
    #         ),
    #         Seed(
    #             id=uuid.UUID("9c38e311-6fd2-4e2c-bc39-5f8970d58ce3"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="CHOND_JUN",
    #             family="Asteraceae ",
    #             genus="Chondrilla",
    #             species="juncea",
    #             original_ista_2025="Chondrilla juncea L.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("39916ae7-70c5-4853-9ded-108f4132428a"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="CHORS_TEN",
    #             family="Brassicaceae ",
    #             genus="Chorispora",
    #             species="tenella",
    #             original_ista_2025="Chorispora tenella (Pall.) DC.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("f0cf0f84-60d0-4cbf-beb7-ae0a73454406"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="AVENA_STE",
    #             family="Poaceae ",
    #             genus="Avena",
    #             species="sterilis",
    #             original_ista_2025="Avena sterilis L.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("32020163-07ab-4490-b5bd-26fbe51385b1"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACACI_DEC",
    #             family="Fabaceae ",
    #             genus="Acacia",
    #             species="decurrens",
    #             original_ista_2025="Acacia decurrens Willd.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("c1df9cf1-5d89-41dd-8b8b-3bbc733a828d"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACACI_ERI",
    #             family="Fabaceae ",
    #             genus="Acacia",
    #             species="erioloba",
    #             original_ista_2025="Acacia erioloba E. Mey.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("e5dc8a9b-c536-41e2-80d3-3d3d56263ed4"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACACI_FAR",
    #             family="Fabaceae ",
    #             genus="Acacia",
    #             species="farnesiana",
    #             original_ista_2025="Acacia farnesiana (L.) Willd.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("c93032b3-a63f-4305-a567-cdce0d283f29"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACACI_MEL",
    #             family="Fabaceae ",
    #             genus="Acacia",
    #             species="melanoxylon",
    #             original_ista_2025="Acacia melanoxylon R. Br.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("810ca9c4-7fa1-49cc-af71-a7bfbaab1e63"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACACI_SEN",
    #             family="Fabaceae ",
    #             genus="Acacia",
    #             species="senegal",
    #             original_ista_2025="Acacia senegal (L.) Willd.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("37dede9a-d1a9-4d33-a5c6-0fdcb9adde63"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACNTS_AUS",
    #             family="Asteraceae ",
    #             genus="Acanthospermum",
    #             species="australe",
    #             original_ista_2025="Acanthospermum australe (Loefl.) Kuntze",
    #         ),
    #         Seed(
    #             id=uuid.UUID("d3cbcca1-ce93-4703-aa28-e94fd5a3809a"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACNTS_HIS",
    #             family="Asteraceae ",
    #             genus="Acanthospermum",
    #             species="hispidum",
    #             original_ista_2025="Acanthospermum hispidum DC.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("cd112448-a097-4107-9da4-98fe7e6a4ae2"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACERR_CAM",
    #             family="Sapindaceae ",
    #             genus="Acer",
    #             species="campestre",
    #             original_ista_2025="Acer campestre L.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("e7ef42b4-5abc-4898-a34e-5c55f8c45af7"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACERR_NEG",
    #             family="Sapindaceae ",
    #             genus="Acer",
    #             species="negundo",
    #             original_ista_2025="Acer negundo L.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("9a1387c1-76c4-40fe-88c6-fe33fabb58bb"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACERR_PAL",
    #             family="Sapindaceae ",
    #             genus="Acer",
    #             species="palmatum",
    #             original_ista_2025="Acer palmatum Thunb.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("7ddb1766-9d6f-45b6-96a2-50cb9554e537"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACERR_PLA",
    #             family="Sapindaceae ",
    #             genus="Acer",
    #             species="platanoides",
    #             original_ista_2025="Acer platanoides L.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("c8d74957-b68c-4d9e-a789-f4abd3352c51"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACERR_PSE",
    #             family="Sapindaceae ",
    #             genus="Acer",
    #             species="pseudoplatanus",
    #             original_ista_2025="Acer pseudoplatanus L.",
    #         ),
    #         Seed(
    #             id=uuid.UUID("b3b0e3b3-9d6c-491d-8e84-624309e1d979"),
    #             seed_metadata=None,
    #             active=True,
    #             date_created=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             date_updated=datetime.fromisoformat("2025-09-03T16:25:12.735882+00:00"),
    #             name_code="ACERR_RUB",
    #             family="Sapindaceae ",
    #             genus="Acer",
    #             species="rubrum",
    #             original_ista_2025="Acer rubrum L.",
    #         ),
    #     ]
    #     session.add_all(seeds)
    # _get_logger().info("Seed data added")

    _get_logger().info("Development database seeded successfully")
