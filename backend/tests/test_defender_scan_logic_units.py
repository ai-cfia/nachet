"""
Unit tests for Defender scan result processing logic.

These tests check the _process_defender_scan_result helper function
which contains the core logic for handling Defender scan results.
"""

import pytest

from app.service.blob_operations import _process_defender_scan_result
from app.exceptions import (
    DefenderScanFailedError,
    DefenderScanNotScannedError,
)


class TestProcessDefenderScanResult:
    """Unit tests for _process_defender_scan_result helper function."""

    def test_clean_scan_returns_success(self):
        """Test that 'No threats found' returns success dict."""
        # Arrange
        tags = {
            "Malware scanning scan result": "No threats found",
            "Malware scanning scan time UTC": "2024-01-15T10:30:00Z",
        }

        # Act
        result = _process_defender_scan_result(
            scan_result="No threats found",
            scan_timestamp="2024-01-15T10:30:00Z",
            tags=tags,
        )

        # Assert
        assert result is not None
        assert result["status"] == "clean"
        assert result["scan_timestamp"] == "2024-01-15T10:30:00Z"
        assert result["tags"] == tags

    def test_malicious_scan_raises_error(self):
        """Test that 'Malicious' raises DefenderScanFailedError."""
        # Arrange
        tags = {
            "Malware scanning scan result": "Malicious",
            "Malware scanning scan time UTC": "2024-01-15T10:35:00Z",
        }

        # Act & Assert
        with pytest.raises(DefenderScanFailedError) as exc_info:
            _process_defender_scan_result(
                scan_result="Malicious",
                scan_timestamp="2024-01-15T10:35:00Z",
                tags=tags,
            )

        assert "Malware detected in image" in str(exc_info.value)

    def test_not_scanned_raises_error(self):
        """Test that 'Not scanned' raises DefenderScanNotScannedError."""
        # Arrange
        tags = {
            "Malware scanning scan result": "Not scanned",
            "Malware scanning scan time UTC": "2024-01-15T10:40:00Z",
        }

        # Act & Assert
        with pytest.raises(DefenderScanNotScannedError) as exc_info:
            _process_defender_scan_result(
                scan_result="Not scanned",
                scan_timestamp="2024-01-15T10:40:00Z",
                tags=tags,
            )

        assert "could not be scanned" in str(exc_info.value)

    def test_transient_sam_errors_return_none(self):
        """Test that transient SAM errors return None to continue polling."""
        # Arrange - test all transient error codes
        transient_codes = [
            "SAM259201",
            "SAM259207",
            "SAM259213",
            "SAM259215",
            "SAM259221",
        ]

        for error_code in transient_codes:
            tags = {
                "Malware scanning scan result": f"{error_code}: Error message",
                "Malware scanning scan time UTC": "2024-01-15T10:45:00Z",
            }

            # Act
            result = _process_defender_scan_result(
                scan_result=f"{error_code}: Error message",
                scan_timestamp="2024-01-15T10:45:00Z",
                tags=tags,
            )

            # Assert
            assert result is None, f"Transient error {error_code} should return None"

    def test_permanent_sam_error_raises_error(self):
        """Test that permanent SAM errors raise DefenderScanFailedError."""
        # Arrange
        tags = {
            "Malware scanning scan result": "SAM999999: Permanent error",
            "Malware scanning scan time UTC": "2024-01-15T10:50:00Z",
        }

        # Act & Assert
        with pytest.raises(DefenderScanFailedError) as exc_info:
            _process_defender_scan_result(
                scan_result="SAM999999: Permanent error",
                scan_timestamp="2024-01-15T10:50:00Z",
                tags=tags,
            )

        assert "Defender scan failed with error" in str(exc_info.value)
        assert "SAM999999" in str(exc_info.value)

    def test_unknown_result_returns_none(self):
        """Test that unknown scan results return None to continue polling."""
        # Arrange
        tags = {
            "Malware scanning scan result": "Unknown status",
            "Malware scanning scan time UTC": "2024-01-15T10:55:00Z",
        }

        # Act
        result = _process_defender_scan_result(
            scan_result="Unknown status",
            scan_timestamp="2024-01-15T10:55:00Z",
            tags=tags,
        )

        # Assert
        assert result is None


class TestNoAzureStorageConfig:
    """Unit tests for NO_AZURE_STORAGE configuration setting."""

    def test_no_azure_storage_defaults_to_false(self):
        """Test that no_azure_storage setting defaults to False."""
        from app.api.config import Settings

        settings = Settings()
        assert settings.no_azure_storage is False

    def test_no_azure_storage_can_be_enabled(self, monkeypatch):
        """Test that no_azure_storage can be set to True via env var."""
        from app.api.config import Settings

        monkeypatch.setenv("NO_AZURE_STORAGE", "true")
        settings = Settings()
        assert settings.no_azure_storage is True

    def test_no_azure_storage_accepts_various_true_values(self, monkeypatch):
        """Test that various truthy values work for NO_AZURE_STORAGE."""
        from app.api.config import Settings

        # Test "True" (capitalized)
        monkeypatch.setenv("NO_AZURE_STORAGE", "True")
        settings = Settings()
        assert settings.no_azure_storage is True

        # Test "1"
        monkeypatch.setenv("NO_AZURE_STORAGE", "1")
        settings = Settings()
        assert settings.no_azure_storage is True

    def test_no_azure_storage_false_values(self, monkeypatch):
        """Test that falsy values result in False."""
        from app.api.config import Settings

        monkeypatch.setenv("NO_AZURE_STORAGE", "false")
        settings = Settings()
        assert settings.no_azure_storage is False

        monkeypatch.setenv("NO_AZURE_STORAGE", "0")
        settings = Settings()
        assert settings.no_azure_storage is False
