"""Check the release/smoke contract, pin propagation, and exit-handler wiring."""

import unittest
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parents[1]


class DatasetReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.release = yaml.safe_load(
            (WORKFLOWS / "dataset-release-workflow-template.yaml").read_text(),
        )["spec"]
        self.smoke = yaml.safe_load(
            (WORKFLOWS / "dataset-release-smoke-workflow-template.yaml").read_text(),
        )["spec"]

    def test_smoke_calls_the_normal_release_and_passes_its_manifest_pin(self):
        templates = {item["name"]: item for item in self.smoke["templates"]}
        steps = [group[0] for group in templates["smoke"]["steps"]]
        self.assertEqual(
            [step["name"] for step in steps], ["seed", "release", "verify"]
        )
        self.assertEqual(
            steps[1]["templateRef"],
            {
                "name": "nachet-dataset-release",
                "template": "release",
            },
        )
        parameters = {
            item["name"]: item["value"] for item in steps[1]["arguments"]["parameters"]
        }
        self.assertEqual(parameters["dataset-name"], "dataset-smoke-{{workflow.uid}}")
        self.assertEqual(parameters["dataset-version"], "v1")
        release = next(
            item for item in self.release["templates"] if item["name"] == "release"
        )
        self.assertEqual(
            set(parameters), {item["name"] for item in release["inputs"]["parameters"]}
        )
        pin = steps[2]["arguments"]["parameters"][0]
        self.assertEqual(
            pin["value"], "{{steps.release.outputs.parameters.manifest-sha256}}"
        )
        self.assertIn(
            "--expected-manifest-sha256", templates["verify"]["container"]["args"]
        )

    def test_normal_release_validates_the_exact_hash_returned_by_publication(self):
        templates = {item["name"]: item for item in self.release["templates"]}
        steps = [group[0] for group in templates["release"]["steps"]]
        self.assertEqual([step["name"] for step in steps], ["publish", "validate"])
        parameters = {
            item["name"]: item["value"] for item in steps[1]["arguments"]["parameters"]
        }
        self.assertEqual(
            parameters["manifest-sha256"],
            "{{steps.publish.outputs.parameters.manifest-sha256}}",
        )
        outputs = {
            item["name"]: item for item in templates["publish"]["outputs"]["parameters"]
        }
        self.assertEqual(
            outputs["manifest-sha256"]["valueFrom"]["path"], "/tmp/manifest-sha256"
        )
        self.assertIn(
            "--expected-manifest-sha256", templates["validate"]["container"]["args"]
        )
        # Values are shell arguments, never interpolated into the shell program.
        publish = templates["publish"]["container"]
        self.assertNotIn("{{", publish["args"][0])

    def test_cleanup_runs_on_exit_with_the_same_unique_identity_and_credentials(self):
        self.assertEqual(self.smoke["onExit"], "cleanup")
        templates = {item["name"]: item for item in self.smoke["templates"]}
        self.assertNotIn(
            "retryStrategy", templates["seed"]
        )  # Creation is not idempotent.
        self.assertEqual(templates["cleanup"]["retryStrategy"]["limit"], "2")
        for stage in ("seed", "verify", "cleanup"):
            container = templates[stage]["container"]
            self.assertEqual(
                container["command"],
                ["python", "/opt/workflows/scripts/dataset_release_smoke.py"],
            )
            self.assertIn("dataset-smoke-{{workflow.uid}}", container["args"])
            self.assertEqual(
                container["envFrom"][0]["secretRef"]["name"],
                "{{workflow.parameters.credentials-secret}}",
            )
        defaults = {
            item["name"]: item.get("value")
            for item in self.smoke["arguments"]["parameters"]
        }
        self.assertEqual(defaults["credentials-secret"], "nachet-dataset-release-smoke")

    def test_referenced_templates_have_the_required_volumes_and_nonroot_runtime(self):
        for spec in (self.release, self.smoke):
            self.assertEqual(spec["serviceAccountName"], "argo-workflow")
            self.assertTrue(spec["securityContext"]["runAsNonRoot"])
            volumes = {item["name"] for item in spec["volumes"]}
            for template in spec["templates"]:
                if "container" not in template:
                    continue
                container = template["container"]
                self.assertTrue(container["securityContext"]["readOnlyRootFilesystem"])
                self.assertLessEqual(
                    {m["name"] for m in container["volumeMounts"]}, volumes
                )


if __name__ == "__main__":
    unittest.main()
