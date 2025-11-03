"""
Test field aliases in InferenceRequest Pydantic model.

Verifies that camelCase aliases from frontend are properly mapped to snake_case fields.
"""

import pytest
from uuid import uuid4
from app.model.inference import InferenceRequest


class TestInferenceRequestAliases:
    """Test cases for InferenceRequest field aliases."""

    @pytest.fixture
    def base_request_data(self):
        """Base request data with all required fields using camelCase aliases."""
        return {
            "pipelineId": "41852dde-beed-44bc-bd94-f36e3bd783b8",
            "folderName": "test.user",
            "folderId": "42ac2dba-c7eb-4cf1-89d4-18f8088457df",
            "imageDims": [1920, 1080],
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "areaRatio": 0.5,
            "colorFormat": "hex",
            "imageName": "test-image",  # Alphanumeric + hyphens only
            "imageDescription": "Test image description",
            "deviceModelId": str(uuid4()),
            "deviceLensId": str(uuid4()),
            "trayCode": "A",  # Must be A, B, C, D, or E
            "magnification": 40.0,
        }

    def test_camelcase_aliases_work(self, base_request_data):
        """Test that camelCase field names from frontend are accepted."""
        request = InferenceRequest(**base_request_data)

        # Verify internal field names use snake_case
        assert request.pipeline_id == base_request_data["pipelineId"]
        assert request.folder_name == base_request_data["folderName"]
        assert request.folder_id == base_request_data["folderId"]
        assert request.image_dims == base_request_data["imageDims"]
        assert request.area_ratio == base_request_data["areaRatio"]
        assert request.color_format == base_request_data["colorFormat"]

    def test_snake_case_field_names_also_work(self, base_request_data):
        """Test that snake_case field names (internal) are also accepted due to populate_by_name."""
        # Convert camelCase to snake_case
        snake_case_data = {
            "pipeline_id": base_request_data["pipelineId"],
            "folder_name": base_request_data["folderName"],
            "folder_id": base_request_data["folderId"],
            "image_dims": base_request_data["imageDims"],
            "image": base_request_data["image"],
            "area_ratio": base_request_data["areaRatio"],
            "color_format": base_request_data["colorFormat"],
            "image_name": base_request_data["imageName"],
            "image_description": base_request_data["imageDescription"],
            "device_model_id": base_request_data["deviceModelId"],
            "device_lens_id": base_request_data["deviceLensId"],
            "tray_code": base_request_data["trayCode"],
            "magnification": base_request_data["magnification"],
        }

        request = InferenceRequest(**snake_case_data)

        # Verify fields are populated correctly
        assert request.pipeline_id == snake_case_data["pipeline_id"]
        assert request.folder_name == snake_case_data["folder_name"]
        assert request.folder_id == snake_case_data["folder_id"]
        assert request.image_dims == snake_case_data["image_dims"]

    def test_missing_required_aliased_field(self):
        """Test that missing required aliased fields raise validation error."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            # Use dict unpacking to pass camelCase aliases
            InferenceRequest(
                **{
                    # Missing pipelineId/pipeline_id
                    "folderName": "test.user",
                    "folderId": "42ac2dba-c7eb-4cf1-89d4-18f8088457df",
                    "imageDims": [1920, 1080],
                    "image": "data:image/png;base64,test",
                    "imageName": "test",
                    "imageDescription": "test",
                    "deviceModelId": str(uuid4()),
                    "deviceLensId": str(uuid4()),
                    "trayCode": "TRAY-001",
                    "magnification": 40.0,
                }
            )

    def test_model_dump_uses_aliases_in_serialization(self, base_request_data):
        """Test that model serialization can use aliases when by_alias=True."""
        request = InferenceRequest(**base_request_data)

        # Serialize with aliases
        serialized = request.model_dump(by_alias=True)

        # Verify aliases are used in output
        assert "pipelineId" in serialized
        assert "folderName" in serialized
        assert "folderId" in serialized
        assert "imageDims" in serialized
        assert "areaRatio" in serialized
        assert "colorFormat" in serialized

        # Verify snake_case names are NOT in output when using aliases
        assert "pipeline_id" not in serialized
        assert "folder_name" not in serialized
        assert "folder_id" not in serialized

    def test_default_values_work_with_aliases(self):
        """Test that default values work correctly with aliased fields."""
        minimal_data = {
            "pipelineId": "41852dde-beed-44bc-bd94-f36e3bd783b8",
            "folderName": "test.user",
            "folderId": "42ac2dba-c7eb-4cf1-89d4-18f8088457df",
            "imageDims": [1920, 1080],
            "image": "data:image/png;base64,test",
            "imageName": "test",
            "imageDescription": "test",
            "deviceModelId": str(uuid4()),
            "deviceLensId": str(uuid4()),
            "trayCode": "B",  # Must be A, B, C, D, or E
            "magnification": 40.0,
            # Not providing areaRatio or colorFormat - should use defaults
        }

        request = InferenceRequest(**minimal_data)

        # Verify default values
        assert request.area_ratio == 0.5
        assert request.color_format == "hex"
