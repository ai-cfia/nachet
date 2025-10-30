"""
Integration tests for AnnotationService - NO MOCKS.

These tests verify the complete integration of AnnotationService with:
- AuthorizedBaseCRUDService inheritance
- Role-based access control (RBAC) via RbacService
- Database operations via AnnotationDataService
- Proper relationship loading and serialization
"""

import pytest
from uuid import uuid4, UUID

from app.service.annotation import AnnotationService
from app.service.image import ImageService
from app.db.model import Folder, Pipeline
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnnotationServiceIntegrationBasic:
    """Basic integration tests for AnnotationService."""

    @pytest.mark.asyncio
    async def test_create_and_get_annotation(
        self,
        test_admin_user,  # UUID
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test creating and retrieving an annotation."""
        # Create test folder with required fields
        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test_folder",
            folder_prefix="test_",
            description="Test folder for annotations",
        )
        integration_db_session.add(test_folder)

        # Create test pipeline with required fields
        pipeline_id = uuid4()
        test_pipeline = Pipeline(
            id=pipeline_id,
            name="test_pipeline",
            data={"test": "pipeline_data"},  # Required field
        )
        integration_db_session.add(test_pipeline)
        await integration_db_session.commit()

        # Create test picture using ImageService
        picture = await ImageService.create(
            test_admin_user,
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
        raw_data = {"inference": "test_inference", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Verify annotation was created
        assert annotation is not None
        assert annotation["user_id"] == str(test_admin_user)
        assert annotation["pipeline_id"] == str(pipeline_id)
        assert annotation["raw_data"] == raw_data
        assert annotation["org_admin_role_id"] == str(test_org_admin_role)

        # Retrieve annotation by ID
        retrieved = await AnnotationService.get_by_id(
            test_admin_user, UUID(annotation["id"])
        )

        # Verify retrieved annotation
        assert retrieved is not None
        assert retrieved["id"] == annotation["id"]
        assert retrieved["raw_data"] == raw_data

        # Cleanup
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)

    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self,
        test_org_admin_role,
        test_org_user_role,
    ):
        """Test that unauthorized users cannot create annotations."""
        invalid_user_id = uuid4()
        raw_data = {"inference": "test_inference", "confidence": 0.95}

        with pytest.raises(Exception):
            await AnnotationService.create(
                invalid_user_id,
                org_admin_role_id=test_org_admin_role,
                org_user_role_id=test_org_user_role,
                picture_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                raw_data=raw_data,
            )

    @pytest.mark.asyncio
    async def test_annotation_not_found(
        self,
        test_admin_user,  # UUID
    ):
        """Test that non-existent annotations raise appropriate HTTP errors."""
        nonexistent_id = uuid4()

        # Service layer converts AnnotationNotFoundError to HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await AnnotationService.get_by_id(test_admin_user, nonexistent_id)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await AnnotationService.update(
                test_admin_user, nonexistent_id, raw_data={"test": "data"}
            )
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await AnnotationService.delete(test_admin_user, nonexistent_id)
        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnnotationServiceIntegrationUpdate:
    """Integration tests for AnnotationService.update method."""

    @pytest.mark.asyncio
    async def test_update_success_as_org_user(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test successful annotation update by organization user."""
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
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            test_admin_user,
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
        original_data = {"inference": "original", "confidence": 0.7}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=original_data,
        )

        # Update annotation with new raw_data
        updated_data = {"inference": "updated", "confidence": 0.95}
        result = await AnnotationService.update(
            test_admin_user, UUID(annotation["id"]), raw_data=updated_data
        )

        # Verify update
        assert result is not None
        assert result["id"] == annotation["id"]
        assert result["raw_data"] == updated_data
        assert result["raw_data"] != original_data

        # Cleanup
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)

    @pytest.mark.asyncio
    async def test_update_partial_fields(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test partial update of annotation fields."""
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
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            test_admin_user,
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

        # Create annotation with complex raw_data
        original_data = {
            "inference": "original",
            "confidence": 0.7,
            "boxes": [{"x": 10, "y": 10, "w": 50, "h": 50}],
        }
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=original_data,
        )

        # Update only raw_data
        new_data = {
            "inference": "updated",
            "confidence": 0.95,
            "boxes": [{"x": 20, "y": 20, "w": 60, "h": 60}],
        }
        result = await AnnotationService.update(
            test_admin_user, UUID(annotation["id"]), raw_data=new_data
        )

        # Verify only raw_data changed
        assert result["raw_data"] == new_data
        assert result["user_id"] == str(test_admin_user)
        assert result["pipeline_id"] == str(pipeline_id)

        # Cleanup
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnnotationServiceIntegrationDelete:
    """Integration tests for AnnotationService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success_as_admin(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test successful annotation deletion by organization admin."""
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
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            test_admin_user,
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

        annotation_id = UUID(annotation["id"])

        # Delete annotation
        result = await AnnotationService.delete(test_admin_user, annotation_id)

        # Verify deletion
        assert result is not None
        assert "message" in result
        assert "id" in result
        assert result["id"] == str(annotation_id)

        # Verify annotation is soft deleted (active=False)
        # get_by_id filters by active=True, so should return 404
        with pytest.raises(HTTPException) as exc_info:
            await AnnotationService.get_by_id(
                test_admin_user,
                UUID(annotation_id)
                if isinstance(annotation_id, str)
                else annotation_id,
            )
        assert exc_info.value.status_code == 404

        # Cleanup (only picture and folder since annotation is deleted)
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
        """Test annotation deletion fails for non-admin users."""
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
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            test_admin_user,
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

        # Create annotation as admin user
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        annotation_id = UUID(annotation["id"])

        # Try to delete as regular user (non-admin)
        with pytest.raises(HTTPException) as exc_info:
            await AnnotationService.delete(test_regular_user, annotation_id)
        assert exc_info.value.status_code == 403

        # Cleanup
        cleanup_test_pictures.append(annotation_id)
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnnotationServiceIntegrationGetAll:
    """Integration tests for AnnotationService.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test successful retrieval of all annotations with organization filtering."""
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
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            test_admin_user,
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

        # Create multiple annotations
        annotations = []
        for i in range(3):
            raw_data = {
                "inference": f"test_inference_{i}",
                "confidence": 0.8 + (i * 0.05),
            }
            annotation = await AnnotationService.create(
                test_admin_user,
                org_admin_role_id=test_org_admin_role,
                org_user_role_id=test_org_user_role,
                picture_id=picture["id"],
                pipeline_id=pipeline_id,
                raw_data=raw_data,
            )
            annotations.append(annotation)

        # Retrieve all annotations
        result = await AnnotationService.get_all(test_admin_user)

        # Verify results (should include all annotations from this organization)
        assert result is not None
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) >= 3  # At least our 3 annotations

        # Verify our annotations are present
        result_ids = [ann["id"] for ann in result["items"]]
        for annotation in annotations:
            assert annotation["id"] in result_ids

        # Cleanup
        for annotation in annotations:
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
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            test_admin_user,
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

        # Create 5 annotations
        annotations = []
        for i in range(5):
            raw_data = {"inference": f"test_{i}", "confidence": 0.8}
            annotation = await AnnotationService.create(
                test_admin_user,
                org_admin_role_id=test_org_admin_role,
                org_user_role_id=test_org_user_role,
                picture_id=picture["id"],
                pipeline_id=pipeline_id,
                raw_data=raw_data,
            )
            annotations.append(annotation)

        # Get first 2 annotations
        result = await AnnotationService.get_all(test_admin_user, limit=2, offset=0)
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) >= 2
        assert result["total"] >= 5  # We created 5 annotations

        # Cleanup
        for annotation in annotations:
            cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnnotationServiceIntegrationRetrieve:
    """Integration tests for AnnotationService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success_as_org_user(
        self,
        test_admin_user,
        test_org_admin_role,
        test_org_user_role,
        integration_db_session: AsyncSession,
        cleanup_test_pictures: list,
    ):
        """Test successful annotation retrieval by organization user."""
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
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            test_admin_user,
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

        # Create annotation as admin user
        raw_data = {"inference": "test", "confidence": 0.95}
        annotation = await AnnotationService.create(
            test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            picture_id=picture["id"],
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        # Retrieve as same organization user (should succeed)
        result = await AnnotationService.get_by_id(
            test_admin_user, UUID(annotation["id"])
        )

        # Verify result
        assert result is not None
        assert result["id"] == annotation["id"]
        assert result["pipeline_name"] == "test_pipeline"
        assert result["raw_data"] == raw_data

        # Cleanup
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
        """Test that get_by_id loads all required relationships."""
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
        await integration_db_session.commit()

        # Create test picture
        picture = await ImageService.create(
            test_admin_user,
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

        # Retrieve annotation
        result = await AnnotationService.get_by_id(
            test_admin_user, UUID(annotation["id"])
        )

        # Verify all relationship data is present
        assert "user_email" in result
        assert "pipeline_name" in result
        assert result["pipeline_name"] == "test_pipeline"
        assert result["user_id"] == str(test_admin_user)
        assert result["picture_id"] == picture["id"]
        assert result["org_admin_role_id"] == str(test_org_admin_role)
        assert result["org_user_role_id"] == str(test_org_user_role)

        # Cleanup
        cleanup_test_pictures.append(annotation["id"])
        cleanup_test_pictures.append(picture["id"])
        cleanup_test_pictures.append(folder_id)
