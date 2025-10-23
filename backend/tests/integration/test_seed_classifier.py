"""
Tests for seed detector and classifier inference pipeline.
"""

import base64
from pathlib import Path

import pytest

from app.service.inference_api.seed_detector import (
    request_inference_from_seed_detector,
)
from app.service.inference_api.swin import request_inference_from_swin
from app.service.inference_api import ModelDispatchInfo
from app.model.inference import (
    SeedDetectorAPIResponse,
    EnhancedClassificationResult,
)

# Get the test image path
TEST_IMAGE_PATH = Path(__file__).parent.parent / "img" / "1310_1.png"


class TestRequestInferenceFromSeedDetector:
    """Test request_inference_from_seed_detector function."""

    @pytest.mark.asyncio
    async def test_request_inference_from_seed_detector_success(self):
        """Test seed detector and classifier inference pipeline."""
        # Load the test image and convert to base64
        with open(TEST_IMAGE_PATH, "rb") as img_file:
            image_bytes = base64.b64encode(img_file.read())

        # Get configuration from environment
        detector_api_endpoint = "http://localhost:12380/score"
        classifier_api_endpoint = "http://localhost:12390/score"
        api_key = "12345"
        deployment_platform = "local"

        # Skip test if endpoint is not configured
        if not detector_api_endpoint or not api_key:
            pytest.skip("Seed detector API endpoint not configured")

        # ============================================================================
        # Step 1: Seed Detection
        # ============================================================================
        # Create model configuration pointing to real seed detector
        detector_model = ModelDispatchInfo(
            content_type="application/json",
            api_key=api_key,
            deployment_platform=deployment_platform,
            name="seed_detector_model",
            endpoint=detector_api_endpoint,
            request_function="rcnn_seed_detector",
        )

        # Call the async function
        detection_result = await request_inference_from_seed_detector(detector_model, image_bytes)

        # Verify detection result structure exists
        assert detection_result is not None
        assert hasattr(detection_result, "result")
        assert hasattr(detection_result, "images")

        # Verify detection results are valid SeedDetectorAPIResponse
        # (Pydantic validates the schema during construction)
        assert isinstance(detection_result.result, SeedDetectorAPIResponse)
        assert isinstance(detection_result.result.boxes, list)
        
        # Verify cropped images match detected boxes
        assert isinstance(detection_result.images, list)
        assert len(detection_result.images) == len(detection_result.result.boxes)
        
        # Verify each cropped image is valid base64
        for i, cropped_image in enumerate(detection_result.images):
            assert isinstance(cropped_image, bytes), f"Cropped image {i} is not bytes"
            assert len(cropped_image) > 0, f"Cropped image {i} is empty"

        # ============================================================================
        # Step 2: Seed Classification (using seed detector result)
        # ============================================================================
        # Skip if no seeds were detected
        if len(detection_result.result.boxes) == 0:
            pytest.skip("No seeds detected in image")

        # Create model configuration for classifier
        classifier_model = ModelDispatchInfo(
            content_type="application/json",
            api_key=api_key,
            deployment_platform=deployment_platform,
            name="swin_classifier_model",
            endpoint=classifier_api_endpoint,
            request_function="swin_classifier",
        )

        # Call the classifier with the detection result
        classification_result = await request_inference_from_swin(classifier_model, detection_result)

        # Verify classification result structure exists
        assert classification_result is not None
        assert hasattr(classification_result, "result")

        # Verify enhanced classification results are valid
        assert isinstance(classification_result.result, EnhancedClassificationResult)
        assert isinstance(classification_result.result.boxes, list)
        assert len(classification_result.result.boxes) == len(detection_result.result.boxes)

        # Verify each enhanced box has classification data
        for i, box in enumerate(classification_result.result.boxes):
            assert hasattr(box, "box"), f"Box {i} missing bounding box"
            assert hasattr(box, "label"), f"Box {i} missing label"
            assert hasattr(box, "score"), f"Box {i} missing score"
            assert hasattr(box, "topN"), f"Box {i} missing topN predictions"
            
            # Verify label is a string
            assert isinstance(box.label, str), f"Box {i} label is not a string"
            assert len(box.label) > 0, f"Box {i} label is empty"
            
            # Verify score is normalized
            assert isinstance(box.score, (int, float)), f"Box {i} score is not numeric"
            assert 0.0 <= box.score <= 1.0, f"Box {i} score {box.score} out of range"
            
            # Verify topN predictions list exists
            assert isinstance(box.topN, list), f"Box {i} topN is not a list"
            assert len(box.topN) > 0, f"Box {i} topN is empty"
