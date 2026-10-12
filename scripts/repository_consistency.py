from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


CHECK_ROOTS = [
    "SKILL.md",
    "README.md",
    "README.zh-CN.md",
    "deploy",
    "assets",
    "config.yaml",
    "command.yaml",
    "test-prompts.json",
    "docs",
    "rules",
    "references",
    "templates",
    "examples",
    "scripts",
    "test",
    "evals",
]

IGNORED_PARTS = {".git", "__pycache__", "output"}
INTENTIONAL_TEST_FILES = {
    "test_protocol_validator.py",
    "test_repository_consistency.py",
    "test_st_semantic_linter.py",
}
SCRIPT_FILES_WITH_REGEX = {
    "protocol_validator.py",
    "repository_consistency.py",
    "st_semantic_linter.py",
}
POLICY_FILES = {
    "golden-sample-policy.md",
}

FORBIDDEN_PORTABLE_REFERENCE_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/](?:Users|home|private-workspace)(?:[\\/]|$)", re.IGNORECASE),
)

HUNGARIAN_PREFIX_BY_TYPE = {
    "BOOL": "b",
    "BYTE": "by",
    "WORD": "w",
    "DWORD": "dw",
    "LWORD": "lw",
    "INT": "i",
    "DINT": "di",
    "SINT": "si",
    "USINT": "usi",
    "UINT": "ui",
    "UDINT": "udi",
    "LINT": "li",
    "ULINT": "uli",
    "REAL": "r",
    "LREAL": "lr",
    "STRING": "s",
    "WSTRING": "s",
    "TIME": "t",
    "TON": "ton",
    "TOF": "tof",
    "TP": "tp",
    "R_TRIG": "rtrig",
    "F_TRIG": "ftrig",
}


@dataclass
class ConsistencyResult:
    passed: bool
    issues: list[str] = field(default_factory=list)


def _iter_files(skill_dir: Path) -> list[Path]:
    files: list[Path] = []
    for root in CHECK_ROOTS:
        path = skill_dir / root
        if path.is_file():
            files.append(path)
        elif path.exists():
            files.extend(item for item in path.rglob("*") if item.is_file())
    return [item for item in files if not (set(item.parts) & IGNORED_PARTS)]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _expected_variable_prefix(var_type: str, block_header: str) -> str | None:
    if "CONSTANT" in block_header:
        return "cn"

    normalized = var_type.strip().upper()
    if normalized.startswith("ARRAY"):
        return "a"
    base_type = normalized.split()[0]
    if base_type in HUNGARIAN_PREFIX_BY_TYPE:
        return HUNGARIAN_PREFIX_BY_TYPE[base_type]
    if base_type.startswith("ST_") or base_type.endswith("_REF"):
        return "st"
    if base_type.startswith("E_"):
        return "e"
    if base_type.startswith("FB_") or base_type.startswith("MC_") or base_type.startswith("SMC_"):
        return "fb"
    if base_type.startswith("POINTER"):
        return "p"
    return None


def _check_hungarian_declarations(rel_path: Path, text: str, issues: list[str]) -> None:
    block_header: str | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        block_match = re.match(r"VAR(?:_(?:INPUT|OUTPUT|IN_OUT|TEMP|GLOBAL))?(?:\s+CONSTANT|\s+RETAIN)?\b", stripped)
        if block_match:
            block_header = block_match.group(0).upper()
            continue
        if re.match(r"END_VAR\b", stripped):
            block_header = None
            continue
        if block_header is None:
            continue

        declaration_match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^;]+);", line)
        if not declaration_match:
            continue
        variable_name = declaration_match.group(1)
        declaration_type = declaration_match.group(2).split(":=", 1)[0].strip()
        expected_prefix = _expected_variable_prefix(declaration_type, block_header)
        if expected_prefix and not variable_name.startswith(expected_prefix):
            issues.append(
                f"{rel_path}:{line_number}: variable '{variable_name}' should use '{expected_prefix}' prefix for {declaration_type}."
            )


def check_repository(skill_dir: Path) -> ConsistencyResult:
    issues: list[str] = []
    stale_metadata = re.compile(r"更新时间|更新日期|适用版本|最后更新|版本历史|\*\*版本\*\*|> 版本:|> 更新日期:")
    bare_units = re.compile(r"//[^\n\[]*\b(?:rpm|N\.m|mm/s²|mm/s|mm|ms)\b", re.IGNORECASE)
    single_line_named_call = re.compile(r"\w+\([^\n)]*:=.*\)")

    for path in _iter_files(skill_dir):
        rel_path = path.relative_to(skill_dir)
        text = _read_text(path)

        if path.suffix.lower() == ".md":
            for block in re.finditer(r"```(?:st|iecst)[^\n]*\n(.*?)```", text, flags=re.DOTALL):
                for terminator in re.finditer(r"^[ \t]*END_(?:IF|CASE|FOR|WHILE|REPEAT)[ \t]*(?://[^\n]*)?$", block.group(1), flags=re.MULTILINE):
                    line_number = text.count("\n", 0, block.start(1) + terminator.start()) + 1
                    issues.append(f"{rel_path}:{line_number}: control statement terminator requires semicolon.")

        if "\t" in text:
            issues.append(f"{rel_path}: Tab is forbidden.")
        if path.name not in SCRIPT_FILES_WITH_REGEX and " / //" in text:
            issues.append(f"{rel_path}: broken comment splice detected.")
        if path.name not in SCRIPT_FILES_WITH_REGEX | INTENTIONAL_TEST_FILES and stale_metadata.search(text):
            issues.append(f"{rel_path}: stale version/time metadata detected.")

        if path.name not in INTENTIONAL_TEST_FILES | SCRIPT_FILES_WITH_REGEX and bare_units.search(text):
            issues.append(f"{rel_path}: bare physical unit detected in comment.")

        if path.suffix.lower() in {".st", ".md"} and path.name not in INTENTIONAL_TEST_FILES:
            _check_hungarian_declarations(rel_path, text, issues)
            for line_number, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if single_line_named_call.search(stripped) and not stripped.startswith("re.compile"):
                    issues.append(f"{rel_path}:{line_number}: named argument call should be multi-line.")

        if "(*" in text or "*)" in text:
            allowed = "禁用 `(* *)`" in text or "禁止 `(* *)`" in text or "禁止使用 `(* ... *)`" in text
            if path.name not in INTENTIONAL_TEST_FILES | SCRIPT_FILES_WITH_REGEX | POLICY_FILES and "antipatterns" not in path.name and not allowed:
                issues.append(f"{rel_path}: IEC block comment syntax detected.")

        if path.name not in INTENTIONAL_TEST_FILES | SCRIPT_FILES_WITH_REGEX:
            for forbidden in FORBIDDEN_PORTABLE_REFERENCE_PATTERNS:
                match = forbidden.search(text)
                if match:
                    issues.append(f"{rel_path}: non-portable local path detected: {match.group(0)}")

    return ConsistencyResult(passed=not issues, issues=issues)


def main() -> int:
    skill_dir = Path(__file__).resolve().parent.parent
    result = check_repository(skill_dir)
    if result.passed:
        print("repository consistency passed")
        return 0
    for issue in result.issues:
        print(issue)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
