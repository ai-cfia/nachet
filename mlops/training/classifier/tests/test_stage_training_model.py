"""Exercise shared model staging without S3 or a GPU."""

import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from stage_training_model import stage_model

SOURCE = "s3://nachet-models/base/model/"
PREFIX = "base/model/"


class StageTrainingModelTests(unittest.TestCase):
    def setUp(self):
        workspace = self.enterContext(TemporaryDirectory())
        self.destination = Path(workspace) / "run" / "base-model"
        self.client = Mock()
        self.create_client = self.enterContext(
            patch("stage_training_model.create_s3_client", return_value=self.client)
        )

    def list_files(self, *names):
        paginator = self.client.get_paginator.return_value
        paginator.paginate.return_value = [
            {"Contents": [{"Key": PREFIX + name}]} for name in names
        ]

    def test_downloads_nested_files_and_reuses_completed_snapshot(self):
        self.list_files("", "config.json", "nested/model.safetensors")
        self.client.get_object.side_effect = [
            {"Body": BytesIO(b"config")},
            {"Body": BytesIO(b"weights")},
        ]

        stage_model(SOURCE, self.destination)
        stage_model(SOURCE.rstrip("/"), self.destination)

        self.assertEqual((self.destination / "config.json").read_bytes(), b"config")
        self.assertEqual(
            (self.destination / "nested/model.safetensors").read_bytes(), b"weights"
        )
        self.client.get_paginator.return_value.paginate.assert_called_once_with(
            Bucket="nachet-models", Prefix=PREFIX
        )
        self.create_client.assert_called_once()
        with self.assertRaises(FileExistsError):
            stage_model("s3://nachet-models/base/other", self.destination)

    def test_failed_download_can_be_retried(self):
        self.list_files("config.json", "model.safetensors")
        self.client.get_object.side_effect = [
            {"Body": BytesIO(b"config")},
            OSError("download interrupted"),
            {"Body": BytesIO(b"config")},
            {"Body": BytesIO(b"weights")},
        ]

        with self.assertRaisesRegex(OSError, "download interrupted"):
            stage_model(SOURCE, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.destination.parent.iterdir()), [])

        stage_model(SOURCE, self.destination)
        self.assertEqual(
            (self.destination / "model.safetensors").read_bytes(), b"weights"
        )

    def test_empty_prefix_or_unsafe_key_leaves_no_snapshot(self):
        for names, error in ((("",), FileNotFoundError), (("../outside",), ValueError)):
            with self.subTest(names=names):
                self.list_files(*names)
                with self.assertRaises(error):
                    stage_model(SOURCE, self.destination)
                self.assertFalse(self.destination.exists())
        self.client.get_object.assert_not_called()
