from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import sys


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from planner import evaluate_request


@dataclass
class CaseResult:
    case_id: str
    title: str
    passed: bool
    expected_status: str
    actual_status: str
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "passed": self.passed,
            "expected_status": self.expected_status,
            "actual_status": self.actual_status,
            "details": self.details,
        }


def run_suite(manifest_path: Path, output_root: Path, summary_name: str) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_root.mkdir(parents=True, exist_ok=True)

    results: list[CaseResult] = []
    for case in manifest.get("cases", []):
        result = evaluate_request(case["request"])
        details: list[str] = []
        passed = result.status == case["expected_status"]

        expected_files = case.get("expected_files") or []
        if expected_files:
            actual_files = [artifact["path"] for artifact in result.artifacts if artifact["type"] == "st_file"]
            if actual_files != expected_files:
                passed = False
                details.append(f"expected_files={expected_files}")
                details.append(f"actual_files={actual_files}")

        if result.clarifications:
            details.extend(f"clarify:{item}" for item in result.clarifications)
        if result.blocking_reasons:
            details.extend(f"block:{item}" for item in result.blocking_reasons)

        case_result = CaseResult(
            case_id=case["id"],
            title=case["title"],
            passed=passed,
            expected_status=case["expected_status"],
            actual_status=result.status,
            details=details,
        )
        results.append(case_result)

        (output_root / f"{case['id']}.json").write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    passed_count = sum(1 for item in results if item.passed)
    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "passed": passed_count == len(results),
        "passed_count": passed_count,
        "total_count": len(results),
        "results": [item.to_dict() for item in results],
    }

    (output_root / summary_name).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary
