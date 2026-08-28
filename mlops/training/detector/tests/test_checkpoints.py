import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "src" / "checkpoints.py"


class CheckpointSelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.runs = self.root / "runs"
        self.trainer_output = self.runs / "training-run" / "trainer-output"
        for checkpoint in ("checkpoint-20", "checkpoint-3"):
            self.write_complete_checkpoint(self.trainer_output / checkpoint)

    @staticmethod
    def write_complete_checkpoint(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for filename in (
            "model.safetensors",
            "optimizer.pt",
            "rng_state.pth",
            "scheduler.pt",
            "trainer_state.json",
            "training_args.bin",
        ):
            (path / filename).write_text(filename, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def command(self, operation: str, *arguments: str) -> list[str]:
        return [
            sys.executable,
            str(SCRIPT),
            "--runs-root",
            str(self.runs),
            "--run-id",
            "training-run",
            operation,
            *arguments,
        ]

    def test_list_sorts_completed_checkpoints_and_skips_incomplete_output(self) -> None:
        incomplete = self.trainer_output / "checkpoint-30"
        incomplete.mkdir()
        (incomplete / "model.safetensors").write_text("weights", encoding="utf-8")
        output = self.root / "checkpoint-options"

        result = subprocess.run(
            self.command("list", "--output", str(output)),
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            output.read_text(encoding="utf-8"),
            '{"enum": ["checkpoint-3", "checkpoint-20"]}\n',
        )

    def test_unknown_selection_is_rejected(self) -> None:
        output = self.root / "selected-checkpoint"
        result = subprocess.run(
            self.command(
                "validate-selection",
                "--checkpoint-options",
                '{"enum":["checkpoint-3","checkpoint-20"]}',
                "--selected-checkpoint",
                "checkpoint-999",
                "--output",
                str(output),
            ),
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown checkpoint selection", result.stderr)
        self.assertFalse(output.exists())

    def test_selection_accepts_one_available_checkpoint(self) -> None:
        output = self.root / "selected-checkpoint"
        result = subprocess.run(
            self.command(
                "validate-selection",
                "--checkpoint-options",
                '{"enum":["checkpoint-3","checkpoint-20"]}',
                "--selected-checkpoint",
                "checkpoint-20",
                "--output",
                str(output),
            ),
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_text(encoding="utf-8"), "checkpoint-20\n")

    def test_selection_rejects_checkpoint_removed_during_review(self) -> None:
        removed_checkpoint = self.trainer_output / "checkpoint-20"
        for file in removed_checkpoint.iterdir():
            file.unlink()
        removed_checkpoint.rmdir()
        output = self.root / "selected-checkpoint"

        result = subprocess.run(
            self.command(
                "validate-selection",
                "--checkpoint-options",
                '{"enum":["checkpoint-3","checkpoint-20"]}',
                "--selected-checkpoint",
                "checkpoint-20",
                "--output",
                str(output),
            ),
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checkpoint is no longer complete", result.stderr)
        self.assertFalse(output.exists())

    def test_malformed_checkpoint_options_are_rejected(self) -> None:
        output = self.root / "selected-checkpoint"
        result = subprocess.run(
            self.command(
                "validate-selection",
                "--checkpoint-options",
                "checkpoint-3,checkpoint-20",
                "--selected-checkpoint",
                "checkpoint-20",
                "--output",
                str(output),
            ),
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checkpoint options must be valid JSON", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
