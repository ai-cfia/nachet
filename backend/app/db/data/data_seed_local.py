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
from app.service import LogService

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


async def seed_dev_data(sessionmanager: SessionManager) -> None:
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

    # Add device brand (Tagarno), models, and lenses
    async with async_session.begin() as session:
        # Tagarno brand
        tagarno_brand = DeviceBrand(
            id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
            name="Tagarno",
            description="Tagarno microscope devices",
            active=True,
        )
        session.add(tagarno_brand)

        # Tagarno models
        tagarno_models = [
            DeviceModel(
                id=uuid.UUID("6594c207-6035-40ba-afb5-00636a620dc4"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="Prestige",
                description="Tagarno Prestige microscope model",
                active=True,
            ),
            DeviceModel(
                id=uuid.UUID("4beef959-ea62-46b1-a096-499ef103b3d4"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="T50",
                description="Tagarno T50 microscope model",
                active=True,
            ),
            DeviceModel(
                id=uuid.UUID("dceb1272-e0f2-4ad3-9d36-41062f08132c"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="Trend",
                description="Tagarno Trend microscope model",
                active=True,
            ),
            DeviceModel(
                id=uuid.UUID("ba7ec916-e712-4e72-a516-53127f4fb9ba"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="Front",
                description="Tagarno Front microscope model",
                active=True,
            ),
            DeviceModel(
                id=uuid.UUID("afb48840-f0bb-415c-af89-385dd066a01c"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="Move",
                description="Tagarno Move microscope model",
                active=True,
            ),
            DeviceModel(
                id=uuid.UUID("36d0581c-304e-424d-9d2c-81872d654cb3"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="Zap",
                description="Tagarno Zap microscope model",
                active=True,
            ),
            DeviceModel(
                id=uuid.UUID("e2a1c904-059a-4d6f-9004-95ef08938bf8"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="Zip",
                description="Tagarno Zip microscope model",
                active=True,
            ),
        ]
        session.add_all(tagarno_models)

        # Tagarno lenses
        tagarno_lenses = [
            DeviceLens(
                id=uuid.UUID("77e29a37-b151-4c3e-b9b1-43b66d2650fc"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="+3",
                description="Tagarno +3 magnification lens",
                active=True,
            ),
            DeviceLens(
                id=uuid.UUID("65c29a99-7b99-4973-bd49-141a15c0bae2"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="+4",
                description="Tagarno +4 magnification lens",
                active=True,
            ),
            DeviceLens(
                id=uuid.UUID("0ec5fdd4-080d-4b69-b7b8-cc709cce7984"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="+5",
                description="Tagarno +5 magnification lens",
                active=True,
            ),
            DeviceLens(
                id=uuid.UUID("6c210d6a-df8b-4ee9-bf7a-a03fe51810ef"),
                device_brand_id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
                name="+10",
                description="Tagarno +10 magnification lens",
                active=True,
            ),
        ]
        session.add_all(tagarno_lenses)
    _get_logger().info("Tagarno device brand, models (7), and lenses (4) added")

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

        # triton model deployments
        swin_15_model_triton = Model(
            id=uuid.UUID("039eb952-3f3c-4511-a7f8-bde914da9045"),
            deployment_platform="on-prem",
            name="swin-15spp-triton",
            endpoint_name="swin-15spp-triton-endpoint",
            task_id=2,
            date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
            # api_url="http://nachet-15spp-classifier-triton:8000/v2/models/15spp_model_120250130/infer",
            api_url="http://127.0.0.1:12330/v2/models/15spp_model_120250130/infer",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="15e-spp triton deployment",
            active=True,
        )

        swin_27_model_triton = Model(
            id=uuid.UUID("63a16dd9-3d0b-42f9-90cb-da14b9613527"),
            deployment_platform="on-prem",
            name="swin-27spp-triton",
            endpoint_name="swin-27spp-triton-endpoint",
            task_id=2,
            date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
            # api_url="http://nachet-27spp-classifier-triton:8000/v2/models/27spp_model_120250130/infer",
            api_url="http://127.0.0.1:12340/v2/models/27spp_model_120250130/infer",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="27spp triton deployment",
            active=True,
        )

        seed_detector_model_triton = Model(
            id=uuid.UUID("609e3a63-e5b5-4a41-af65-f452b7d4ca80"),
            deployment_platform="on-prem",
            name="detector-rcnn-15spp-triton",
            endpoint_name="detector-rcnn-15spp-triton-endpoint",
            task_id=1,
            date_model_training=datetime(2024, 11, 13, 7, 40, 25, 867369),
            # api_url="http://nachet-seed-detector-triton:8000/v2/models/rcnn-152-15spp/infer",
            api_url="http://127.0.0.1:12350/v2/models/rcnn-152-15spp/infer",
            api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
            created_by="Test User",
            version="0.0.1",
            description="Seed detector triton deployment",
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
                swin_15_model_triton,
                swin_27_model_triton,
                seed_detector_model_triton,
            ]
        )
    _get_logger().info("Models added (including local test models)")

    async with async_session.begin() as session:
        # Create pipeline
        from datetime import date

        pipeline = Pipeline(
            id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            name="27 spp RCNN SWIN ensemble",
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

    # triton pipelines
    async with async_session.begin() as session:
        from datetime import date

        pipeline_triton = Pipeline(
            id=uuid.UUID("ca8da2b4-0e74-4537-9e1f-bde7728b4976"),
            name="27 spp RCNN SWIN ensemble (Triton)",
            active=True,
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="Triton deployment pipeline - 27spp with detector and two classifiers",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=False,
            data={
                "models": [
                    "detector-rcnn-15spp-triton",
                    "swin-27spp-triton",
                    "swin-15spp-triton",
                ],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "Triton deployment pipeline - 27spp",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline_triton)

        pipeline_triton_15spp = Pipeline(
            id=uuid.UUID("d46bf2f6-51bd-45c9-91b5-46220ae7a5f3"),
            name="15 spp RCNN SWIN (Triton)",
            active=True,
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="Triton deployment pipeline - 15spp with detector and classifier",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=False,
            data={
                "models": ["detector-rcnn-15spp-triton", "swin-15spp-triton"],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "Triton deployment pipeline - 15spp",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline_triton_15spp)

        pipeline_triton_27spp_single = Pipeline(
            id=uuid.UUID("e9b506c9-c827-4276-ad1a-27649762ad44"),
            name="27 spp RCNN SWIN Single (Triton)",
            active=True,
            created_by="Test User",
            creation_date=date(2025, 1, 30),
            description="Triton deployment pipeline - 27spp with detector only",
            job_name="",
            version="1",
            dataset="",
            identifiable=[],
            metrics=[],
            default=False,
            data={
                "models": ["detector-rcnn-15spp-triton", "swin-27spp-triton"],
                "created_by": "Test User",
                "creation_date": "2025-01-30",
                "description": "Triton deployment pipeline - 27spp single",
                "job_name": "",
                "version": "1",
                "dataset": "",
            },
        )
        session.add(pipeline_triton_27spp_single)
    _get_logger().info("Triton deployment pipelines added")

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
        # Step 1: seed-detector-rcnn-1 (detection)
        pipeline_model_1 = PipelineModel(
            id=uuid.UUID("0704a8a6-7853-4530-a49a-d98a884a3f71"),
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            model_id=uuid.UUID("52fd7ca2-8101-4541-ae49-d6d92ac69196"),
            step=1,
            request_function="rcnn_seed_detector",
            active=True,
        )

        # Step 2: swin-27-spp (classification)
        pipeline_model_2 = PipelineModel(
            id=uuid.UUID("3dad6eb9-56c6-4bc1-b8ab-c683f186b874"),
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            model_id=uuid.UUID("e83ee51e-830e-403a-a48f-d216ae91abb9"),
            step=2,
            request_function="ensemble_a",
            active=True,
        )

        # Step 3: swin-15e-spp (classification)
        pipeline_model_3 = PipelineModel(
            id=uuid.UUID("b2d0f715-7d64-48ed-8f5f-b3ce338918c4"),
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            model_id=uuid.UUID("ecef8395-e6d5-47a3-8f3d-8424b4dd3816"),
            step=3,
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

        # triton pipeline models
        pipeline_model_triton_1 = PipelineModel(
            id=uuid.UUID("a5e48669-eff5-4f89-bdb8-4865c7659c1e"),
            pipeline_id=uuid.UUID("ca8da2b4-0e74-4537-9e1f-bde7728b4976"),
            model_id=uuid.UUID(
                "609e3a63-e5b5-4a41-af65-f452b7d4ca80"
            ),  # detector-triton
            step=1,
            request_function="triton_detector",
            active=True,
        )
        pipeline_model_triton_2 = PipelineModel(
            id=uuid.UUID("c98a4565-9157-41f6-bf22-447cc6c92721"),
            pipeline_id=uuid.UUID("ca8da2b4-0e74-4537-9e1f-bde7728b4976"),
            model_id=uuid.UUID(
                "63a16dd9-3d0b-42f9-90cb-da14b9613527"
            ),  # swin-27-triton
            step=2,
            request_function="triton_ensemble_a",
            active=True,
        )
        pipeline_model_triton_3 = PipelineModel(
            id=uuid.UUID("4cab2a4a-9ef1-4d1d-8437-4ae6d56d6b1a"),
            pipeline_id=uuid.UUID("ca8da2b4-0e74-4537-9e1f-bde7728b4976"),
            model_id=uuid.UUID(
                "039eb952-3f3c-4511-a7f8-bde914da9045"
            ),  # swin-15-triton
            step=3,
            request_function="triton_ensemble_b",
            active=True,
        )
        pipeline_model_triton_4 = PipelineModel(
            id=uuid.UUID("e002afe5-953f-4219-9cf7-68ffec9a983b"),
            pipeline_id=uuid.UUID("d46bf2f6-51bd-45c9-91b5-46220ae7a5f3"),
            model_id=uuid.UUID(
                "609e3a63-e5b5-4a41-af65-f452b7d4ca80"
            ),  # detector-triton
            step=1,
            request_function="triton_detector",
            active=True,
        )
        pipeline_model_triton_5 = PipelineModel(
            id=uuid.UUID("921e62af-82d0-4866-868f-9333897af5cd"),
            pipeline_id=uuid.UUID("d46bf2f6-51bd-45c9-91b5-46220ae7a5f3"),
            model_id=uuid.UUID(
                "039eb952-3f3c-4511-a7f8-bde914da9045"
            ),  # swin-15-triton
            step=2,
            request_function="triton_classifier",
            active=True,
        )
        pipeline_model_triton_6 = PipelineModel(
            id=uuid.UUID("8d72ec1e-8b16-4358-a939-6a671648c8e1"),
            pipeline_id=uuid.UUID("e9b506c9-c827-4276-ad1a-27649762ad44"),
            model_id=uuid.UUID(
                "609e3a63-e5b5-4a41-af65-f452b7d4ca80"
            ),  # detector-triton
            step=1,
            request_function="triton_detector",
            active=True,
        )
        pipeline_model_triton_7 = PipelineModel(
            id=uuid.UUID("13dc7be8-9a02-4408-9d13-e3176c99987b"),
            pipeline_id=uuid.UUID("e9b506c9-c827-4276-ad1a-27649762ad44"),
            model_id=uuid.UUID(
                "63a16dd9-3d0b-42f9-90cb-da14b9613527"
            ),  # swin-27-triton
            step=2,
            request_function="triton_classifier",
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
                pipeline_model_triton_1,
                pipeline_model_triton_2,
                pipeline_model_triton_3,
                pipeline_model_triton_4,
                pipeline_model_triton_5,
                pipeline_model_triton_6,
                pipeline_model_triton_7,
            ]
        )
    _get_logger().info("Pipeline models added (including local test pipeline models)")

    async with async_session.begin() as session:
        # Create organization first (required for foreign key references)
        # Use CFIA org ID from environment for test organization
        organization = Organization(
            id=cfia_org_id,
            name="Canadian Food Inspection Agency",
            description="Default test organization for development",
            folder_prefix="cfia",
            active=True,
        )
        session.add(organization)

        # Note: RBAC roles (admin, user, verifier) will be created by seed_rbac_constants below
        # The admin role ID will be: uuid.uuid5(cfia_org_id, "admin")

        # Add RBAC permissions

        read_permission = RbacPermission(
            id=uuid.UUID("7b6e7736-6fb7-4895-b6d5-c521621705b3"),
            name="read",
            description="Read access permission",
            active=True,
        )
        write_permission = RbacPermission(
            id=uuid.UUID("0e85cdaf-5577-48a0-b874-ed349d13ea1a"),
            name="write",
            description="Write access permission",
            active=True,
        )
        admin_permission = RbacPermission(
            id=uuid.UUID("3b05d100-0aa4-4ab1-8ba5-ee6d72fd3cfd"),
            name="admin",
            description="Administrative access permission",
            active=True,
        )
        session.add_all([read_permission, write_permission, admin_permission])

        # Add RBAC resources

        pictures_resource = RbacResource(
            id=uuid.UUID("5184f45f-c8ee-46df-a3c1-106401fd5c8c"),
            name="pictures",
            description="Picture management resource",
            active=True,
        )
        models_resource = RbacResource(
            id=uuid.UUID("fe0bcdf3-d9c9-4d1b-8e1f-5b8c44e4a562"),
            name="models",
            description="Model management resource",
            active=True,
        )
        users_resource = RbacResource(
            id=uuid.UUID("e5ae5211-3f24-4bd8-b078-62ff96717cf0"),
            name="users",
            description="User management resource",
            active=True,
        )
        session.add_all([pictures_resource, models_resource, users_resource])

        # Add role-permission-resource mappings
        # Admin role gets admin permission on all resources
        # Use admin role ID from environment for CFIA org
        admin_pictures = RbacRolePermissionResource(
            role_id=cfia_admin_role_id,
            permission_id=uuid.UUID("3b05d100-0aa4-4ab1-8ba5-ee6d72fd3cfd"),
            resource_id=uuid.UUID("5184f45f-c8ee-46df-a3c1-106401fd5c8c"),
            active=True,
        )
        admin_models = RbacRolePermissionResource(
            role_id=cfia_admin_role_id,
            permission_id=uuid.UUID("3b05d100-0aa4-4ab1-8ba5-ee6d72fd3cfd"),
            resource_id=uuid.UUID("fe0bcdf3-d9c9-4d1b-8e1f-5b8c44e4a562"),
            active=True,
        )
        admin_users = RbacRolePermissionResource(
            role_id=cfia_admin_role_id,
            permission_id=uuid.UUID("3b05d100-0aa4-4ab1-8ba5-ee6d72fd3cfd"),
            resource_id=uuid.UUID("e5ae5211-3f24-4bd8-b078-62ff96717cf0"),
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
            org_user_role_id=user_role_id,
            org_admin_role_id=admin_role_id,
            name="default",
            folder_prefix="/cfia/test-user",
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
    #             org_user_role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
    #             org_admin_role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
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
    #             org_user_role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
    #             org_admin_role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
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
    #             org_user_role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
    #             org_admin_role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
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

    _get_logger().info("Development database seeded successfully")
