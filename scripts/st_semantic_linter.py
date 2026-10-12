from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


EXECUTABLE_FAMILIES = {"function_block", "function", "program"}
ST_OBJECT_FAMILIES = EXECUTABLE_FAMILIES | {"gvl", "enum", "struct"}
EXCLUDED_PROJECT_DIRS = {".git", ".pytest_cache", "__pycache__", "output", "build", "dist"}
DOMAIN_TOKEN_HINTS = {
    "curve": ("Curve",),
    "曲线": ("Curve",),
    "matrix": ("Matrix",),
    "矩阵": ("Matrix",),
    "filter": ("Filter",),
    "滤波": ("Filter",),
    "array": ("Array",),
    "数组": ("Array",),
    "retain": ("Retain",),
    "掉电保持": ("Retain",),
    "time": ("Time",),
    "时间": ("Time",),
}


def _chars(*codepoints: int) -> str:
    return "".join(chr(codepoint) for codepoint in codepoints)


PROBABLE_MOJIBAKE_MARKERS = {
    _chars(0x9354, 0x71BB, 0x5158),
    _chars(0x6434, 0x64B2, 0x7DF7, 0x74A7),
    _chars(0x5A34, 0x5B2D, 0x762F),
    _chars(0x7F02, 0x682B, 0x25BC),
    chr(0xFFFD),
}

LEGACY_LIBRARY_BRAND_PATTERN = re.compile(r"oscat", flags=re.IGNORECASE)
BOILERPLATE_COMMENT_PATTERNS = [
    (
        re.compile(r"^\s*///\s*功能\s*[:：].*(?:数据类型\s+ST_|功能块\s+FB_|函数\s+F_)", flags=re.MULTILINE),
        "function description must explain behavior, not repeat object kind/name.",
    ),
    (
        re.compile(r"(?:保留|保持).*原始算法语义|字段已语义化命名"),
        "comment must describe behavior and engineering intent, not migration bookkeeping.",
    ),
    (
        re.compile(r"为什么不是|为什么不用|精度边界|百万分之一|工程收益很小|反而更容易漏判|不会吞掉"),
        "comment is over-explained; keep numeric tolerance rationale concise and avoid teaching-style comparisons.",
    ),
    (
        re.compile(
            r"本段刷新诊断、处理边界条件，并根据内部状态输出当前扫描周期结果|"
            r"状态只在有效分支内推进，避免无效输入改写保持量|"
            r"本段执行输入边界保护和核心计算，返回当前输入对应的确定性结果|"
            r"正常分支只使用当前输入和局部计算，避免隐藏状态影响返回值|"
            r"本段调度入口程序并刷新全局汇总状态|"
            r"调用顺序保持固定，便于离线断言读回一致的汇总结果|"
            r"由本周期输入和保持量计算得到，后续输出或状态判断直接使用该中间量|"
            r"专用功能逻辑|"
            r"按该对象的输入契约刷新对应工程输出|"
            r"的实现区按当前输入刷新输出"
        ),
        "generic filler implementation comment is forbidden; explain the actual algorithm, state transition, boundary, or function call.",
    ),
]
LIBRARY_DEPENDENCY_PATTERN = re.compile(r"^\s*///\s*库依赖\s*[:：]\s*(?P<value>.+?)\s*$", flags=re.MULTILINE)


@dataclass
class SemanticLintResult:
    passed: bool
    issues: list[str] = field(default_factory=list)
    checked_files: int = 0


def _line_number(content: str, index: int) -> int:
    return content.count("\n", 0, index) + 1


def _strip_line_comment(line: str) -> str:
    return line.split("//", 1)[0]


def _mask_comments_and_strings(content: str) -> str:
    """Preserve line/column positions while hiding comments and string literals."""

    masked = re.sub(r"\(\*.*?\*\)", lambda match: " " * len(match.group(0)), content, flags=re.DOTALL)
    masked = re.sub(r"'(?:''|[^'])*'", lambda match: " " * len(match.group(0)), masked)
    masked_lines = []
    for line in masked.splitlines(keepends=True):
        comment_index = line.find("//")
        if comment_index >= 0:
            line = line[:comment_index] + (" " * (len(line) - comment_index))
        masked_lines.append(line)
    return "".join(masked_lines)


