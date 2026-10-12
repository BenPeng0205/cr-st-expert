#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from protocol_validator import load_manifest, validate_example_manifest
from golden_sample_guard import validate_golden_manifest
from repository_consistency import check_repository
from st_semantic_linter import lint_manifest
from public_asset_guard import check_public_assets


@dataclass
class GateStageResult:
    stage_id: str
    title: str
    passed: bool
    summary: str
    output_path: str
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "title": self.title,
            "passed": self.passed,
            "summary": self.summary,
            "output_path": self.output_path,
            "details": self.details,
        }


def _prepare_output(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to replace existing evidence: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _run_command(command: list[str], cwd: Path) -> tuple[int, str, str]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return completed.returncode, completed.stdout, completed.stderr


def _run_suite_stage(stage_id: str, title: str, runner: str, output_path: Path, summary_name: str) -> GateStageResult:
    _prepare_output(output_path)
    code, stdout_text, stderr_text = _run_command(
        [sys.executable, runner, "--output-root", str(output_path)],
        SKILL_DIR,
    )

    details: list[str] = []
    if stdout_text.strip():
        details.append(stdout_text.strip())
    if stderr_text.strip():
        details.append(stderr_text.strip())
    if code != 0:
        return GateStageResult(stage_id, title, False, f"command failed with exit code {code}", str(output_path), details)

    summary_path = output_path / summary_name
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return GateStageResult(
        stage_id,
        title,
        bool(summary["passed"]),
        f"{summary['passed_count']}/{summary['total_count']} passed",
        str(output_path),
        details,
    )


def _run_example_stage(stage_id: str, title: str, output_path: Path) -> GateStageResult:
    _prepare_output(output_path)
    manifest = load_manifest(SKILL_DIR / "examples" / "example_manifest.json")
    result = validate_example_manifest(SKILL_DIR, manifest)
    details = result.issues if result.issues else ["all example files passed protocol validation"]
    (output_path / "example_validation.json").write_text(
        json.dumps({"passed": result.passed, "issues": result.issues}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = "example manifest passed" if result.passed else "example manifest failed"
    return GateStageResult(stage_id, title, result.passed, summary, str(output_path), details)


def _run_golden_guard_stage(stage_id: str, title: str, output_path: Path) -> GateStageResult:
    _prepare_output(output_path)
    manifest = load_manifest(SKILL_DIR / "examples" / "example_manifest.json")
    result = validate_golden_manifest(SKILL_DIR, manifest)
    details = result.issues if result.issues else ["golden sample guard passed"]
    (output_path / "golden_sample_guard.json").write_text(
        json.dumps({"passed": result.passed, "issues": result.issues}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = "golden sample guard passed" if result.passed else "golden sample guard failed"
    return GateStageResult(stage_id, title, result.passed, summary, str(output_path), details)


def _run_semantic_lint_stage(stage_id: str, title: str, output_path: Path) -> GateStageResult:
    _prepare_output(output_path)
    manifest = load_manifest(SKILL_DIR / "examples" / "example_manifest.json")
    result = lint_manifest(SKILL_DIR, manifest)
    details = result.issues if result.issues else ["semantic linter passed"]
    (output_path / "semantic_lint.json").write_text(
        json.dumps({"passed": result.passed, "issues": result.issues}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = "semantic linter passed" if result.passed else "semantic linter failed"
    return GateStageResult(stage_id, title, result.passed, summary, str(output_path), details)


def _run_unit_test_stage(stage_id: str, title: str, output_path: Path) -> GateStageResult:
    _prepare_output(output_path)
    code, stdout_text, stderr_text = _run_command(
        [sys.executable, "-m", "unittest", "discover", "-s", "test", "-p", "test_*.py"],
        SKILL_DIR,
    )
    (output_path / "unittest_stdout.txt").write_text(stdout_text, encoding="utf-8")
    (output_path / "unittest_stderr.txt").write_text(stderr_text, encoding="utf-8")
    details = [stdout_text.strip()] if stdout_text.strip() else []
    if stderr_text.strip():
        details.append(stderr_text.strip())
    return GateStageResult(stage_id, title, code == 0, "unittest passed" if code == 0 else "unittest failed", str(output_path), details)


def _run_repository_consistency_stage(stage_id: str, title: str, output_path: Path) -> GateStageResult:
    _prepare_output(output_path)
    result = check_repository(SKILL_DIR)
    details = result.issues if result.issues else ["repository consistency passed"]
    (output_path / "repository_consistency.json").write_text(
        json.dumps({"passed": result.passed, "issues": result.issues}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = "repository consistency passed" if result.passed else "repository consistency failed"
    return GateStageResult(stage_id, title, result.passed, summary, str(output_path), details)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cr-st-expert delivery gate")
    parser.add_argument("--output-root", default="output/reports/factory-gate", help="Output directory")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = SKILL_DIR / output_root
    if output_root.exists():
        parser.error("Output root exists; use a new evidence directory.")
    output_root.mkdir(parents=True, exist_ok=True)

    results = [
        _run_suite_stage("DG01", "Regression Suite", "evals/run_regression.py", output_root / "regression", "regression_summary.json"),
        _run_suite_stage(
            "DG02",
            "Customer Acceptance",
            "evals/run_customer_acceptance.py",
            output_root / "customer_acceptance",
            "customer_acceptance_summary.json",
        ),
        _run_example_stage("DG03", "Golden Example Validation", output_root / "examples"),
        _run_golden_guard_stage("DG04", "Golden Sample Guard", output_root / "golden_guard"),
        _run_semantic_lint_stage("DG05", "ST Semantic Lint", output_root / "semantic_lint"),
        _run_repository_consistency_stage("DG06", "Repository Consistency", output_root / "repository_consistency"),
        _run_unit_test_stage("DG07", "Local Unit Tests", output_root / "unit_tests"),
    ]
    public_result = check_public_assets(SKILL_DIR)
    public_path = output_root / "public_assets.json"
    public_path.write_text(json.dumps({"passed": public_result.passed, "issues": public_result.issues}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    results.append(GateStageResult("DG08", "Public Assets and UTF-8", public_result.passed, "public assets passed" if public_result.passed else "public assets failed", str(public_path), public_result.issues))

    passed_count = sum(1 for item in results if item.passed)
    summary = {
        "gate_name": "codesys_st_expert_delivery_gate_v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "passed": passed_count == len(results),
        "passed_count": passed_count,
        "total_count": len(results),
        "results": [item.to_dict() for item in results],
    }

    summary_path = output_root / "delivery_gate_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Delivery gate: {passed_count}/{len(results)} passed")
    print(f"Summary file: {summary_path}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
