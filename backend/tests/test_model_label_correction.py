"""
Tests for temporary model label correction shim.

TODO: Remove these tests once the model API is fixed and the shim is removed.
"""


class TestCorrectModelLabelSwin:
    """Test correct_model_label() function from swin.py"""

    def test_corrects_brassica_junsea_lowercase(self):
        """Test correction of lowercase 'brassica junsea'"""
        from app.service.inference_api.swin import correct_model_label

        result = correct_model_label("brassica junsea")
        assert result == "Brassica juncea"

    def test_corrects_brassica_junsea_mixed_case(self):
        """Test correction of mixed case 'Brassica Junsea'"""
        from app.service.inference_api.swin import correct_model_label

        result = correct_model_label("Brassica Junsea")
        assert result == "Brassica juncea"

    def test_corrects_brassica_junsea_uppercase(self):
        """Test correction of uppercase 'BRASSICA JUNSEA'"""
        from app.service.inference_api.swin import correct_model_label

        result = correct_model_label("BRASSICA JUNSEA")
        assert result == "Brassica juncea"

    def test_corrects_brassica_junsea_with_spaces(self):
        """Test correction handles exact match (case-insensitive)"""
        from app.service.inference_api.swin import correct_model_label

        result = correct_model_label("Brassica junsea")
        assert result == "Brassica juncea"

    def test_does_not_modify_correct_label(self):
        """Test that correctly spelled 'Brassica juncea' is not modified"""
        from app.service.inference_api.swin import correct_model_label

        result = correct_model_label("Brassica juncea")
        assert result == "Brassica juncea"

    def test_does_not_modify_other_labels(self):
        """Test that other labels are not modified"""
        from app.service.inference_api.swin import correct_model_label

        test_labels = [
            "Avena fatua",
            "Ambrosia artemisiifolia",
            "Triticum aestivum",
            "Unknown species",
        ]

        for label in test_labels:
            result = correct_model_label(label)
            assert result == label

    def test_does_not_modify_partial_match(self):
        """Test that partial matches are not corrected"""
        from app.service.inference_api.swin import correct_model_label

        # Should not match because it's not exactly "brassica junsea"
        result = correct_model_label("Brassica junsea variant")
        assert result == "Brassica junsea variant"

    def test_empty_string(self):
        """Test that empty string is returned unchanged"""
        from app.service.inference_api.swin import correct_model_label

        result = correct_model_label("")
        assert result == ""


class TestCorrectModelLabelTorchEnsemble:
    """Test correct_model_label() function from torch_ensemble.py"""

    def test_corrects_brassica_junsea_lowercase(self):
        """Test correction of lowercase 'brassica junsea'"""
        from app.service.inference_api.torch_ensemble import correct_model_label

        result = correct_model_label("brassica junsea")
        assert result == "Brassica juncea"

    def test_corrects_brassica_junsea_mixed_case(self):
        """Test correction of mixed case 'Brassica Junsea'"""
        from app.service.inference_api.torch_ensemble import correct_model_label

        result = correct_model_label("Brassica Junsea")
        assert result == "Brassica juncea"

    def test_corrects_brassica_junsea_uppercase(self):
        """Test correction of uppercase 'BRASSICA JUNSEA'"""
        from app.service.inference_api.torch_ensemble import correct_model_label

        result = correct_model_label("BRASSICA JUNSEA")
        assert result == "Brassica juncea"

    def test_does_not_modify_correct_label(self):
        """Test that correctly spelled 'Brassica juncea' is not modified"""
        from app.service.inference_api.torch_ensemble import correct_model_label

        result = correct_model_label("Brassica juncea")
        assert result == "Brassica juncea"

    def test_does_not_modify_other_labels(self):
        """Test that other labels are not modified"""
        from app.service.inference_api.torch_ensemble import correct_model_label

        test_labels = [
            "Avena fatua",
            "Ambrosia artemisiifolia",
            "Triticum aestivum",
            "Unknown species",
        ]

        for label in test_labels:
            result = correct_model_label(label)
            assert result == label

    def test_empty_string(self):
        """Test that empty string is returned unchanged"""
        from app.service.inference_api.torch_ensemble import correct_model_label

        result = correct_model_label("")
        assert result == ""


class TestCleanLabelIntegrationSwin:
    """Test that clean_label() in swin.py applies the correction"""

    def test_clean_label_corrects_misspelling_with_prefix(self):
        """Test that clean_label removes prefix AND corrects spelling"""
        from app.service.inference_api.swin import (
            process_swin_result,
        )
        from app.model.inference import (
            SeedDetectorAPIResponse,
            SwinClassificationAPIResponse,
            DetectionBoxAPI,
            BoundingBoxAPI,
            PredictionLabelScore,
        )

        # Create mock detection response with one box (using keyword arguments)
        # Note: Bounding box coordinates are normalized (0-1 range)
        detection_response = SeedDetectorAPIResponse(
            boxes=[
                DetectionBoxAPI(
                    box=BoundingBoxAPI(topX=0.1, topY=0.1, bottomX=0.9, bottomY=0.9),
                    label="seed",
                    score=0.95,
                )
            ]
        )

        # Create mock classification with misspelled label and numeric prefix
        classification_results = [
            SwinClassificationAPIResponse(
                [
                    PredictionLabelScore(label="0 brassica junsea", score=0.95),
                    PredictionLabelScore(label="1 Avena fatua", score=0.05),
                ]
            )
        ]

        # Process results
        result = process_swin_result(detection_response, classification_results)

        # Verify correction was applied
        assert result.boxes[0].label == "Brassica juncea"
        assert result.boxes[0].topN[0].label == "Brassica juncea"
        assert result.boxes[0].topN[1].label == "Avena fatua"

    def test_clean_label_corrects_misspelling_without_prefix(self):
        """Test that clean_label corrects spelling even without numeric prefix"""
        from app.service.inference_api.swin import (
            process_swin_result,
        )
        from app.model.inference import (
            SeedDetectorAPIResponse,
            SwinClassificationAPIResponse,
            DetectionBoxAPI,
            BoundingBoxAPI,
            PredictionLabelScore,
        )

        # Create mock detection response (using keyword arguments)
        # Note: Bounding box coordinates are normalized (0-1 range)
        detection_response = SeedDetectorAPIResponse(
            boxes=[
                DetectionBoxAPI(
                    box=BoundingBoxAPI(topX=0.1, topY=0.1, bottomX=0.9, bottomY=0.9),
                    label="seed",
                    score=0.95,
                )
            ]
        )

        # Create mock classification with misspelled label (no prefix)
        classification_results = [
            SwinClassificationAPIResponse(
                [
                    PredictionLabelScore(label="BRASSICA JUNSEA", score=0.95),
                    PredictionLabelScore(label="Avena fatua", score=0.05),
                ]
            )
        ]

        # Process results
        result = process_swin_result(detection_response, classification_results)

        # Verify correction was applied
        assert result.boxes[0].label == "Brassica juncea"
        assert result.boxes[0].topN[0].label == "Brassica juncea"
