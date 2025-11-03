"""
Tests for camelCase alias support across all Pydantic models.

Tests verify that:
- camelCase aliases work (frontend convention)
- snake_case field names also work (backend convention)
- populate_by_name=True is configured correctly
- model_dump() serialization uses aliases
"""

from uuid import uuid4
from app.model.batch_upload import BatchUploadInitRequest
from app.model.directory import CreateOrGetFolderRequest, UpdateFolderRequest
from app.model.logs import FrontendLogRequest
from app.api.test_dbos import ToyWorkflowRequest


class TestBatchUploadInitRequestAliases:
    """Test camelCase aliases for BatchUploadInitRequest."""

    def test_camelcase_aliases_work(self):
        """Frontend can send camelCase field names."""
        request = BatchUploadInitRequest(
            **{
                "folderId": str(uuid4()),
                "fileCount": 10,
            }
        )
        assert request.folder_id is not None
        assert request.file_count == 10

    def test_snake_case_field_names_also_work(self):
        """Backend can use snake_case field names."""
        folder_id = str(uuid4())
        request = BatchUploadInitRequest(
            folder_id=folder_id,
            file_count=20,
        )
        assert request.folder_id == folder_id
        assert request.file_count == 20

    def test_model_dump_uses_aliases(self):
        """Serialization to dict uses camelCase aliases by default."""
        folder_id = str(uuid4())
        request = BatchUploadInitRequest(
            folder_id=folder_id,
            file_count=5,
        )
        dumped = request.model_dump(by_alias=True)
        assert "folderId" in dumped
        assert "fileCount" in dumped
        assert dumped["folderId"] == folder_id
        assert dumped["fileCount"] == 5

    def test_model_dump_without_alias_uses_field_names(self):
        """Serialization without by_alias uses snake_case field names."""
        folder_id = str(uuid4())
        request = BatchUploadInitRequest(
            folder_id=folder_id,
            file_count=5,
        )
        dumped = request.model_dump(by_alias=False)
        assert "folder_id" in dumped
        assert "file_count" in dumped


class TestCreateOrGetFolderRequestAliases:
    """Test camelCase aliases for CreateOrGetFolderRequest."""

    def test_camelcase_aliases_work(self):
        """Frontend can send camelCase field names."""
        request = CreateOrGetFolderRequest(
            **{
                "normalizedPath": "test/path",
                "description": "Test description",
            }
        )
        assert request.normalized_path == "test/path"
        assert request.description == "Test description"

    def test_snake_case_field_names_also_work(self):
        """Backend can use snake_case field names."""
        request = CreateOrGetFolderRequest(
            normalized_path="another/path",
            description="Another description",
        )
        assert request.normalized_path == "another/path"
        assert request.description == "Another description"

    def test_description_defaults_to_empty(self):
        """Description defaults to empty string with both naming conventions."""
        request1 = CreateOrGetFolderRequest(**{"normalizedPath": "test/path"})
        assert request1.description == ""

        request2 = CreateOrGetFolderRequest(normalized_path="test/path")
        assert request2.description == ""

    def test_model_dump_uses_aliases(self):
        """Serialization uses camelCase aliases."""
        request = CreateOrGetFolderRequest(
            normalized_path="test/path",
            description="Test desc",
        )
        dumped = request.model_dump(by_alias=True)
        assert "normalizedPath" in dumped
        assert "description" in dumped
        assert dumped["normalizedPath"] == "test/path"


class TestUpdateFolderRequestAliases:
    """Test camelCase aliases for UpdateFolderRequest."""

    def test_camelcase_aliases_work(self):
        """Frontend can send camelCase field names."""
        request = UpdateFolderRequest(
            name="new-name",
            description="New description",
        )
        assert request.name == "new-name"
        assert request.description == "New description"

    def test_snake_case_field_names_also_work(self):
        """Backend can use snake_case field names."""
        request = UpdateFolderRequest(
            name="another-name",
            description="Another description",
        )
        assert request.name == "another-name"
        assert request.description == "Another description"

    def test_optional_fields_work_with_both_conventions(self):
        """Optional fields can be None with both conventions."""
        request1 = UpdateFolderRequest(name="test")
        assert request1.name == "test"
        assert request1.description is None

        request2 = UpdateFolderRequest(description="test desc")
        assert request2.name is None
        assert request2.description == "test desc"

    def test_model_dump_uses_aliases(self):
        """Serialization uses camelCase aliases."""
        request = UpdateFolderRequest(
            name="test-name",
            description="Test desc",
        )
        dumped = request.model_dump(by_alias=True, exclude_none=True)
        assert "name" in dumped
        assert "description" in dumped


