"""
Tests for seed_detector.py - Image slicing and inference processing functions.
"""

import base64
from pathlib import Path

import pytest

from app.service.inference_api.seed_detector import (
    request_inference_from_seed_detector,
)
from app.service.inference_api import ModelDispatchInfo
from app.model.inference import SeedDetectorAPIResponse

# Get the test image path
TEST_IMAGE_PATH = Path(__file__).parent.parent / "img" / "1310_1.png"


class TestRequestInferenceFromSeedDetector:
    """Test request_inference_from_seed_detector function."""

    @pytest.mark.asyncio
    async def test_request_inference_from_seed_detector_success(self):
        """Test successful inference request to real seed detector API."""
        # Load the test image and convert to base64
        with open(TEST_IMAGE_PATH, "rb") as img_file:
            image_bytes = base64.b64encode(img_file.read())

        # Get configuration from environment
        api_endpoint = "http://localhost:12380/score"
        api_key = "12345"
        deployment_platform = "local"

        # Skip test if endpoint is not configured
        if not api_endpoint or not api_key:
            pytest.skip("Seed detector API endpoint not configured")

        # Create model configuration pointing to real seed detector
        model = ModelDispatchInfo(
            content_type="application/json",
            api_key=api_key,
            deployment_platform=deployment_platform,
            name="seed_detector_model",
            endpoint=api_endpoint,
        )

        # Call the async function
        result = await request_inference_from_seed_detector(model, image_bytes)

        # Verify result structure exists
        assert result is not None
        assert hasattr(result, "result")
        assert hasattr(result, "images")

        # Verify detection results are valid SeedDetectorAPIResponse
        # (Pydantic validates the schema during construction)
        assert isinstance(result.result, SeedDetectorAPIResponse)
        assert isinstance(result.result.boxes, list)
        
        # Verify cropped images match detected boxes
        assert isinstance(result.images, list)
        assert len(result.images) == len(result.result.boxes)
        
        # Verify each cropped image is valid base64
        for i, cropped_image in enumerate(result.images):
            assert isinstance(cropped_image, bytes), f"Cropped image {i} is not bytes"
            assert len(cropped_image) > 0, f"Cropped image {i} is empty"
