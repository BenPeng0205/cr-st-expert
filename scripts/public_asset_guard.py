"""Check the exact, tool-independent public file set using the standard library."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

PUBLIC_FILES = (
    "SKILL.md", "README.md", "README.zh-CN.md", "LICENSE", "requirements.txt", "config.yaml",
    "command.yaml", "test-prompts.json", "deploy/README.md",
    "docs/product-contract.md", "docs/golden-sample-policy.md",
    "docs/离线POU测试规则.md",
)
PUBLIC_DIRS = ("assets", "rules", "references", "templates", "examples", "scripts", "test", "evals")
SKIP_PARTS = {"__pycache__", ".pytest_cache", "output", ".git"}
PRIVATE_PATH = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:Users|home)/[A-Za-z0-9_.-]+/)")
PRIVATE_IP = re.compile(r"\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b")
CREDENTIAL = re.compile(r"(?:AKIA[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY)")
SECRET_ASSIGNMENT = re.compile(r'''(?i)(?:password|passwd|api_key|apikey|client_secret|access_token)\s*[:=]\s*["'][^"']{6,}["']''')
INTERNAL_MARKERS = (
    "cr-" + "motion-expert", "cr-" + "codesys-cli", "st-" + "graph",
    "llm-" + "synchronizer", "cr-" + "synchronizer-st-expert",
    "Lic" + "OS", "evolve-" + "anything", "ai-" + "workspace",
)


@dataclass
class PublicAssetResult:
    passed: bool
    issues: list[str] = field(default_factory=list)


def public_files(root: Path) -> list[Path]:
    root = root.resolve()
    files = [root / rel for rel in PUBLIC_FILES]
    for rel in PUBLIC_DIRS:
        directory = root / rel
        if not directory.is_dir():
            raise ValueError(f"missing public directory: {rel}")
        files.extend(p for p in directory.rglob("*") if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_PARTS))
    for path in files:
        if not path.is_file():
            raise ValueError(f"missing public file: {path.relative_to(root)}")
        if path.is_symlink():
            raise ValueError(f"public symlink forbidden: {path.relative_to(root)}")
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError("public file escapes package root") from exc
    return sorted(set(files), key=lambda p: p.relative_to(root).as_posix())


def check_public_assets(root: Path) -> PublicAssetResult:
    issues: list[str] = []
    try:
        files = public_files(root)
    except ValueError as exc:
        return PublicAssetResult(False, [str(exc)])
    for path in files:
        rel = path.relative_to(root.resolve()).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            issues.append(f"{rel}: invalid UTF-8")
            continue
        if chr(0xFFFD) in text:
            issues.append(f"{rel}: replacement character")
        for pattern, label in [(PRIVATE_PATH, "machine path"), (PRIVATE_IP, "private IP"), (CREDENTIAL, "credential"), (SECRET_ASSIGNMENT, "secret assignment")]:
            for number, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    issues.append(f"{rel}:{number}: {label}")
        for marker in INTERNAL_MARKERS:
            if marker.casefold() in text.casefold():
                issues.append(f"{rel}: internal dependency marker")
    return PublicAssetResult(not issues, issues)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = check_public_assets(args.root)
    print(json.dumps({"passed": result.passed, "issues": result.issues}, ensure_ascii=False, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
