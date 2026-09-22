"""Run an evaluator and publish its reports under the training MLflow run."""

import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from mlflow import MlflowClient


def execute(args, client=None):
    client = client or MlflowClient()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    reports = output / "reports"
    state_path = output / "evaluation.json"
    identity = {
        "parent_run_id": args.parent_run_id,
        "checkpoint": args.checkpoint,
        "command": args.command,
    }

    # Reuse state only for the same checkpoint and evaluator command.
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state["identity"] != identity:
            raise ValueError("evaluation output belongs to a different invocation")
    else:
        parent = client.get_run(args.parent_run_id)
        # A lost response can leave a child run without a local state file.
        # Look it up before creating another run.
        evaluation_key = hashlib.sha256(
            json.dumps(identity, sort_keys=True).encode()
        ).hexdigest()
        children = client.search_runs(
            [parent.info.experiment_id],
            filter_string=f"tags.`nachet.evaluation` = '{evaluation_key}'",
        )
        if len(children) > 1:
            raise ValueError("multiple MLflow runs exist for this evaluation")
        if children:
            child = children[0]
        else:
            child = client.create_run(
                parent.info.experiment_id,
                tags={
                    "mlflow.parentRunId": args.parent_run_id,
                    "mlflow.runName": f"evaluate-{args.checkpoint}",
                    "nachet.evaluation": evaluation_key,
                },
            )
        state = {"identity": identity, "run_id": child.info.run_id, "computed": False}
        save_state(state_path, state)

    if state.get("published"):
        return state
    run_id = state["run_id"]
    client.update_run(run_id, status="RUNNING")
    try:
        # Reuse completed reports when only the upload needs retrying.
        if not state["computed"]:
            if reports.exists():
                # Keep failed-attempt reports separate from the next attempt.
                attempt = 1
                while (output / f"failed-reports-{attempt}").exists():
                    attempt += 1
                reports.rename(output / f"failed-reports-{attempt}")
            reports.mkdir()
            subprocess.run(args.command, check=True, stdout=sys.stderr)
            state["reports"] = report_hashes(reports)
            if not state["reports"]:
                raise ValueError("evaluator completed without producing reports")
            state["computed"] = True
            save_state(state_path, state)
        if report_hashes(reports) != state["reports"]:
            raise ValueError(
                "evaluation reports changed or are missing; use a new output directory"
            )
        client.log_artifacts(run_id, str(reports), artifact_path="evaluation")
        client.set_terminated(run_id, status="FINISHED")
        state["published"] = True
        save_state(state_path, state)
        return state
    except Exception:
        # Preserve the original error if MLflow also fails during cleanup.
        with contextlib.suppress(Exception):
            client.set_terminated(run_id, status="FAILED")
        raise


def report_hashes(directory: Path) -> dict[str, str]:
    # Detect reports changed or removed between inference and an upload retry.
    hashes = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            with path.open("rb") as stream:
                hashes[str(path.relative_to(directory))] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
    return hashes


def save_state(path: Path, state: dict) -> None:
    # Write the complete state file before replacing the previous one.
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-run-id", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command[:1] == ["--"]:
        args.command = args.command[1:]
    if not args.command:
        parser.error("an evaluator command is required after --")
    state = execute(args)
    # Argo reads stdout as JSON; evaluator logs go to stderr.
    print(json.dumps({"checkpoint": args.checkpoint, "mlflow_run_id": state["run_id"]}))


if __name__ == "__main__":
    main()
