import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "checkpoints.py"


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
        optional_output = self.root / "optional-checkpoint-options"

        result = subprocess.run(
            self.command(
                "list", "--output", str(output),
                "--optional-output", str(optional_output),
            ),
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            output.read_text(encoding="utf-8"),
            '{"enum": ["checkpoint-3", "checkpoint-20"]}\n',
        )
        self.assertEqual(
            json.loads(optional_output.read_text()),
            {"enum": ["none", "checkpoint-3", "checkpoint-20"]},
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
        self.assertEqual(json.loads(output.read_text()), ["checkpoint-20"])

    def test_review_accepts_one_to_three_distinct_checkpoints(self) -> None:
        self.write_complete_checkpoint(self.trainer_output / "checkpoint-30")
        names = ["checkpoint-3", "checkpoint-20", "checkpoint-30"]
        for count in (1, 2, 3):
            with self.subTest(count=count):
                output = self.root / f"selection-{count}"
                result = subprocess.run(
                    self.command(
                        "validate-selection",
                        "--checkpoint-options", json.dumps({"enum": names}),
                        "--selected-checkpoint", *names[:count],
                        *(["none"] * (3 - count)),
                        "--output", str(output),
                    ),
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(output.read_text()), names[:count])

    def test_invalid_review_does_not_produce_a_selection(self) -> None:
        # Listed checkpoints must still exist when the user finishes reviewing.
        (self.trainer_output / "checkpoint-20" / "model.safetensors").unlink()
        for choices in (
            ["none", "none", "none"],
            ["checkpoint-3", "checkpoint-3", "none"],
            ["checkpoint-3", "checkpoint-999", "none"],
            ["checkpoint-3", "checkpoint-20", "none"],
        ):
            with self.subTest(choices=choices):
                output = self.root / "invalid-selection"
                result = subprocess.run(
                    self.command(
                        "validate-selection", "--checkpoint-options",
                        '{"enum":["checkpoint-3","checkpoint-20"]}',
                        "--selected-checkpoint", *choices,
                        "--output", str(output),
                    ),
                    capture_output=True, text=True, check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_untouched_optional_fields_are_omitted(self) -> None:
        names = ["checkpoint-3", "checkpoint-20"]
        optional_options = json.dumps({"enum": ["none", *names]})
        cases = (
            (["checkpoint-3", optional_options, optional_options], ["checkpoint-3"]),
            (["checkpoint-3", "checkpoint-20", optional_options], names),
            (["checkpoint-3", optional_options, "checkpoint-20"], names),
        )
        for case_number, (choices, expected) in enumerate(cases):
            with self.subTest(choices=choices):
                output = self.root / f"selection-{case_number}"
                result = subprocess.run(
                    self.command(
                        "validate-selection", "--checkpoint-options",
                        json.dumps({"enum": names}),
                        "--selected-checkpoint", *choices,
                        "--output", str(output),
                    ),
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(output.read_text()), expected)

    def test_invalid_dropdown_payloads_are_rejected(self) -> None:
        names = ["checkpoint-3", "checkpoint-20"]
        optional_options = json.dumps({"enum": ["none", *names]})
        # Required fields and altered payloads must not acquire an implicit default.
        cases = (
            (0, json.dumps({"enum": names})),
            (0, optional_options),
            (1, '{"enum":'),
            (1, json.dumps({"enum": ["none", "checkpoint-999"]})),
            (1, json.dumps({"enum": ["none", *names], "default": "none"})),
            (1, json.dumps({"enum": ["none", *reversed(names)]})),
            (2, '{"enum":'),
        )
        for case_number, (field, value) in enumerate(cases):
            with self.subTest(field=field, value=value):
                choices = ["checkpoint-3", "none", "none"]
                choices[field] = value
                output = self.root / f"invalid-selection-{case_number}"
                result = subprocess.run(
                    self.command(
                        "validate-selection", "--checkpoint-options",
                        json.dumps({"enum": names}),
                        "--selected-checkpoint", *choices,
                        "--output", str(output),
                    ),
                    capture_output=True, text=True, check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
