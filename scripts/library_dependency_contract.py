from __future__ import annotations

import re
from dataclasses import dataclass, field


DEPENDENCY_LABEL = "\u5e93\u4f9d\u8d56"
NO_LIBRARY_VALUE = "\u6682\u65e0"
DEPENDENCY_LINE_PATTERN = re.compile(
    r"^\s*///\s*" + re.escape(DEPENDENCY_LABEL) + r"\s*[:\uff1a]\s*(?P<value>.+?)\s*$",
    flags=re.MULTILINE,
)
VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+){1,5}$")
NO_LIBRARY_VALUES = {NO_LIBRARY_VALUE, "\u65e0", "none", "None", "N/A", "NA", "-"}
VERSION_POLICY_VALUES = {"installed", "project", "default"}

LIBRARY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_]+(?:[ .-][A-Za-z0-9_]+)*$")

ALIASES = {
    "Element Collections": "ElementCollections",
    "CAA Types Extern": "CAA Types",
}

SYMBOL_DEPENDENCY_RULES = (
    ("RecipeManagement", re.compile(r"\b(?:RecipeManagement|RecipeManCommands|RCP\.)\b")),
    ("SysTypes", re.compile(r"\bRTS_IEC_[A-Za-z0-9_]+\b")),
    ("SysMem", re.compile(r"\b(?:SysMem\.|SysMemCpy|SysMemMove)\b")),
    ("NBS", re.compile(r"\b(?:NBS\.|TCP_Client|TCP_Server|UDP_Peer)\b")),
    ("3SLicense", re.compile(r"\b__(?:CHECKLICENSE|CHECKLICENSEBIT)\b")),
    ("SM3_Basic", re.compile(r"\b(?:SM3_Basic|AXIS_REF_SM3|MC_POWER|MC_MOVEABSOLUTE|SMC_AXIS_STATE)\b", flags=re.IGNORECASE)),
    ("ElementCollections", re.compile(r"\b(?:ElementCollections|COL\.)\b")),
)


@dataclass
class DependencyParseResult:
    dependencies: list[dict[str, str]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    header_count: int = 0
    no_library_header_count: int = 0


def canonical_dependency_name(name: str) -> str:
    stripped = name.strip()
    return ALIASES.get(stripped, stripped)


def split_dependency_value(value: str) -> tuple[list[str], list[str]]:
    stripped = value.strip()
    if not stripped:
        return [], ["library dependency must not be empty; use \u6682\u65e0 when unknown."]
    if stripped in NO_LIBRARY_VALUES:
        return [], []
    if "," in stripped or "\uff0c" in stripped:
        return [], ["library dependency entries must use ';' and Library@Version, not CODESYS display text."]
    return [item.strip() for item in re.split(r"[;\uff1b]", stripped) if item.strip()], []


def parse_dependency_token(token: str) -> tuple[dict[str, str] | None, str | None]:
    raw = token.strip().strip("`")
    if not raw or raw in NO_LIBRARY_VALUES:
        return None, None
    if "(" in raw or ")" in raw:
        return None, "library dependency must use LibraryId or LibraryId@Version, not display resolution text."
    if raw.count("@") > 1:
        return None, "library dependency token can contain only one @ version separator."
    name = raw
    version = ""
    version_policy = ""
    if "@" in raw:
        name, version_text = raw.split("@", 1)
        name = name.strip()
        version_text = version_text.strip()
        if VERSION_PATTERN.fullmatch(version_text):
            version = version_text
        elif version_text.lower() in VERSION_POLICY_VALUES:
            version_policy = version_text.lower()
        else:
            return None, "library dependency version must be exact numeric, installed, project, or default."
    canonical = canonical_dependency_name(name)
    if not LIBRARY_ID_PATTERN.fullmatch(canonical):
        return None, "library dependency must use an explicit LibraryId, not a platform label or display text."
    return {"name": canonical, "version": version, "version_policy": version_policy, "raw": raw}, None


def parse_library_dependencies(content: str) -> DependencyParseResult:
    result = DependencyParseResult()
    versions_by_name: dict[str, set[str]] = {}
    for match in DEPENDENCY_LINE_PATTERN.finditer(content):
        result.header_count += 1
        value = match.group("value").strip()
        tokens, split_issues = split_dependency_value(value)
        result.issues.extend(split_issues)
        if not tokens:
            result.no_library_header_count += 1
            continue
        for token in tokens:
            item, issue = parse_dependency_token(token)
            if issue:
                result.issues.append(issue)
                continue
            if item is None:
                continue
            result.dependencies.append(item)
            if item["version"]:
                versions_by_name.setdefault(item["name"], set()).add(item["version"])
    for name, versions in sorted(versions_by_name.items()):
        if len(versions) > 1:
            result.issues.append(
                f"library dependency {name} declares conflicting exact versions: {', '.join(sorted(versions))}."
            )
    return result


def dependency_names(content: str) -> set[str]:
    return {item["name"] for item in parse_library_dependencies(content).dependencies}


def required_symbol_dependencies(content: str) -> set[str]:
    body = re.sub(r"//.*", "", content)
    required: set[str] = set()
    for name, pattern in SYMBOL_DEPENDENCY_RULES:
        if pattern.search(body):
            required.add(name)
    return required
