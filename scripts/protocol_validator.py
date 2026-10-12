from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PROBABLE_MOJIBAKE_PATTERNS = [
    chr(0xFFFD),
    "".join(chr(codepoint) for codepoint in (0x9354, 0x71BB, 0x5158)),
    "".join(chr(codepoint) for codepoint in (0x6434, 0x64B2, 0x7DF7)),
    "".join(chr(codepoint) for codepoint in (0x95AB, 0x6C33, 0x7E43)),
    "".join(chr(codepoint) for codepoint in (0x7039, 0x5C7E, 0x66A3)),
    "".join(chr(codepoint) for codepoint in (0x93C7, 0x5B58, 0x67CA)),
]
FORBIDDEN_HEADER_FIELDS = ["编程人员", "时间", "版本", "更新日期"]
BARE_UNIT_PATTERNS = [
    re.compile(r"//[^\n\[]*\b(?:rpm|W|A|N\.m|mm/s²|mm/s|mm|ms|s)\b", re.IGNORECASE),
    re.compile(r"//[^\n\[]*单位[:：]"),
]
KNOWN_LIBRARY_DEPENDENCIES = {"暂无", "Standard", "PLCopen MC"}
STANDARD_LOGICAL_PREFIX = {
    "enum": "DUTs/",
    "struct": "DUTs/",
    "gvl": "GVLs/",
    "function": "POUs/FCs/",
    "function_block": "POUs/FBs/",
    "program": "POUs/PRGs/",
}
PUBLIC_NAME_PREFIXES = {
    "enum": "E_",
    "struct": "ST_",
    "gvl": "GVL_",
    "function": "F_",
    "function_block": "FB_",
    "program": "PRG_",
}
STANDALONE_CHILD_FAMILIES = {"method", "action", "property"}
DECLARATION_PATTERNS = {
    "function_block": re.compile(r"^\s*FUNCTION_BLOCK\s+([A-Za-z][A-Za-z0-9_]*)\b", flags=re.MULTILINE),
    "function": re.compile(r"^\s*FUNCTION\s+([A-Za-z][A-Za-z0-9_]*)\b", flags=re.MULTILINE),
    "program": re.compile(r"^\s*PROGRAM\s+([A-Za-z][A-Za-z0-9_]*)\b", flags=re.MULTILINE),
    "enum": re.compile(r"^\s*TYPE\s+([A-Za-z][A-Za-z0-9_]*)\s*:", flags=re.MULTILINE),
    "struct": re.compile(r"^\s*TYPE\s+([A-Za-z][A-Za-z0-9_]*)\s*:", flags=re.MULTILINE),
}
SEGMENT_MARKER_PATTERN = re.compile(
    r"^// === (?P<kind>METHOD|ACTION|PROPERTY) (?P<name>[A-Za-z][A-Za-z0-9_]*) ===\s*$",
    flags=re.MULTILINE,
)
SEGMENT_NAME_PREFIX = {
    "METHOD": "M_",
    "ACTION": "A_",
    "PROPERTY": "P_",
}


@dataclass
class ValidationResult:
    passed: bool
    issues: list[str] = field(default_factory=list)


def _first_non_empty_line(content: str) -> str:
    for line in content.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _contains_mojibake(content: str) -> bool:
    return any(marker in content for marker in PROBABLE_MOJIBAKE_PATTERNS)


def _type_definition_count(content: str) -> int:
    return len(re.findall(r"^\s*TYPE\s+(?:E_|ST_)[A-Za-z0-9_]*\s*:", content, flags=re.MULTILINE))


def _enum_explicit_values(content: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r"^\s*[A-Za-z][A-Za-z0-9_]*\s*:=\s*([^,\)\s]+)", content, flags=re.MULTILINE):
        values.append(match.group(1).strip())
    return values


def _duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def _implementation_marker_index(content: str) -> int:
    return content.find("// === IMPLEMENTATION ===")


def _full_doc_block_index(content: str) -> int:
    return content.find("/// =======================================================================")