class TestFrontendLogRequestAliases:
    """Test camelCase aliases for FrontendLogRequest."""

    def test_camelcase_aliases_work(self):
        """Frontend can send camelCase field names."""
        request = FrontendLogRequest(
            level="ERROR",
            **{
                "message": "Test error",
                "errorType": "NetworkError",
                "stackTrace": "at function (file.js:10)",
                "url": "https://example.com",
                "correlationId": "abc-123",
                "sessionId": "session-456",
            },
        )
        assert request.level == "ERROR"
        assert request.message == "Test error"
        assert request.error_type == "NetworkError"
        assert request.stack_trace == "at function (file.js:10)"
        assert request.url == "https://example.com"
        assert request.correlation_id == "abc-123"
        assert request.session_id == "session-456"

    def test_snake_case_field_names_also_work(self):
        """Backend can use snake_case field names."""
        request = FrontendLogRequest(
            level="WARNING",
            message="Test warning",
            error_type="ValidationError",
            stack_trace="at handler (app.js:50)",
            url="https://test.com",
            correlation_id="def-456",
            session_id="session-789",
        )
        assert request.level == "WARNING"
        assert request.message == "Test warning"
        assert request.error_type == "ValidationError"
        assert request.stack_trace == "at handler (app.js:50)"

    def test_minimal_request_with_camelcase(self):
        """Minimal request works with camelCase."""
        request = FrontendLogRequest(message="Minimal error")  # type: ignore[call-arg]
        assert request.level == "ERROR"  # Default
        assert request.message == "Minimal error"
        assert request.error_type is None

    def test_model_dump_uses_aliases(self):
        """Serialization uses camelCase aliases."""
        request = FrontendLogRequest(  # type: ignore[call-arg]
            message="Test",
            error_type="TestError",
        )
        dumped = request.model_dump(by_alias=True, exclude_none=True)
        assert "level" in dumped
        assert "message" in dumped
        assert "errorType" in dumped
        # Optional fields that are None should be excluded
        assert "stackTrace" not in dumped
        assert "url" not in dumped


class TestToyWorkflowRequestAliases:
    """Test camelCase aliases for ToyWorkflowRequest."""

    def test_camelcase_aliases_work(self):
        """Frontend can send camelCase field names."""
        request = ToyWorkflowRequest(name="Alice")
        assert request.name == "Alice"

    def test_snake_case_field_names_also_work(self):
        """Backend can use snake_case field names."""
        request = ToyWorkflowRequest(name="Bob")
        assert request.name == "Bob"

    def test_model_dump_uses_aliases(self):
        """Serialization uses camelCase aliases."""
        request = ToyWorkflowRequest(name="Charlie")
        dumped = request.model_dump(by_alias=True)
        assert "name" in dumped
        assert dumped["name"] == "Charlie"


class TestCrossModelConsistency:
    """Test that all models follow consistent alias patterns."""

    def test_all_models_have_populate_by_name(self):
        """All models should accept both camelCase and snake_case."""
        # BatchUploadInitRequest
        batch1 = BatchUploadInitRequest(**{"folderId": str(uuid4()), "fileCount": 10})
        batch2 = BatchUploadInitRequest(folder_id=str(uuid4()), file_count=10)
        assert batch1.file_count == batch2.file_count

        # CreateOrGetFolderRequest
        folder1 = CreateOrGetFolderRequest(**{"normalizedPath": "test"})
        folder2 = CreateOrGetFolderRequest(normalized_path="test")
        assert folder1.normalized_path == folder2.normalized_path

        # UpdateFolderRequest
        update1 = UpdateFolderRequest(name="test")
        update2 = UpdateFolderRequest(name="test")
        assert update1.name == update2.name

        # FrontendLogRequest
        log1 = FrontendLogRequest(message="test", **{"errorType": "Error"})  # type: ignore[call-arg]
        log2 = FrontendLogRequest(message="test", error_type="Error")  # type: ignore[call-arg]
        assert log1.error_type == log2.error_type

        # ToyWorkflowRequest
        toy1 = ToyWorkflowRequest(name="test")
        toy2 = ToyWorkflowRequest(name="test")
        assert toy1.name == toy2.name

    def test_all_models_serialize_with_camelcase(self):
        """All models should serialize to camelCase when by_alias=True."""
        # BatchUploadInitRequest
        batch = BatchUploadInitRequest(folder_id=str(uuid4()), file_count=10)
        batch_dumped = batch.model_dump(by_alias=True)
        assert "folderId" in batch_dumped
        assert "fileCount" in batch_dumped

        # CreateOrGetFolderRequest
        folder = CreateOrGetFolderRequest(normalized_path="test")
        folder_dumped = folder.model_dump(by_alias=True)
        assert "normalizedPath" in folder_dumped

        # FrontendLogRequest
        log = FrontendLogRequest(message="test", error_type="Error")  # type: ignore[call-arg]
        log_dumped = log.model_dump(by_alias=True, exclude_none=True)
        assert "errorType" in log_dumped

        # ToyWorkflowRequest
        toy = ToyWorkflowRequest(name="test")
        toy_dumped = toy.model_dump(by_alias=True)
        assert "name" in toy_dumped