def _first_declaration_index(family: str, content: str) -> int:
    patterns = {
        "function_block": r"^\s*FUNCTION_BLOCK\b",
        "function": r"^\s*FUNCTION\b",
        "program": r"^\s*PROGRAM\b",
        "gvl": r"^\s*VAR_GLOBAL\b",
        "enum": r"^\s*TYPE\b",
        "struct": r"^\s*TYPE\b",
    }
    match = re.search(patterns.get(family, r"$^"), content, flags=re.MULTILINE)
    return match.start() if match else len(content)


def _looks_like_complete_object(family: str, content: str) -> bool:
    if family == "function_block":
        return bool(re.search(r"^\s*FUNCTION_BLOCK\s+[A-Za-z_][A-Za-z0-9_]*\b", content, flags=re.MULTILINE))
    if family == "function":
        return bool(re.search(r"^\s*FUNCTION\s+[A-Za-z_][A-Za-z0-9_]*\b", content, flags=re.MULTILINE))
    if family == "program":
        return bool(re.search(r"^\s*PROGRAM\s+[A-Za-z_][A-Za-z0-9_]*\b", content, flags=re.MULTILINE))
    if family == "gvl":
        return bool(re.search(r"^\s*VAR_GLOBAL\b", content, flags=re.MULTILINE))
    if family == "enum":
        return bool(re.search(r"^\s*TYPE\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*\(", content, flags=re.MULTILINE))
    if family == "struct":
        return bool(re.search(r"^\s*TYPE\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*STRUCT\b", content, flags=re.MULTILINE))
    return False


def infer_family(path: Path | str, content: str) -> str:
    name = Path(path).name
    if re.search(r"^\s*FUNCTION_BLOCK\b", content, flags=re.MULTILINE):
        return "function_block"
    if re.search(r"^\s*FUNCTION\s+\w+", content, flags=re.MULTILINE):
        return "function"
    if re.search(r"^\s*PROGRAM\b", content, flags=re.MULTILINE):
        return "program"
    if re.search(r"^\s*VAR_GLOBAL\b", content, flags=re.MULTILINE):
        return "gvl"
    if re.search(r"^\s*TYPE\s+\w+\s*:\s*STRUCT\b", content, flags=re.MULTILINE):
        return "struct"
    if re.search(r"^\s*TYPE\s+\w+\s*:\s*\(", content, flags=re.MULTILINE):
        return "enum"
    if name.startswith("GVL_"):
        return "gvl"
    if name.startswith("E_"):
        return "enum"
    if name.startswith("ST_"):
        return "struct"
    return "unknown"