def _library_dependency_value(content: str) -> str | None:
    match = re.search(r"^\s*///\s*库依赖\s*[:：]\s*(.+?)\s*$", content, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def _expected_file_stem(path: str) -> str:
    return Path(path.replace("\\", "/")).stem


def _public_name_issue(path: str, family: str, name: str) -> str | None:
    prefix = PUBLIC_NAME_PREFIXES.get(family)
    if prefix is None:
        return f"{path}: Unknown family {family}."
    if not re.fullmatch(rf"{re.escape(prefix)}[A-Z][A-Za-z0-9]*", name):
        return f"{path}: public object name {name} must use {prefix}PascalCase with no extra underscores."
    return None


def _declared_public_name(family: str, content: str) -> str | None:
    pattern = DECLARATION_PATTERNS.get(family)
    if pattern is None:
        return None
    match = pattern.search(content)
    if match:
        return match.group(1)
    return None


def _validate_public_object_name(path: str, family: str, content: str) -> list[str]:
    issues: list[str] = []
    expected_name = _expected_file_stem(path)

    if family == "gvl":
        name = expected_name
    else:
        name = _declared_public_name(family, content)
        if name is None:
            return issues

    name_issue = _public_name_issue(path, family, name)
    if name_issue:
        issues.append(name_issue)

    file_name_issue = _public_name_issue(path, family, expected_name)
    if file_name_issue:
        issues.append(file_name_issue.replace("public object name", "file stem"))

    if family != "gvl" and name != expected_name:
        issues.append(f"{path}: file stem {expected_name} must match declared object name {name}.")

    return issues


def _validate_call_format(path: str, content: str) -> list[str]:
    issues: list[str] = []
    lines = content.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if ":=" in stripped and re.search(r"\w+\([^)]*:=.*\);?$", stripped):
            issues.append(f"{path}: named argument call must place each pin on its own line.")
        if stripped == ");" and not line.startswith("    "):
            issues.append(f"{path}: closing ); must align with call pins using four spaces.")
    return issues


def _validate_executable_doc_block(path: str, content: str) -> list[str]:
    issues: list[str] = []
    marker_index = _implementation_marker_index(content)
    block_index = _full_doc_block_index(content)
    if marker_index < 0:
        return issues
    if block_index < 0:
        issues.append(f"{path}: full function comment block is missing after implementation marker.")
        return issues
    if block_index < marker_index:
        issues.append(f"{path}: full function comment block must be placed after implementation marker.")
    if block_index > marker_index:
        between = content[marker_index + len("// === IMPLEMENTATION ==="):block_index].strip()
        if between:
            issues.append(f"{path}: full function comment block must be the first content after implementation marker.")

    next_block_index = content.find("/// =======================================================================", block_index + len("/// ======================================================================="))
    if next_block_index < 0:
        block_text = content[block_index:]
    else:
        third_block_index = content.find("/// =======================================================================", next_block_index + len("/// ======================================================================="))
        block_text = content[block_index:] if third_block_index < 0 else content[block_index:third_block_index]
    for label in ("名称", "功能", "库依赖", "使用说明"):
        if not re.search(rf"^\s*///\s*{label}\s*[:：]", block_text, flags=re.MULTILINE):
            issues.append(f"{path}: full function comment block must include {label}.")
    return issues


def _segment_blocks(content: str) -> list[tuple[str, str, str]]:
    markers = list(SEGMENT_MARKER_PATTERN.finditer(content))
    blocks: list[tuple[str, str, str]] = []
    for index, marker in enumerate(markers):
        start = marker.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(content)
        blocks.append((marker.group("kind"), marker.group("name"), content[start:end]))
    return blocks


def _validate_mirror_segments(path: str, content: str) -> list[str]:
    issues: list[str] = []
    for kind, name, body in _segment_blocks(content):
        prefix = SEGMENT_NAME_PREFIX[kind]
        if not re.fullmatch(rf"{re.escape(prefix)}[A-Z][A-Za-z0-9]*", name):
            issues.append(f"{path}: {kind} segment {name} must use {prefix}PascalCase with no extra underscores.")

        if kind == "METHOD":
            declaration = re.search(r"^\s*METHOD\s+PUBLIC\s+([A-Za-z][A-Za-z0-9_]*)\b", body, flags=re.MULTILINE)
            if declaration is None:
                issues.append(f"{path}: METHOD segment {name} must declare METHOD PUBLIC {name}.")
            elif declaration.group(1) != name:
                issues.append(f"{path}: METHOD declaration {declaration.group(1)} must match segment {name}.")
            if "// === IMPLEMENTATION ===" not in body:
                issues.append(f"{path}: METHOD segment {name} must include implementation marker.")

        if kind == "ACTION":
            if re.search(r"^\s*ACTION\b", body, flags=re.MULTILINE):
                issues.append(f"{path}: ACTION segment {name} must not declare ACTION header.")
            if "// === IMPLEMENTATION ===" not in body:
                issues.append(f"{path}: ACTION segment {name} must include implementation marker.")

        if kind == "PROPERTY":
            declaration = re.search(
                rf"^\s*PROPERTY\s+PUBLIC\s+{re.escape(name)}\s*:\s*[A-Za-z0-9_()]+",
                body,
                flags=re.MULTILINE,
            )
            if declaration is None:
                issues.append(f"{path}: PROPERTY segment {name} must declare PROPERTY PUBLIC {name}.")
            if "// === GET ===" not in body or "// === SET ===" not in body:
                issues.append(f"{path}: PROPERTY segment {name} must include GET and SET sections.")
            if "// === IMPLEMENTATION ===" in body:
                issues.append(f"{path}: PROPERTY segment {name} must not include implementation markers inside GET/SET sections.")
    return issues


def validate_file_content(file_spec: dict[str, Any], content: str) -> list[str]:
    issues: list[str] = []
    family = file_spec["family"]
    path = file_spec["path"]

    if family in STANDALONE_CHILD_FAMILIES:
        return [f"{path}: {family} must be aggregated inside parent FUNCTION_BLOCK mirror file."]

    if _contains_mojibake(content):
        issues.append(f"{path}: probable mojibake detected.")

    if "(*" in content or "*)" in content:
        issues.append(f"{path}: forbidden IEC block comment syntax detected.")

    if "\t" in content:
        issues.append(f"{path}: tabs are forbidden; use four spaces.")

    for field_name in FORBIDDEN_HEADER_FIELDS:
        if re.search(rf"^\s*///\s*{re.escape(field_name)}\s*[:：]", content, flags=re.MULTILINE):
            issues.append(f"{path}: file header must not include {field_name}.")

    if family in {"function_block", "function", "program", "gvl", "enum", "struct"}:
        library_dependency = _library_dependency_value(content)
        if library_dependency is None:
            issues.append(f"{path}: file header must include library dependency; use 暂无 when unknown.")
        elif not library_dependency:
            issues.append(f"{path}: file header library dependency must not be empty; use 暂无 when unknown.")
        elif library_dependency not in KNOWN_LIBRARY_DEPENDENCIES:
            issues.append(f"{path}: file header library dependency must be 暂无 or a known explicit library.")

    for pattern in BARE_UNIT_PATTERNS:
        if pattern.search(content):
            issues.append(f"{path}: physical units in comments must use [unit] format.")
            break

    if family in {"function_block", "function", "program"}:
        issues.extend(_validate_call_format(path, content))

    if family in PUBLIC_NAME_PREFIXES:
        issues.extend(_validate_public_object_name(path, family, content))

    if family == "function_block":
        issues.extend(_validate_executable_doc_block(path, content))
        issues.extend(_validate_mirror_segments(path, content))
        if "{attribute 'hide_all_locals'}" not in content:
            issues.append(f"{path}: FUNCTION_BLOCK must include hide_all_locals attribute.")
        if "FUNCTION_BLOCK " not in content:
            issues.append(f"{path}: FUNCTION_BLOCK declaration is missing.")
        if "// === IMPLEMENTATION ===" not in content:
            issues.append(f"{path}: parent implementation marker is missing.")

    elif family == "function":
        issues.extend(_validate_executable_doc_block(path, content))
        if "FUNCTION " not in content:
            issues.append(f"{path}: FUNCTION declaration is missing.")
        if "// === IMPLEMENTATION ===" not in content:
            issues.append(f"{path}: FUNCTION must include implementation marker.")

    elif family == "program":
        issues.extend(_validate_executable_doc_block(path, content))
        if "PROGRAM " not in content:
            issues.append(f"{path}: PROGRAM declaration is missing.")
        if "// === IMPLEMENTATION ===" not in content:
            issues.append(f"{path}: PROGRAM must include implementation marker.")
        if "{attribute 'hide_all_locals'}" in content:
            issues.append(f"{path}: PROGRAM must not include hide_all_locals attribute.")

    elif family == "gvl":
        if "{attribute 'qualified_only'}" not in content:
            issues.append(f"{path}: GVL must include qualified_only attribute.")
        if "VAR_GLOBAL" not in content:
            issues.append(f"{path}: GVL declaration is missing.")

    elif family == "enum":
        if "{attribute 'qualified_only'}" not in content or "{attribute 'strict'}" not in content:
            issues.append(f"{path}: ENUM must include qualified_only and strict attributes.")
        if "TYPE E_" not in content:
            issues.append(f"{path}: ENUM type declaration is missing.")
        if _type_definition_count(content) != 1:
            issues.append(f"{path}: ENUM file must contain exactly one DUT definition.")
        duplicates = _duplicate_values(_enum_explicit_values(content))
        if duplicates:
            issues.append(f"{path}: ENUM explicit values must be unique; duplicated values: {', '.join(duplicates)}.")

    elif family == "struct":
        if "TYPE ST_" not in content or "STRUCT" not in content:
            issues.append(f"{path}: STRUCT declaration is missing.")
        if _type_definition_count(content) != 1:
            issues.append(f"{path}: STRUCT file must contain exactly one DUT definition.")

    else:
        issues.append(f"{path}: Unknown family {family}.")

    return issues


def validate_file_location(file_spec: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    family = file_spec["family"]
    path = file_spec["path"].replace("\\", "/")
    logical_path = file_spec.get("logical_path")

    if family in STANDALONE_CHILD_FAMILIES:
        return [f"{path}: {family} files are not CODESYS ST text canonical files."]

    if logical_path is None:
        issues.append(f"{path}: logical_path is required to declare standard project folder placement.")
        return issues

    normalized = str(logical_path).replace("\\", "/")
    expected_prefix = STANDARD_LOGICAL_PREFIX.get(family)
    if expected_prefix is None:
        issues.append(f"{path}: Unknown family {family}.")
        return issues

    if not normalized.startswith(expected_prefix):
        issues.append(f"{path}: logical_path must be under {expected_prefix}.")

    if Path(normalized).name != Path(path).name:
        issues.append(f"{path}: logical_path filename must match exchange file name.")

    forbidden_segments = {"Device", "Application", "Data Types", "Functions", "Examples"}
    segments = set(Path(normalized).parts)
    found_forbidden = sorted(forbidden_segments & segments)
    if found_forbidden:
        issues.append(
            f"{path}: logical_path must use standard project folders, not CODESYS export folders: {', '.join(found_forbidden)}."
        )

    return issues


def validate_example_manifest(skill_dir: Path, manifest: dict[str, Any]) -> ValidationResult:
    issues: list[str] = []

    if manifest.get("skill_name") != "cr-st-expert":
        issues.append("example_manifest.json: skill_name must be cr-st-expert.")

    for bundle in manifest.get("bundles", []):
        if bundle.get("protocol") != "codesys_st_text_v1":
            issues.append(f"{bundle.get('bundle_id', '<missing>')}: protocol must be codesys_st_text_v1.")
        for file_spec in bundle.get("files", []):
            file_path = skill_dir / "examples" / file_spec["path"]
            issues.extend(validate_file_location(file_spec))
            if not file_path.exists():
                issues.append(f"{file_spec['path']}: file is missing.")
                continue
            content = file_path.read_text(encoding="utf-8")
            issues.extend(validate_file_content(file_spec, content))

    return ValidationResult(passed=not issues, issues=issues)


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
