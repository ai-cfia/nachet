"""Evaluation retries preserve reports and reuse one MLflow child run."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mlflow import MlflowClient

from evaluation_runtime import execute


class EvaluationRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.client = MlflowClient(tracking_uri=(self.root / "mlruns").as_uri())
        experiment = self.client.create_experiment(
            "evaluation", artifact_location=(self.root / "artifacts").as_uri()
        )
        self.parent = self.client.create_run(experiment)
        self.client.set_terminated(self.parent.info.run_id)
        output = self.root / "checkpoint-9"
        report = output / "reports" / "metrics.json"
        self.args = argparse.Namespace(
            parent_run_id=self.parent.info.run_id,
            checkpoint="checkpoint-9",
            output_dir=output,
            command=[sys.executable, "-c", f"from pathlib import Path; Path({str(report)!r}).write_text('{{}}')"],
        )

    def test_publish_and_repeat_keep_one_child_and_completed_parent(self):
        state = execute(self.args, self.client)
        with patch("evaluation_runtime.subprocess.run") as run:
            repeated = execute(self.args, self.client)
        run.assert_not_called()
        self.assertEqual(state["run_id"], repeated["run_id"])
        child = self.client.get_run(state["run_id"])
        self.assertEqual(child.info.status, "FINISHED")
        self.assertEqual(child.data.tags["mlflow.parentRunId"], self.parent.info.run_id)
        self.assertEqual(self.client.get_run(self.parent.info.run_id).info.status, "FINISHED")
        self.assertEqual(
            [item.path for item in self.client.list_artifacts(state["run_id"], "evaluation")],
            ["evaluation/metrics.json"],
        )

    def test_cli_keeps_evaluator_logs_out_of_argo_json_result(self):
        # Argo reads stdout as the result; evaluator logs must stay on stderr.
        command = self.args.command.copy()
        command[-1] += '; print("evaluator progress")'
        process = subprocess.run(
            [sys.executable, "-m", "evaluation_runtime",
             "--parent-run-id", self.parent.info.run_id,
             "--checkpoint", self.args.checkpoint,
             "--output-dir", str(self.args.output_dir), "--", *command],
            env=dict(os.environ, MLFLOW_TRACKING_URI=(self.root / "mlruns").as_uri()),
            capture_output=True, text=True, check=True, timeout=60,
        )
        result = json.loads(process.stdout)
        self.assertEqual(result["checkpoint"], self.args.checkpoint)
        self.assertEqual(self.client.get_run(result["mlflow_run_id"]).info.status, "FINISHED")
        self.assertIn("evaluator progress", process.stderr)

    def test_upload_failure_retries_publication_without_inference(self):
        with patch.object(self.client, "log_artifacts", side_effect=OSError("offline")):
            with self.assertRaisesRegex(OSError, "offline"):
                execute(self.args, self.client)
        with patch("evaluation_runtime.subprocess.run") as run:
            state = execute(self.args, self.client)
        run.assert_not_called()
        self.assertTrue(state["published"])
        self.assertEqual(self.client.get_run(state["run_id"]).info.status, "FINISHED")

    def test_failed_inference_is_not_marked_complete(self):
        with patch("evaluation_runtime.subprocess.run", side_effect=subprocess.CalledProcessError(1, "evaluator")):
            with self.assertRaises(subprocess.CalledProcessError):
                execute(self.args, self.client)
        state = execute(self.args, self.client)
        self.assertTrue(state["computed"])
        self.assertTrue((self.args.output_dir / "failed-reports-1").exists())

    def test_changed_invocation_cannot_reuse_saved_reports(self):
        execute(self.args, self.client)
        self.args.command.append("different")
        with self.assertRaisesRegex(ValueError, "different invocation"):
            execute(self.args, self.client)

    def test_deleted_report_cannot_be_published_as_success(self):
        with patch.object(self.client, "log_artifacts", side_effect=OSError("offline")):
            with self.assertRaises(OSError):
                execute(self.args, self.client)
        (self.args.output_dir / "reports" / "metrics.json").unlink()
        with self.assertRaisesRegex(ValueError, "reports.*changed|reports.*missing"):
            execute(self.args, self.client)

    def test_empty_directory_is_not_a_completed_report(self):
        directory = self.args.output_dir / "reports" / "checkpoint-9"
        self.args.command = [
            sys.executable, "-c", f"from pathlib import Path; Path({str(directory)!r}).mkdir()"
        ]
        with self.assertRaisesRegex(ValueError, "without producing reports"):
            execute(self.args, self.client)

    def test_changed_report_cannot_be_published_as_original_result(self):
        with patch.object(self.client, "log_artifacts", side_effect=OSError("offline")):
            with self.assertRaises(OSError):
                execute(self.args, self.client)
        (self.args.output_dir / "reports" / "metrics.json").write_text('{"changed": true}')
        with self.assertRaisesRegex(ValueError, "reports changed"):
            execute(self.args, self.client)

    def test_retry_recovers_child_created_before_receipt_write(self):
        with patch("evaluation_runtime.save_state", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                execute(self.args, self.client)
        state = execute(self.args, self.client)
        children = self.client.search_runs(
            [self.parent.info.experiment_id],
            filter_string=f"tags.`mlflow.parentRunId` = '{self.parent.info.run_id}'",
        )
        self.assertEqual([run.info.run_id for run in children], [state["run_id"]])


if __name__ == "__main__":
    unittest.main()
