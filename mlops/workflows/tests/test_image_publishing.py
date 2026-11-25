"""Exercise publishing shell steps without a registry or GitHub write access."""

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parents[3] / ".github/workflows"
MANIFEST = '{"schemaVersion":2}'
DIGEST = "sha256:" + hashlib.sha256(MANIFEST.encode()).hexdigest()
IMAGE = "registry.example.test/nachet-export"


def workflow(name):
    # Preserve the GitHub Actions "on" key instead of treating it as a boolean.
    return yaml.load((WORKFLOWS / name).read_text(), Loader=yaml.BaseLoader)


class ImagePublishingTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nachet-publishing-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.calls = self.root / "calls"
        fake = self.root / "fake"
        fake.write_text("""#!/bin/bash
set -eu
command_name=$(basename "$0")
printf '%s\n' "$command_name $*" >> "$CALLS"
case "$command_name" in
  gh) printf '%s\n' "$LATEST_RUN" ;;
  docker)
    if [ "$3" = inspect ]; then printf '%s' "$PUBLISHED_MANIFEST"; fi ;;
  cosign)
    if [ "${COSIGN_FAIL:-}" = "$1" ]; then exit 1; fi ;;
esac
""")
        fake.chmod(0o755)
        for command in ("gh", "docker", "cosign"):
            (self.root / command).symlink_to(fake)
        self.steps = workflow("reusable-sign-container-images.yml")["jobs"][
            "sign-images"
        ]["steps"]

    def run_step(self, name, **overrides):
        script = next(step["run"] for step in self.steps if step["name"] == name)
        for expression, value in {
            "github.sha": "build-commit",
            "github.event.number": "1103",
            "github.event.pull_request.merged": overrides.pop("merged", "false"),
            "github.event.pull_request.base.ref": "main",
        }.items():
            script = script.replace("${{ " + expression + " }}", value)
        environment = {
            **os.environ,
            "PATH": str(self.root) + os.pathsep + os.environ["PATH"],
            "CALLS": str(self.calls),
            "LATEST_RUN": "200",
            "GITHUB_RUN_ID": "200",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REPOSITORY": "ai-cfia/nachet",
            "WORKFLOW_NAME": "MLOps export build and publish",
            "IMAGE": IMAGE,
            "IMAGE_LABEL": "export runtime",
            "IMAGE_DIGEST": DIGEST,
            "RELEASE_VERSION": "0.2.2",
            "PUBLISHED_MANIFEST": MANIFEST,
            "GITHUB_HEAD_REF": "feature",
            "GITHUB_REF": "refs/heads/main",
            **overrides,
        }
        return subprocess.run(
            ["bash", "-e", "-c", script],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    def test_main_push_queue_and_preview_tag_guard(self):
        signer = workflow("reusable-sign-container-images.yml")["jobs"]["sign-images"]
        self.assertEqual(signer["concurrency"]["queue"], "max")
        for name in ("mlops-export-build.yml", "mlops-training-build.yml"):
            with self.subTest(workflow=name):
                config = workflow(name)
                self.assertEqual(config["on"]["push"]["branches"], ["main"])
                builds = [
                    step
                    for job in config["jobs"].values()
                    for step in job.get("steps", [])
                    if "docker/build-push-action@" in step.get("uses", "")
                ]
                preview = next(
                    step for step in builds if "pull_request" in step.get("if", "")
                )
                self.assertIn("!= 'main'", preview["with"]["tags"])
                for build in builds:
                    self.assertNotIn(":main", build["with"]["tags"])

    def test_digest_signing_and_legacy_callers(self):
        for event, digest, merged, expected in (
            ("push", DIGEST, "false", [IMAGE + "@" + DIGEST]),
            ("pull_request", DIGEST, "false", [IMAGE + "@" + DIGEST]),
            (
                "pull_request",
                "",
                "false",
                [
                    IMAGE + ":build-commit",
                    IMAGE + ":0.2.2",
                    IMAGE + ":1103",
                    IMAGE + ":feature",
                ],
            ),
            (
                "pull_request",
                "",
                "true",
                [IMAGE + ":build-commit", IMAGE + ":0.2.2", IMAGE + ":main"],
            ),
        ):
            with self.subTest(event=event, digest=digest, merged=merged):
                self.calls.write_text("")
                result = self.run_step(
                    "Sign and verify images",
                    GITHUB_EVENT_NAME=event,
                    IMAGE_DIGEST=digest,
                    merged=merged,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.calls.read_text().splitlines()
                self.assertEqual(
                    [
                        line.split()[-1]
                        for line in calls
                        if line.startswith("cosign sign ")
                    ],
                    expected,
                )
                self.assertEqual(
                    [
                        line.split()[-1]
                        for line in calls
                        if line.startswith("cosign verify ")
                    ],
                    expected,
                )

    def test_older_build_finishing_last_cannot_move_main_backwards(self):
        current = self.run_step("Publish signed main image")
        self.assertEqual(current.returncode, 0, current.stderr)
        previous = self.run_step("Publish signed main image", GITHUB_RUN_ID="100")
        self.assertEqual(previous.returncode, 0, previous.stderr)
        calls = self.calls.read_text().splitlines()
        promotions = [
            line for line in calls if line.startswith("docker buildx imagetools create")
        ]
        self.assertEqual(len(promotions), 1)
        self.assertIn(f"{IMAGE}:main", promotions[0].split())
        self.assertIn(f"{IMAGE}@{DIGEST}", promotions[0].split())

    def test_failed_signing_and_missing_build_digest_stop(self):
        for options in (
            {"COSIGN_FAIL": "sign"},
            {"COSIGN_FAIL": "verify"},
            {"IMAGE_DIGEST": ""},
        ):
            with self.subTest(options=options):
                result = self.run_step("Sign and verify images", **options)
                self.assertNotEqual(result.returncode, 0)

    def test_unknown_latest_run_or_wrong_published_digest_fails(self):
        for latest in ("", "null", "unknown"):
            with self.subTest(latest=latest):
                self.calls.write_text("")
                result = self.run_step("Publish signed main image", LATEST_RUN=latest)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("docker", self.calls.read_text())
        result = self.run_step(
            "Publish signed main image", PUBLISHED_MANIFEST='{"schemaVersion":1}'
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