def _object_declarations(content: str) -> Iterable[tuple[str, str, int]]:
    patterns = [
        ("function_block", r"^\s*FUNCTION_BLOCK\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        ("function", r"^\s*FUNCTION\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        ("program", r"^\s*PROGRAM\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        ("method", r"^\s*METHOD(?:\s+(?:PUBLIC|PRIVATE|PROTECTED|INTERNAL))?\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        ("action", r"^\s*ACTION\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        ("property", r"^\s*PROPERTY(?:\s+(?:PUBLIC|PRIVATE|PROTECTED|INTERNAL))?\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        ("type", r"^\s*TYPE\s+([A-Za-z_][A-Za-z0-9_]*)\s*:"),
    ]
    for family, pattern in patterns:
        for match in re.finditer(pattern, content, flags=re.MULTILINE):
            yield family, match.group(1), match.start()


def _is_pascal_case_body(body: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Za-z0-9]*", body))


def _pascal_words(body: str) -> list[str]:
    return re.findall(r"[A-Z][a-z0-9]*|[A-Z]+(?=[A-Z]|$)|[0-9]+", body)


def _domain_tokens_from_root(root: Path) -> tuple[str, ...]:
    normalized_parts = [part.lower() for part in root.parts]
    tokens: list[str] = []
    for part in normalized_parts:
        for hint, hinted_tokens in DOMAIN_TOKEN_HINTS.items():
            if hint.lower() in part:
                for token in hinted_tokens:
                    if token not in tokens:
                        tokens.append(token)
    return tuple(tokens)


def _lint_domain_context_redundancy(path: str, object_name: str, index: int, content: str, domain_tokens: Iterable[str]) -> list[str]:
    if "_" not in object_name:
        return []
    body = object_name.split("_", 1)[1]
    words = _pascal_words(body)
    issues: list[str] = []
    for token in domain_tokens:
        if token in words:
            issues.append(
                f"{path}:{_line_number(content, index)}: public object name repeats library domain token '{token}'; remove it unless it is a type family, standard term, conflict guard, or compatibility requirement."
            )
    return issues


def _lint_public_object_names(path: str, content: str, domain_tokens: Iterable[str] = ()) -> list[str]:
    issues: list[str] = []
    prefixes = {
        "function_block": "FB_",
        "function": "F_",
        "program": "PRG_",
        "method": "M_",
        "action": "A_",
        "property": "P_",
    }
    type_prefixes = ("E_", "ST_", "U_", "I_")

    for family, object_name, index in _object_declarations(content):
        if family == "program" and object_name == "PLC_PRG":
            continue
        if family == "type":
            expected = next((prefix for prefix in type_prefixes if object_name.startswith(prefix)), "")
            if not expected:
                issues.append(f"{path}:{_line_number(content, index)}: DUT name must start with E_/ST_/U_/I_.")
                continue
        else:
            expected = prefixes.get(family, "")
            if expected and not object_name.startswith(expected):
                issues.append(f"{path}:{_line_number(content, index)}: {family} name must start with {expected}.")
                continue

        if "_" not in object_name:
            continue
        body = object_name.split("_", 1)[1]
        if "_" in body:
            issues.append(f"{path}:{_line_number(content, index)}: public object body must not contain extra underscore.")
        if not _is_pascal_case_body(body):
            issues.append(f"{path}:{_line_number(content, index)}: public object body must use PascalCase.")
        if family in ST_OBJECT_FAMILIES:
            issues.extend(_lint_domain_context_redundancy(path, object_name, index, content, domain_tokens))
    return issues


def _lint_attributes(path: str, family: str, content: str) -> list[str]:
    issues: list[str] = []
    declaration_index = _first_declaration_index(family, content)
    header_region = content[:declaration_index]

    if family in {"function_block", "function"} and _looks_like_complete_object(family, content):
        if "{attribute 'hide_all_locals'}" not in header_region:
            issues.append(f"{path}: FB/FUNCTION must declare {{attribute 'hide_all_locals'}} before declaration.")
    if family == "program" and "{attribute 'hide_all_locals'}" in header_region:
        issues.append(f"{path}: PROGRAM must not use {{attribute 'hide_all_locals'}}.")
    if family == "enum" and _looks_like_complete_object(family, content):
        if "{attribute 'qualified_only'}" not in header_region:
            issues.append(f"{path}: ENUM must declare {{attribute 'qualified_only'}}.")
        if "{attribute 'strict'}" not in header_region:
            issues.append(f"{path}: ENUM must declare {{attribute 'strict'}}.")
    if family == "gvl" and _looks_like_complete_object(family, content):
        if "{attribute 'qualified_only'}" not in header_region:
            issues.append(f"{path}: GVL must declare {{attribute 'qualified_only'}}.")
    return issues


def _lint_file_header(path: str, family: str, content: str) -> list[str]:
    issues: list[str] = []
    if family not in ST_OBJECT_FAMILIES or not _looks_like_complete_object(family, content):
        return issues

    header_region = content[:_first_declaration_index(family, content)]
    if not re.search(r"^\s*///\s*功能\s*[:：]\s*\S+", header_region, flags=re.MULTILINE):
        issues.append(f"{path}: file header must include /// 功能.")
    if not re.search(r"^\s*///\s*库依赖\s*[:：]\s*\S+", header_region, flags=re.MULTILINE):
        issues.append(f"{path}: file header must include /// 库依赖.")
    return issues


def _lint_comment_encoding(path: str, content: str) -> list[str]:
    issues: list[str] = []
    for line_index, line in enumerate(content.splitlines(), start=1):
        stripped = line.lstrip()
        if not stripped.startswith("//"):
            continue
        if any(marker in stripped for marker in PROBABLE_MOJIBAKE_MARKERS):
            issues.append(f"{path}:{line_index}: comment appears mojibake.")
    return issues


def _lint_comment_and_dependency_quality(path: str, content: str) -> list[str]:
    issues: list[str] = []

    for match in LEGACY_LIBRARY_BRAND_PATTERN.finditer(content):
        issues.append(f"{path}:{_line_number(content, match.start())}: legacy source library brand must not appear in ST code or comments.")

    for pattern, message in BOILERPLATE_COMMENT_PATTERNS:
        for match in pattern.finditer(content):
            issues.append(f"{path}:{_line_number(content, match.start())}: {message}")

    for match in LIBRARY_DEPENDENCY_PATTERN.finditer(content):
        value = match.group("value")
        if "原生库" in value:
            issues.append(f"{path}:{_line_number(content, match.start())}: library dependency must list concrete library names; '原生库' is forbidden.")
        if "CODESYS" in value or "CodeSys" in value:
            issues.append(f"{path}:{_line_number(content, match.start())}: library dependency must list library names only, not platform names.")

    return issues


def _lint_basic_format(path: str, family: str, content: str) -> list[str]:
    issues: list[str] = []
    header_region = content[:_first_declaration_index(family, content)]

    if "(*" in content or "*)" in content:
        issues.append(f"{path}: block comment (* *) is forbidden; use // or ///.")

    for line_index, line in enumerate(content.splitlines(), start=1):
        if "\t" in line:
            issues.append(f"{path}:{line_index}: tab character is forbidden; use 4 spaces.")

    for line_index, line in enumerate(header_region.splitlines(), start=1):
        if re.search(r"^\s*///\s*(?:编程人员|作者|时间|日期|版本)\s*[:：]", line):
            issues.append(f"{path}:{line_index}: unstable author/time/version comment is forbidden.")
    return issues


def _lint_line_spacing(path: str, content: str) -> list[str]:
    issues: list[str] = []
    if "\n\n\n" in content:
        issues.append(f"{path}: more than one consecutive blank line is forbidden.")

    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) < 8:
        return issues

    blank_indexes = [index for index, line in enumerate(lines) if not line.strip()]
    if not blank_indexes:
        return issues

    alternating_blanks = 0
    for index in blank_indexes:
        if index == 0 or index >= len(lines) - 1:
            continue
        if lines[index - 1].strip() and lines[index + 1].strip():
            alternating_blanks += 1

    blank_ratio = len(blank_indexes) / len(lines)
    alternating_ratio = alternating_blanks / len(blank_indexes)
    if blank_ratio >= 0.45 and alternating_ratio >= 0.75:
        issues.append(
            f"{path}: suspicious every-line blank spacing detected "
            f"(blank_ratio={blank_ratio:.2f}, alternating_blank_ratio={alternating_ratio:.2f})."
        )
    return issues


def _lint_implementation_header(path: str, family: str, content: str) -> list[str]:
    issues: list[str] = []
    if family not in EXECUTABLE_FAMILIES or not _looks_like_complete_object(family, content):
        return issues

    marker_match = re.search(r"^\s*// === IMPLEMENTATION ===\s*$", content, flags=re.MULTILINE)
    if not marker_match:
        issues.append(f"{path}: executable object must include // === IMPLEMENTATION === marker.")
        return issues

    header_lines: list[str] = []
    for line in content[marker_match.end():].splitlines():
        if not line.strip():
            continue
        if not line.lstrip().startswith("///"):
            break
        header_lines.append(line)

    header = "\n".join(header_lines)
    required_labels = {
        "名称": "implementation header must include 名称.",
        "功能": "implementation header must include 功能.",
        "库依赖": "implementation header must include 库依赖.",
        "使用说明": "implementation header must include 使用说明.",
    }
    for label, message in required_labels.items():
        if not re.search(rf"^\s*///\s*{label}\s*[:：]\s*\S+", header, flags=re.MULTILINE):
            issues.append(f"{path}: {message}")

    if not re.search(r"^\s*///\s*使用说明\s*[:：]\s*1\.\s*\S+", header, flags=re.MULTILINE):
        issues.append(f"{path}: implementation usage note must include numbered item 1.")
    if not re.search(r"^\s*///\s*[:：]\s*2\.\s*\S+", header, flags=re.MULTILINE):
        issues.append(f"{path}: implementation usage note must include numbered item 2.")
    return issues


def _implementation_sections(content: str) -> list[tuple[int, str]]:
    marker_pattern = re.compile(r"^\s*// === IMPLEMENTATION ===\s*$", flags=re.MULTILINE)
    next_segment_pattern = re.compile(
        r"^\s*// === (?:METHOD|ACTION|PROPERTY|GET|SET)\b.*$",
        flags=re.MULTILINE,
    )
    sections: list[tuple[int, str]] = []

    for marker_match in marker_pattern.finditer(content):
        start = marker_match.end()
        next_segment_match = next_segment_pattern.search(content, start)
        end = next_segment_match.start() if next_segment_match else len(content)
        sections.append((start, content[start:end]))

    return sections


def _lint_engineering_implementation_comments(path: str, family: str, content: str) -> list[str]:
    issues: list[str] = []
    if family not in EXECUTABLE_FAMILIES or not _looks_like_complete_object(family, content):
        return issues

    for start_index, section in _implementation_sections(content):
        executable_lines: list[str] = []
        engineering_comment_lines: list[str] = []

        for line in section.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("///"):
                continue
            if stripped.startswith("//"):
                engineering_comment_lines.append(stripped)
                continue
            executable_lines.append(stripped)

        if executable_lines and not engineering_comment_lines:
            issues.append(
                f"{path}:{_line_number(content, start_index)}: implementation code must include engineering // comments."
            )
            continue

    return issues


def _var_blocks(content: str) -> Iterable[tuple[str, int, str]]:
    block_pattern = re.compile(
        r"^\s*(VAR(?:_(?:INPUT|OUTPUT|IN_OUT|TEMP|GLOBAL))?(?:\s+CONSTANT|\s+RETAIN)?)\b(?P<body>.*?)^\s*END_VAR\b",
        flags=re.MULTILINE | re.DOTALL,
    )
    for block_match in block_pattern.finditer(content):
        yield block_match.group(1).upper(), block_match.start(), block_match.group("body")


def _expected_variable_prefix(var_type: str, block_header: str) -> str | None:
    if "CONSTANT" in block_header:
        return "cn"

    normalized = var_type.strip().upper()
    if normalized.startswith("ARRAY"):
        return "a"
    base_type = normalized.split()[0]
    mapping = {
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
    if base_type in mapping:
        return mapping[base_type]
    if base_type.startswith("ST_") or base_type.endswith("_REF"):
        return "st"
    if base_type.startswith("E_"):
        return "e"
    if base_type.startswith("FB_"):
        return "fb"
    if base_type.startswith("POINTER"):
        return "p"
    return None


def _requires_safe_input_default(var_type: str) -> bool:
    normalized = var_type.strip().upper()
    if normalized.startswith("ARRAY"):
        return True
    base_type = normalized.split()[0]
    if base_type.startswith("ST_") or base_type.startswith("E_") or base_type.startswith("FB_"):
        return False
    if base_type.endswith("_REF"):
        return False
    return True


def _lint_variable_declaration_style(path: str, content: str) -> list[str]:
    issues: list[str] = []
    declaration_pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^;]+);")

    for block_header, block_start, block_body in _var_blocks(content):
        block_start_line = _line_number(content, block_start)
        declarations: list[tuple[int, str, int, int]] = []

        for offset, line in enumerate(block_body.splitlines(), start=1):
            code = _strip_line_comment(line)
            declaration_match = declaration_pattern.search(code)
            if not declaration_match:
                continue

            line_number = block_start_line + offset
            variable_name = declaration_match.group(1)
            declaration_type = declaration_match.group(2).split(":=", 1)[0].strip()
            colon_column = line.index(":")
            comment_column = line.find("//")
            declarations.append((line_number, line, colon_column, comment_column))

            if comment_column == -1:
                issues.append(f"{path}:{line_number}: variable declaration must include trailing // comment.")

            if block_header == "VAR_INPUT":
                if ":=" not in code and _requires_safe_input_default(declaration_type):
                    issues.append(f"{path}:{line_number}: VAR_INPUT declaration must provide a safe default value.")
                if re.search(r"\bPOINTER\s+TO\b", declaration_type, flags=re.IGNORECASE):
                    issues.append(f"{path}:{line_number}: VAR_INPUT must not expose POINTER; use VAR_IN_OUT instead.")

            expected_prefix = _expected_variable_prefix(declaration_type, block_header)
            if expected_prefix:
                if not variable_name.startswith(expected_prefix):
                    issues.append(
                        f"{path}:{line_number}: variable '{variable_name}' should use '{expected_prefix}' prefix for {declaration_type}."
                    )

        colon_columns = {colon_column for _, _, colon_column, _ in declarations}
        if len(colon_columns) > 1:
            first_line = declarations[0][0]
            issues.append(f"{path}:{first_line}: declaration ':' columns must align within each VAR block.")

        comment_columns = {comment_column for _, _, _, comment_column in declarations if comment_column != -1}
        if len(comment_columns) > 1:
            first_line = declarations[0][0]
            issues.append(f"{path}:{first_line}: trailing // comment columns must align within each VAR block.")

    return issues


def _lint_fb_error_contract(path: str, family: str, content: str) -> list[str]:
    issues: list[str] = []
    if family != "function_block" or not _looks_like_complete_object(family, content):
        return issues

    outputs = ""
    for block_header, _, block_body in _var_blocks(content):
        if block_header == "VAR_OUTPUT":
            outputs += "\n" + block_body
    if not outputs:
        issues.append(f"{path}: FUNCTION_BLOCK must expose VAR_OUTPUT diagnostics.")
        return issues
    if not re.search(r"^\s*(?:bError|xError)\s*:\s*BOOL\b", outputs, flags=re.MULTILINE):
        issues.append(f"{path}: FUNCTION_BLOCK must expose bError/xError BOOL output.")
    if not re.search(r"^\s*(?:diErrorID|udiErrorID)\s*:\s*(?:DINT|UDINT|DWORD)\b", outputs, flags=re.MULTILINE):
        issues.append(f"{path}: FUNCTION_BLOCK must expose diErrorID/udiErrorID diagnostic output.")
    return issues


def _lint_named_argument_call_style(path: str, content: str) -> list[str]:
    issues: list[str] = []
    pending_calls: list[dict[str, object]] = []

    for line_index, line in enumerate(content.splitlines(), start=1):
        code = _strip_line_comment(line).rstrip()
        stripped = code.strip()
        if not stripped:
            if pending_calls:
                issues.append(f"{path}:{line_index}: blank line inside named argument call is forbidden.")
            continue

        if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*(?::=|=>)[^)]*\)\s*;", stripped):
            issues.append(f"{path}:{line_index}: named argument call must use multiline pin format.")

        if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(\s*$", code):
            pending_calls.append({"pin_column": len(line) - len(line.lstrip(" ")) + 4, "operator_columns": []})
            continue

        if pending_calls and (":=" in stripped or "=>" in stripped):
            expected_column = int(pending_calls[-1]["pin_column"])
            actual_column = len(line) - len(line.lstrip(" "))
            if actual_column != expected_column:
                issues.append(f"{path}:{line_index}: named argument pin must use {expected_column} spaces indentation.")

            operator_match = re.search(r":=|=>", line)
            if operator_match:
                operator_columns = pending_calls[-1]["operator_columns"]
                assert isinstance(operator_columns, list)
                operator_columns.append(operator_match.start())

        if stripped in {");", ") THEN"} and pending_calls:
            call_state = pending_calls.pop()
            expected_column = int(call_state["pin_column"])
            actual_column = len(line) - len(line.lstrip(" "))
            if actual_column != expected_column:
                issues.append(f"{path}:{line_index}: call closing ');' must align with pins.")
            operator_columns = call_state["operator_columns"]
            assert isinstance(operator_columns, list)
            if len(set(operator_columns)) > 1:
                issues.append(f"{path}:{line_index}: named argument ':=' columns must align within each call.")

    return issues


def _lint_case_else(path: str, content: str) -> list[str]:
    issues: list[str] = []
    scan_content = _mask_comments_and_strings(content)
    for match in re.finditer(r"\bCASE\b", scan_content):
        end_match = re.search(r"\bEND_CASE\b", scan_content[match.end():])
        if not end_match:
            issues.append(f"{path}:{_line_number(content, match.start())}: CASE must end with END_CASE.")
            continue
        block = scan_content[match.start(): match.end() + end_match.end()]
        if not re.search(r"^\s*ELSE\b", block, flags=re.MULTILINE):
            issues.append(f"{path}:{_line_number(content, match.start())}: CASE must include ELSE branch.")
    return issues


def _lint_var_temp_fb_instances(path: str, content: str) -> list[str]:
    issues: list[str] = []
    for block_header, block_start, block_body in _var_blocks(content):
        if block_header != "VAR_TEMP":
            continue
        for type_name in ("TON", "TOF", "TP", "R_TRIG", "F_TRIG"):
            if re.search(rf":\s*{type_name}\s*;", block_body):
                issues.append(f"{path}:{_line_number(content, block_start)}: {type_name} instance must not be declared in VAR_TEMP.")
        if re.search(r":\s*FB_[A-Za-z0-9_]+\s*;", block_body):
            issues.append(f"{path}:{_line_number(content, block_start)}: FB instance must not be declared in VAR_TEMP.")
    return issues


def _lint_empty_pins(path: str, content: str) -> list[str]:
    issues: list[str] = []
    scan_content = _mask_comments_and_strings(content)
    for match in re.finditer(r"(?::=|=>)\s*(?:,|\))", scan_content):
        issues.append(f"{path}:{_line_number(content, match.start())}: empty named argument pin is forbidden.")
    return issues


def _lint_real_equality(path: str, content: str) -> list[str]:
    issues: list[str] = []
    real_vars: set[str] = set()
    for match in re.finditer(r"^\s*([a-z][A-Za-z0-9_]*)\s*:\s*(?:REAL|LREAL)\b", content, flags=re.MULTILINE):
        real_vars.add(match.group(1))
    if not real_vars:
        return issues
    for line_index, line in enumerate(content.splitlines(), start=1):
        code = _strip_line_comment(line)
        if ":=" in code or "<>" in code or "<=" in code or ">=" in code:
            continue
        if "=" not in code:
            continue
        for var_name in real_vars:
            if re.search(rf"\b{re.escape(var_name)}\b\s*=", code) or re.search(rf"=\s*\b{re.escape(var_name)}\b", code):
                issues.append(f"{path}:{line_index}: REAL/LREAL equality must use tolerance comparison.")
                break
    return issues


def _unsigned_length_guarded(lines: list[str], line_index: int, variable_name: str) -> bool:
    previous = "\n".join(_strip_line_comment(line) for line in lines[max(0, line_index - 9):line_index])
    guard_patterns = [
        rf"\bIF\s+{re.escape(variable_name)}\s*>\s*0\b",
        rf"\bIF\s+{re.escape(variable_name)}\s*>=\s*1\b",
        rf"\bIF\s+{re.escape(variable_name)}\s*<>\s*0\b",
        rf"\bIF\s+{re.escape(variable_name)}\s*=\s*0\s+THEN[\s\S]*?\bRETURN\s*;",
    ]
    return any(re.search(pattern, previous, flags=re.IGNORECASE) for pattern in guard_patterns)


def _lint_unsigned_minus_one_loop(path: str, content: str) -> list[str]:
    issues: list[str] = []
    unsigned_vars: set[str] = set()
    for match in re.finditer(r"^\s*([a-z][A-Za-z0-9_]*)\s*:\s*(?:USINT|UINT|UDINT|ULINT)\b", content, flags=re.MULTILINE):
        unsigned_vars.add(match.group(1))
    lines = content.splitlines()
    for line_index, line in enumerate(lines):
        code = _strip_line_comment(line)
        for var_name in unsigned_vars:
            if re.search(rf"\bTO\s+{re.escape(var_name)}\s*-\s*1\b", code):
                if not _unsigned_length_guarded(lines, line_index, var_name):
                    issues.append(
                        f"{path}:{line_index + 1}: unsigned length loop upper bound must be guarded before subtracting 1."
                    )
    return issues


def _lint_enum_values(path: str, family: str, content: str) -> list[str]:
    issues: list[str] = []
    if family != "enum" or not _looks_like_complete_object(family, content):
        return issues

    enum_match = re.search(
        r"TYPE\s+\w+\s*:\s*\((?P<body>.*?)\)\s*(?P<base>BYTE|WORD|DWORD|INT|DINT|UINT|UDINT)?\s*;",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not enum_match:
        return issues

    base_type = (enum_match.group("base") or "INT").upper()
    prefix = {"BYTE": "by", "WORD": "w", "DWORD": "dw"}.get(base_type, "i")
    for value_match in re.finditer(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:=", enum_match.group("body"), flags=re.MULTILINE):
        value_name = value_match.group(1)
        if not value_name.startswith(prefix):
            line = _line_number(content, enum_match.start("body") + value_match.start(1))
            issues.append(f"{path}:{line}: enum value '{value_name}' must use '{prefix}' prefix for {base_type}.")
    return issues


def lint_file_content(path: str, family: str, content: str, domain_tokens: Iterable[str] = ()) -> list[str]:
    issues: list[str] = []
    effective_family = family if family != "unknown" else infer_family(path, content)
    issues.extend(_lint_line_spacing(path, content))
    issues.extend(_lint_basic_format(path, effective_family, content))
    issues.extend(_lint_comment_encoding(path, content))
    issues.extend(_lint_comment_and_dependency_quality(path, content))
    issues.extend(_lint_public_object_names(path, content, domain_tokens))
    issues.extend(_lint_attributes(path, effective_family, content))
    issues.extend(_lint_file_header(path, effective_family, content))
    issues.extend(_lint_implementation_header(path, effective_family, content))
    issues.extend(_lint_engineering_implementation_comments(path, effective_family, content))
    issues.extend(_lint_variable_declaration_style(path, content))
    issues.extend(_lint_named_argument_call_style(path, content))
    issues.extend(_lint_enum_values(path, effective_family, content))
    if effective_family not in EXECUTABLE_FAMILIES:
        return issues
    issues.extend(_lint_fb_error_contract(path, effective_family, content))
    issues.extend(_lint_case_else(path, content))
    issues.extend(_lint_var_temp_fb_instances(path, content))
    issues.extend(_lint_empty_pins(path, content))
    issues.extend(_lint_real_equality(path, content))
    issues.extend(_lint_unsigned_minus_one_loop(path, content))
    return issues


def lint_manifest(skill_dir: Path, manifest: dict) -> SemanticLintResult:
    issues: list[str] = []
    checked_files = 0
    for bundle in manifest.get("bundles", []):
        for file_spec in bundle.get("files", []):
            file_path = skill_dir / "examples" / file_spec["path"]
            if not file_path.exists():
                continue
            content = file_path.read_text(encoding="utf-8")
            checked_files += 1
            issues.extend(lint_file_content(file_spec["path"], file_spec["family"], content))
    return SemanticLintResult(passed=not issues, issues=issues, checked_files=checked_files)


def _iter_project_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.st")):
        if any(part in EXCLUDED_PROJECT_DIRS for part in path.parts):
            continue
        yield path


def lint_project_root(root: Path) -> SemanticLintResult:
    issues: list[str] = []
    checked_files = 0
    root = root.resolve()
    domain_tokens = _domain_tokens_from_root(root)
    for file_path in _iter_project_files(root):
        content = file_path.read_text(encoding="utf-8")
        relative_path = file_path.relative_to(root).as_posix()
        checked_files += 1
        issues.extend(lint_file_content(relative_path, infer_family(file_path, content), content, domain_tokens))
    return SemanticLintResult(passed=not issues, issues=issues, checked_files=checked_files)


def _write_report(path: Path, root: Path, result: SemanticLintResult) -> None:
    report = {
        "root": str(root),
        "checked_files": result.checked_files,
        "issue_count": len(result.issues),
        "passed": result.passed,
        "issues": result.issues,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="CODESYS ST semantic and style gate.")
    parser.add_argument("--root", type=Path, help="Scan all .st files under a CODESYS mirror project root.")
    parser.add_argument("--output", type=Path, help="Write a JSON report.")
    parser.add_argument("--strict", action="store_true", help="Reserved for fail-closed project review gates.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    if args.root is not None:
        result = lint_project_root(args.root)
        if args.output is not None:
            _write_report(args.output, args.root, result)
    else:
        manifest = json.loads((skill_dir / "examples" / "example_manifest.json").read_text(encoding="utf-8"))
        result = lint_manifest(skill_dir, manifest)
        if args.output is not None:
            _write_report(args.output, skill_dir / "examples", result)

    if result.passed:
        print(f"semantic linter passed; checked_files={result.checked_files}")
        return 0
    for issue in result.issues:
        print(issue)
    print(f"semantic linter failed; checked_files={result.checked_files}; issue_count={len(result.issues)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
