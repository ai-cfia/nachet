"""
Integration tests for ImageObjectsService - NO MOCKS.

These tests verify the complete integration of ImageObjectsService with:
- AuthorizedBaseCRUDService inheritance
- Role-based access control (RBAC) via RbacService
- Database operations via ImageObjectsDataService
- Proper relationship loading and serialization
"""

import pytest
from uuid import uuid4, UUID

from app.service.image_objects import ImageObjectsService
from app.service.image import ImageService
from app.service.annotation import AnnotationService
from app.db.model import Folder, Pipeline, Seed
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageObjectsServiceIntegrationBasic:
    """Basic integration tests for ImageObjectsService."""

    @pytest.mark.asyncio
    async def test_create_and_get_image_object(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test creating and retrieving an image object."""
        # Create test folder
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "data"},
        )
        integration_db_session.add(test_pipeline)

        # Create test seed
        seed_id = uuid4()
        test_seed = Seed(
            id=seed_id,
            name_code="TEST-SEED-001",
            family="Testaceae",
            genus="Testus",
            species="testis",
            original_ista_2025="TESTSEED",
            active=True,
        )
        integration_db_session.add(test_seed)
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_picture.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Create annotation (required for image object)
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Create image object
        image_object = await ImageObjectsService.create(
            test_admin_user,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            inference_id=annotation["id"],
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            valid=True,
            top_x_abs=10,
            top_y_abs=20,
            bot_x_abs=100,
            bot_y_abs=200,
            top_id=seed_id,
            top_score=0.95,
        )

        # Verify image object was created
        assert image_object is not None
        assert image_object["user_id"] == str(test_admin_user)
        assert image_object["org_admin_role_id"] == str(test_org_admin_role)
        assert image_object["org_user_role_id"] == str(test_org_user_role)
        assert image_object["inference_id"] == str(annotation["id"])
        assert image_object["picture_id"] == str(picture["id"])
        assert image_object["pipeline_id"] == str(pipeline_id)
        assert image_object["valid"] is True
        assert image_object["box"]["top_x"] == 10
        assert image_object["box"]["top_y"] == 20
        assert image_object["box"]["bottom_x"] == 100
        assert image_object["box"]["bottom_y"] == 200
        assert image_object["top_id"] == str(seed_id)
        assert image_object["top_score"] == 0.95

        # Retrieve image object by ID
        retrieved = await ImageObjectsService.get_by_id(
            test_admin_user, UUID(image_object["id"])
        )

        # Verify retrieved image object
        assert retrieved is not None
        assert retrieved["id"] == image_object["id"]
        assert retrieved["valid"] is True

        # Cleanup
        cleanup_test_pictures.append(image_object["id"])
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)

    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self,
        test_org_admin_role,
        test_org_user_role,
    ):
        """Test that unauthorized users cannot create image objects."""
        invalid_user_id = uuid4()

        with pytest.raises(Exception):
            await ImageObjectsService.create(
                invalid_user_id,
                user_id=invalid_user_id,
                org_admin_role_id=test_org_admin_role,
                org_user_role_id=test_org_user_role,
                inference_id=str(uuid4()),
                picture_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                valid=True,
                top_x_abs=10,
                top_y_abs=20,
                bot_x_abs=100,
                bot_y_abs=200,
                top_id=str(uuid4()),
                top_score=0.95,
            )

    @pytest.mark.asyncio
    async def test_image_object_not_found(
        self,
        test_admin_user,
    ):
        """Test that non-existent image objects raise appropriate HTTP errors."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await ImageObjectsService.get_by_id(test_admin_user, nonexistent_id)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await ImageObjectsService.update(
                test_admin_user, nonexistent_id, valid=False
            )
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await ImageObjectsService.delete(test_admin_user, nonexistent_id)
        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageObjectsServiceIntegrationUpdate:
    """Integration tests for ImageObjectsService.update method."""

    @pytest.mark.asyncio
    async def test_update_success_as_org_user(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test successful image object update by organization user."""
        # Create test folder
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "data"},
        )
        integration_db_session.add(test_pipeline)

        # Create test seed
        seed_id = uuid4()
        test_seed = Seed(
            id=seed_id,
            name_code="TEST-SEED-001",
            family="Testaceae",
            genus="Testus",
            species="testis",
            original_ista_2025="TESTSEED",
            active=True,
        )
        integration_db_session.add(test_seed)
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_picture.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Create annotation
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Create image object
        image_object = await ImageObjectsService.create(
            test_admin_user,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            inference_id=annotation["id"],
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            valid=True,
            top_x_abs=10,
            top_y_abs=20,
            bot_x_abs=100,
            bot_y_abs=200,
            top_id=seed_id,
            top_score=0.95,
        )

        # Update image object validity
        result = await ImageObjectsService.update(
            test_admin_user, UUID(image_object["id"]), valid=False
        )

        # Verify update
        assert result is not None
        assert result["id"] == image_object["id"]
        assert result["valid"] is False

        # Cleanup
        cleanup_test_pictures.append(image_object["id"])
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)

    @pytest.mark.asyncio
    async def test_update_bounding_box(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test updating bounding box coordinates."""
        # Create test folder
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "data"},
        )
        integration_db_session.add(test_pipeline)

        # Create test seed
        seed_id = uuid4()
        test_seed = Seed(
            id=seed_id,
            name_code="TEST-SEED-001",
            family="Testaceae",
            genus="Testus",
            species="testis",
            original_ista_2025="TESTSEED",
            active=True,
        )
        integration_db_session.add(test_seed)
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_picture.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Create annotation
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Create image object
        image_object = await ImageObjectsService.create(
            test_admin_user,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            inference_id=annotation["id"],
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            valid=True,
            top_x_abs=10,
            top_y_abs=20,
            bot_x_abs=100,
            bot_y_abs=200,
            top_id=seed_id,
            top_score=0.95,
        )

        # Update bounding box
        result = await ImageObjectsService.update(
            test_admin_user,
            UUID(image_object["id"]),
            top_x_abs=15,
            top_y_abs=25,
            bot_x_abs=105,
            bot_y_abs=205,
            box_update=True,
        )

        # Verify update
        assert result is not None
        assert result["box"]["top_x"] == 15
        assert result["box"]["top_y"] == 25
        assert result["box"]["bottom_x"] == 105
        assert result["box"]["bottom_y"] == 205
        assert result["box_update"] is True

        # Cleanup
        cleanup_test_pictures.append(image_object["id"])
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageObjectsServiceIntegrationDelete:
    """Integration tests for ImageObjectsService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success_as_admin(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test successful image object deletion by organization admin."""
        # Create test folder
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "data"},
        )
        integration_db_session.add(test_pipeline)

        # Create test seed
        seed_id = uuid4()
        test_seed = Seed(
            id=seed_id,
            name_code="TEST-SEED-001",
            family="Testaceae",
            genus="Testus",
            species="testis",
            original_ista_2025="TESTSEED",
            active=True,
        )
        integration_db_session.add(test_seed)
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_picture.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Create annotation
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Create image object
        image_object = await ImageObjectsService.create(
            test_admin_user,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            inference_id=annotation["id"],
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            valid=True,
            top_x_abs=10,
            top_y_abs=20,
            bot_x_abs=100,
            bot_y_abs=200,
            top_id=seed_id,
            top_score=0.95,
        )

        object_id = UUID(image_object["id"])

        # Delete image object
        result = await ImageObjectsService.delete(test_admin_user, object_id)

        # Verify deletion
        assert result is not None
        assert "message" in result
        assert "id" in result
        assert result["id"] == str(object_id)

        # Verify image object is soft deleted (active=False) - can't be retrieved
        with pytest.raises(HTTPException) as exc_info:
            await ImageObjectsService.get_by_id(test_admin_user, object_id)
        assert exc_info.value.status_code == 404

        # Cleanup (only annotation, picture, and folder since object is deleted)
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)

    @pytest.mark.asyncio
    async def test_delete_unauthorized_non_admin(
        self,
        test_regular_user,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test image object deletion fails for non-admin users."""
        # Create test folder
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "data"},
        )
        integration_db_session.add(test_pipeline)

        # Create test seed
        seed_id = uuid4()
        test_seed = Seed(
            id=seed_id,
            name_code="TEST-SEED-001",
            family="Testaceae",
            genus="Testus",
            species="testis",
            original_ista_2025="TESTSEED",
            active=True,
        )
        integration_db_session.add(test_seed)
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_picture.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Create annotation
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Create image object as admin
        image_object = await ImageObjectsService.create(
            test_admin_user,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            inference_id=annotation["id"],
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            valid=True,
            top_x_abs=10,
            top_y_abs=20,
            bot_x_abs=100,
            bot_y_abs=200,
            top_id=seed_id,
            top_score=0.95,
        )

        object_id = UUID(image_object["id"])

        # Try to delete as regular user (non-admin)
        with pytest.raises(HTTPException) as exc_info:
            await ImageObjectsService.delete(test_regular_user, object_id)

        # Verify access denied
        assert exc_info.value.status_code == 403

        # Cleanup
        cleanup_test_pictures.append(object_id)
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageObjectsServiceIntegrationGetAll:
    """Integration tests for ImageObjectsService.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test retrieving all image objects with pagination."""
        # Create test folder
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "data"},
        )
        integration_db_session.add(test_pipeline)

        # Create test seed
        seed_id = uuid4()
        test_seed = Seed(
            id=seed_id,
            name_code="TEST-SEED-001",
            family="Testaceae",
            genus="Testus",
            species="testis",
            original_ista_2025="TESTSEED",
            active=True,
        )
        integration_db_session.add(test_seed)
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_picture.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Create annotation
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Create multiple image objects
        objects = []
        for i in range(3):
            obj = await ImageObjectsService.create(
                test_admin_user,
                user_id=test_admin_user,
                org_admin_role_id=test_org_admin_role,
                org_user_role_id=test_org_user_role,
                inference_id=annotation["id"],
                picture_id=picture["id"],
                pipeline_id=pipeline_id,
                valid=True,
                top_x_abs=10 + i,
                top_y_abs=20 + i,
                bot_x_abs=100 + i,
                bot_y_abs=200 + i,
                top_id=seed_id,
                top_score=0.90 + (i * 0.01),
            )
            objects.append(obj)

        # Get all image objects
        result = await ImageObjectsService.get_all(test_admin_user, offset=0, limit=10)

        # Verify result structure
        assert "items" in result
        assert "total" in result
        assert "offset" in result
        assert "limit" in result
        assert "has_more" in result

        # Verify we got our objects (there might be more from other tests)
        assert result["total"] >= 3
        assert len(result["items"]) >= 3

        # Cleanup
        for obj in objects:
            cleanup_test_pictures.append(obj["id"])
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test get_all with pagination parameters."""
        # Create test folder
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "data"},
        )
        integration_db_session.add(test_pipeline)

        # Create test seed
        seed_id = uuid4()
        test_seed = Seed(
            id=seed_id,
            name_code="TEST-SEED-001",
            family="Testaceae",
            genus="Testus",
            species="testis",
            original_ista_2025="TESTSEED",
            active=True,
        )
        integration_db_session.add(test_seed)
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_picture.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Create annotation
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Create 5 image objects
        objects = []
        for i in range(5):
            obj = await ImageObjectsService.create(
                test_admin_user,
                user_id=test_admin_user,
                org_admin_role_id=test_org_admin_role,
                org_user_role_id=test_org_user_role,
                inference_id=annotation["id"],
                picture_id=picture["id"],
                pipeline_id=pipeline_id,
                valid=True,
                top_x_abs=10 + i,
                top_y_abs=20 + i,
                bot_x_abs=100 + i,
                bot_y_abs=200 + i,
                top_id=seed_id,
                top_score=0.90 + (i * 0.01),
            )
            objects.append(obj)

        # Test pagination: limit 2
        result = await ImageObjectsService.get_all(test_admin_user, offset=0, limit=2)

        assert result["limit"] == 2
        assert result["offset"] == 0
        assert len(result["items"]) == 2

        # Cleanup
        for obj in objects:
            cleanup_test_pictures.append(obj["id"])
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageObjectsServiceIntegrationRetrieve:
    """Integration tests for ImageObjectsService retrieve operations."""

    @pytest.mark.asyncio
    async def test_get_by_id_success_as_org_user(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test retrieving image object by ID as organization user."""
        # Create test folder
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "data"},
        )
        integration_db_session.add(test_pipeline)

        # Create test seed
        seed_id = uuid4()
        test_seed = Seed(
            id=seed_id,
            name_code="TEST-SEED-001",
            family="Testaceae",
            genus="Testus",
            species="testis",
            original_ista_2025="TESTSEED",
            active=True,
        )
        integration_db_session.add(test_seed)
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_picture.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Create annotation
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Create image object
        image_object = await ImageObjectsService.create(
            test_admin_user,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            inference_id=annotation["id"],
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            valid=True,
            top_x_abs=10,
            top_y_abs=20,
            bot_x_abs=100,
            bot_y_abs=200,
            top_id=seed_id,
            top_score=0.95,
        )

        # Retrieve as org user (same user who created it)
        retrieved = await ImageObjectsService.get_by_id(
            test_admin_user, UUID(image_object["id"])
        )

        # Verify retrieval
        assert retrieved is not None
        assert retrieved["id"] == image_object["id"]
        assert retrieved["user_id"] == str(test_admin_user)

        # Cleanup
        cleanup_test_pictures.append(image_object["id"])
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)

    @pytest.mark.asyncio
    async def test_get_by_id_includes_all_relationships(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test that get_by_id loads all entity relationships."""
        # Create test folder
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "data"},
        )
        integration_db_session.add(test_pipeline)

        # Create test seed
        seed_id = uuid4()
        test_seed = Seed(
            id=seed_id,
            name_code="TEST-SEED-001",
            family="Testaceae",
            genus="Testus",
            species="testis",
            original_ista_2025="TESTSEED",
            active=True,
        )
        integration_db_session.add(test_seed)
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_picture.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Create annotation
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Create image object
        image_object = await ImageObjectsService.create(
            test_admin_user,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            inference_id=annotation["id"],
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            valid=True,
            top_x_abs=10,
            top_y_abs=20,
            bot_x_abs=100,
            bot_y_abs=200,
            top_id=seed_id,
            top_score=0.95,
        )

        # Retrieve image object
        retrieved = await ImageObjectsService.get_by_id(
            test_admin_user, UUID(image_object["id"])
        )

        # Verify all relationships are loaded
        assert retrieved is not None
        assert "user_email" in retrieved
        assert retrieved["user_email"] is not None
        assert "pipeline_name" in retrieved
        assert retrieved["pipeline_name"] == "test_pipeline"
        assert "top_seed_name" in retrieved
        assert retrieved["top_seed_name"] == "TEST-SEED-001"

        # Cleanup
        cleanup_test_pictures.append(image_object["id"])
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)
