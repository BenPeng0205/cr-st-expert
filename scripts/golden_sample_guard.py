from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_BUNDLE_FIELDS = {
    "bundle_id",
    "description",
    "target_platform",
    "protocol",
    "verification_level",
    "promotion_evidence",
    "files",
    "coverage",
}

ALLOWED_VERIFICATION_LEVELS = {
    "protocol_gate",
    "codesys_compile",
    "field_verified",
}
ALLOWED_PROTOCOLS = {"codesys_st_text_v1"}


@dataclass
class GuardResult:
    passed: bool
    issues: list[str] = field(default_factory=list)


def validate_golden_manifest(skill_dir: Path, manifest: dict[str, Any]) -> GuardResult:
    issues: list[str] = []
    examples_dir = skill_dir / "examples"

    for bundle in manifest.get("bundles", []):
        bundle_id = bundle.get("bundle_id", "<missing>")
        missing = sorted(REQUIRED_BUNDLE_FIELDS - set(bundle))
        if missing:
            issues.append(f"{bundle_id}: missing required metadata fields: {', '.join(missing)}.")

        verification_level = bundle.get("verification_level")
        if verification_level not in ALLOWED_VERIFICATION_LEVELS:
            issues.append(f"{bundle_id}: verification_level must be one of {sorted(ALLOWED_VERIFICATION_LEVELS)}.")

        protocol = bundle.get("protocol")
        if protocol not in ALLOWED_PROTOCOLS:
            issues.append(f"{bundle_id}: protocol must be one of {sorted(ALLOWED_PROTOCOLS)}.")

        promotion_evidence = bundle.get("promotion_evidence", [])
        if not isinstance(promotion_evidence, list) or not promotion_evidence:
            issues.append(f"{bundle_id}: promotion_evidence must be a non-empty list.")

        description = str(bundle.get("description", ""))
        if "可直接复制" in description or "现场验证" in description:
            if verification_level != "field_verified":
                issues.append(f"{bundle_id}: strong reuse claims require field_verified verification_level.")

        for file_spec in bundle.get("files", []):
            rel_path = Path(file_spec.get("path", ""))
            if "candidates" in rel_path.parts:
                issues.append(f"{bundle_id}: candidate sample {rel_path} must not be listed as golden sample.")
            target = (examples_dir / rel_path).resolve()
            try:
                target.relative_to(examples_dir.resolve())
            except ValueError:
                issues.append(f"{bundle_id}: file path escapes examples directory: {rel_path}.")

    candidate_files = [
        item
        for item in (examples_dir / "candidates").rglob("*")
        if item.is_file() and item.name != "README.md"
    ]
    if candidate_files:
        for candidate in candidate_files:
            text = candidate.read_text(encoding="utf-8", errors="ignore")
            for marker in ("验证状态", "未决问题", "不可直接复制", "晋升"):
                if marker not in text:
                    issues.append(f"{candidate.relative_to(skill_dir)}: candidate sample must document {marker}.")

    return GuardResult(passed=not issues, issues=issues)


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    skill_dir = Path(__file__).resolve().parent.parent
    manifest = load_manifest(skill_dir / "examples" / "example_manifest.json")
    result = validate_golden_manifest(skill_dir, manifest)
    if result.passed:
        print("golden sample guard passed")
        return 0
    for issue in result.issues:
        print(issue)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
