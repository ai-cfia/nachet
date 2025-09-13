"""
Dev database seeding script using ORM syntax.

This script contains functions to seed the development database with initial data
using SQLAlchemy ORM models instead of raw SQL.
"""

import uuid
from datetime import datetime

# from sqlalchemy.orm import sessionmaker
from app.db.utils import SessionManager

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
    RbacRole,
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


async def seed_dev_data(sessionmanager: SessionManager) -> None:
    """
    Seed the development database with initial data using ORM models.

    Args:
        async_engine: SQLAlchemy async engine (for backward compatibility)
    """
    print("Dev data compatible semver: 0.2.0")
    # Use SessionManager's factory for consistent session management
    async_session = sessionmanager.get_session_factory()

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
    print("✅ Device brand and models added")

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
    print("✅ Model tasks added")

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

        session.add_all([swin_15_model, swin_27_model, seed_detector_model])
    print("✅ Models added")

    async with async_session.begin() as session:
        # Create pipeline
        pipeline = Pipeline(
            id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            name="27 spp RCNN SWIN",
            active=True,
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
    print("✅ Pipeline added")

    # Add pipeline default
    async with async_session.begin() as session:
        pipeline_default = PipelineDefault(
            id=1,
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            active=True,
        )
        session.add(pipeline_default)
    print("✅ Pipeline default added")

    async with async_session.begin() as session:
        # Create pipeline-model relationships
        pipeline_model_1 = PipelineModel(
            id=uuid.UUID("0704a8a6-7853-4530-a49a-d98a884a3f71"),
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            model_id=uuid.UUID("52fd7ca2-8101-4541-ae49-d6d92ac69196"),
            active=True,
        )

        pipeline_model_2 = PipelineModel(
            id=uuid.UUID("3dad6eb9-56c6-4bc1-b8ab-c683f186b874"),
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            model_id=uuid.UUID("e83ee51e-830e-403a-a48f-d216ae91abb9"),
            active=True,
        )

        pipeline_model_3 = PipelineModel(
            id=uuid.UUID("b2d0f715-7d64-48ed-8f5f-b3ce338918c4"),
            pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
            model_id=uuid.UUID("ecef8395-e6d5-47a3-8f3d-8424b4dd3816"),
            active=True,
        )

        session.add_all([pipeline_model_1, pipeline_model_2, pipeline_model_3])
    print("✅ Pipeline models added")

    async with async_session.begin() as session:
        # Create organization first (required for foreign key references)
        organization = Organization(
            id=uuid.UUID("12345678-1234-1234-1234-123456789012"),
            name="Test Organization",
            description="Default test organization for development",
            active=True,
        )
        session.add(organization)

        # Create RBAC role (basic admin role)
        admin_role = RbacRole(
            id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
            organization_id=uuid.UUID("12345678-1234-1234-1234-123456789012"),
            name="Admin",
            description="Administrator role with full access",
        )
        session.add(admin_role)

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
        admin_pictures = RbacRolePermissionResource(
            role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
            permission_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            resource_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            active=True,
        )
        admin_models = RbacRolePermissionResource(
            role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
            permission_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            resource_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            active=True,
        )
        admin_users = RbacRolePermissionResource(
            role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
            permission_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            resource_id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            active=True,
        )
        session.add_all([admin_pictures, admin_models, admin_users])
    print("✅ Organization, rbac roles, rbac permissions, and rbac resources added")

    async with async_session.begin() as session:
        # Organization already created above

        # Create test user
        test_user = Users(
            id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
            email="test.user@inspection.gc.ca",
            date_created=datetime(2024, 10, 30, 19, 59, 56, 653932),
            date_updated=datetime(2024, 10, 30, 19, 59, 56, 653932),
            organization=uuid.UUID("12345678-1234-1234-1234-123456789012"),
            active=True,
        )
        session.add(test_user)

        # Create default folder
        default_folder = Folder(
            id=uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
            user_id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
            org_admin_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
            name="default",
            folder_prefix="test-org/test-user",
            description="Default folder for test user",
            active=True,
        )
        session.add(default_folder)

        # Update user's default folder (after folder is created)
        test_user.default_folder_id = uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")
    print("✅ Test user and default folder added")

    # Add user-role mapping
    async with async_session.begin() as session:
        user_role_mapping = RbacUserRole(
            user_id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
            role_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
            active=True,
        )
        session.add(user_role_mapping)
    print("✅ User-role mapping added")

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

    print("✅ Development database seeded successfully!")
