from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


SUPPORTED_PLATFORMS = {"CODESYS / CODESYS V3.5"}
SUPPORTED_DELIVERY_MODES = {"codesys_text", "single_file"}
LEGACY_UNSUPPORTED_DELIVERY_MODES = {"multi_file"}
FAMILY_PREFIXES = {
    "FUNCTION_BLOCK": "FB_",
    "FUNCTION": "F_",
    "PROGRAM": "PRG_",
    "GVL": "GVL_",
    "ENUM": "E_",
    "STRUCT": "ST_",
}
NAME_PATTERNS = {
    "FUNCTION_BLOCK": re.compile(r"^FB_[A-Z][A-Za-z0-9]*$"),
    "FUNCTION": re.compile(r"^F_[A-Z][A-Za-z0-9]*$"),
    "PROGRAM": re.compile(r"^PRG_[A-Z][A-Za-z0-9]*$"),
    "GVL": re.compile(r"^GVL_[A-Z][A-Za-z0-9]*$"),
    "ENUM": re.compile(r"^E_[A-Z][A-Za-z0-9]*$"),
    "STRUCT": re.compile(r"^ST_[A-Z][A-Za-z0-9]*$"),
}
CHILD_NAME_PATTERNS = {
    "Method": re.compile(r"^M_[A-Z][A-Za-z0-9]*$"),
    "Action": re.compile(r"^A_[A-Z][A-Za-z0-9]*$"),
    "Property": re.compile(r"^P_[A-Z][A-Za-z0-9]*$"),
}
CHILD_OBJECT_PARENT_FAMILIES = {"FUNCTION_BLOCK"}
PROPERTY_ACCESSORS = ("GET", "SET")


@dataclass
class SkillResult:
    status: str
    summary: str
    clarifications: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    trace: list[dict[str, str]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "clarifications": self.clarifications,
            "blocking_reasons": self.blocking_reasons,
            "assumptions": self.assumptions,
            "trace": self.trace,
            "artifacts": self.artifacts,
        }


def _normalize_child_objects(raw: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    raw = raw or {}
    return {
        "methods": list(raw.get("methods") or []),
        "actions": list(raw.get("actions") or []),
        "properties": list(raw.get("properties") or []),
    }


def _has_child_objects(child_objects: dict[str, list[dict[str, Any]]]) -> bool:
    return any(child_objects.values())


def _validate_required_fields(request: dict[str, Any]) -> list[str]:
    missing = []
    for field_name in ("request_id", "target_platform", "object_family", "object_name", "delivery_mode"):
        if not request.get(field_name):
            missing.append(field_name)
    return missing


def _validate_name_prefix(object_family: str, object_name: str) -> str | None:
    prefix = FAMILY_PREFIXES.get(object_family)
    pattern = NAME_PATTERNS.get(object_family)
    if prefix and pattern and not pattern.fullmatch(object_name):
        return f"{object_family} object name must use {prefix}PascalCase with no extra underscores."
    return None


def _validate_child_object_prefixes(child_objects: dict[str, list[dict[str, Any]]]) -> list[str]:
    clarifications: list[str] = []

    for method in child_objects["methods"]:
        if not CHILD_NAME_PATTERNS["Method"].fullmatch(str(method.get("name", ""))):
            clarifications.append("Method name must use M_PascalCase with no extra underscores.")

    for action in child_objects["actions"]:
        if not CHILD_NAME_PATTERNS["Action"].fullmatch(str(action.get("name", ""))):
            clarifications.append("Action name must use A_PascalCase with no extra underscores.")

    for prop in child_objects["properties"]:
        prop_name = str(prop.get("name", ""))
        if not CHILD_NAME_PATTERNS["Property"].fullmatch(prop_name):
            clarifications.append("Property name must use P_PascalCase with no extra underscores.")

        accessors = prop.get("accessors") or []
        if list(accessors) != list(PROPERTY_ACCESSORS):
            clarifications.append(f"Property {prop_name or '<unknown>'} must declare accessors as ['GET', 'SET'].")

    return clarifications


def build_file_manifest(request: dict[str, Any]) -> list[str]:
    return [f"{request['object_name']}.st"]


def build_mirror_segments(child_objects: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    segments.extend({"kind": "METHOD", "name": method["name"]} for method in child_objects["methods"])
    segments.extend({"kind": "ACTION", "name": action["name"]} for action in child_objects["actions"])
    segments.extend(
        {
            "kind": "PROPERTY",
            "name": prop["name"],
            "accessors": list(prop.get("accessors") or []),
        }
        for prop in child_objects["properties"]
    )
    return segments


def build_generation_contract(request: dict[str, Any], segments: list[dict[str, Any]]) -> dict[str, Any]:
    object_name = request["object_name"]
    return {
        "protocol": "codesys_st_text_v1",
        "file_name": f"{object_name}.st",
        "object_name": object_name,
        "object_family": request["object_family"],
        "library_dependency": request.get("library_dependency") or "暂无",
        "segments": segments,
        "implementation_comment_contract": {
            "required": True,
            "scope": "关键逻辑、算法公式、状态转换、边界保护、异常兜底和平台适配点",
            "forbidden": "只复述代码或只保留对象头部说明",
        },
        "rename_policy": {
            "final_name_before_write": True,
            "forbid_patch_move_as_primary_path": True,
            "verify_file_exists_after_write": True,
        },
    }


def evaluate_request(request: dict[str, Any]) -> SkillResult:
    missing_fields = _validate_required_fields(request)
    if missing_fields:
        return SkillResult(
            status="clarify",
            summary="输入结构不完整，无法建立 CODESYS ST text 交付计划。",
            clarifications=[f"Missing required field: {field_name}" for field_name in missing_fields],
            trace=[{"step": "validate_input", "detail": "Required field check failed."}],
        )

    target_platform = request["target_platform"]
    object_family = request["object_family"]
    object_name = request["object_name"]
    delivery_mode = request["delivery_mode"]
    child_objects = _normalize_child_objects(request.get("child_objects"))

    if target_platform not in SUPPORTED_PLATFORMS:
        return SkillResult(
            status="block",
            summary="目标平台超出当前技能的生产边界。",
            blocking_reasons=[f"Unsupported target_platform: {target_platform}"],
            trace=[{"step": "validate_platform", "detail": "Target platform is not supported."}],
        )

    if delivery_mode in LEGACY_UNSUPPORTED_DELIVERY_MODES:
        return SkillResult(
            status="clarify",
            summary="可选规划脚本使用父对象聚合文本格式。",
            clarifications=[
                "Use delivery_mode=codesys_text for the bundled text format.",
                "Other file layouts can be reviewed directly by the AI; this optional planner handles aggregated text only.",
            ],
            trace=[{"step": "validate_delivery_mode", "detail": "Legacy multi_file mode rejected."}],
        )

    if delivery_mode not in SUPPORTED_DELIVERY_MODES:
        return SkillResult(
            status="clarify",
            summary="交付模式不在当前 CODESYS ST text 协议范围内。",
            clarifications=[f"Unsupported delivery_mode: {delivery_mode}"],
            trace=[{"step": "validate_delivery_mode", "detail": "Delivery mode is unknown."}],
        )

    if object_family not in FAMILY_PREFIXES:
        return SkillResult(
            status="clarify",
            summary="对象类型未落入当前技能支持范围。",
            clarifications=[f"Unsupported object_family: {object_family}"],
            trace=[{"step": "validate_object_family", "detail": "Object family is unknown."}],
        )

    if not request.get("functional_description") and object_family in {"FUNCTION_BLOCK", "FUNCTION", "PROGRAM"}:
        return SkillResult(
            status="clarify",
            summary="可执行对象缺少功能说明，无法稳定生成生产级代码。",
            clarifications=["functional_description is required for executable IEC objects."],
            trace=[{"step": "validate_business_boundary", "detail": "Functional description is missing."}],
        )

    prefix_issue = _validate_name_prefix(object_family, object_name)
    if prefix_issue:
        return SkillResult(
            status="clarify",
            summary="对象命名不符合技能命名规范。",
            clarifications=[prefix_issue],
            trace=[{"step": "validate_naming", "detail": "Top-level name prefix mismatch."}],
        )

    child_name_issues = _validate_child_object_prefixes(child_objects)
    if child_name_issues:
        return SkillResult(
            status="clarify",
            summary="子对象命名或访问器结构不符合 mirror 协议要求。",
            clarifications=child_name_issues,
            trace=[{"step": "validate_child_objects", "detail": "Child object naming or accessor rules failed."}],
        )

    if _has_child_objects(child_objects) and object_family not in CHILD_OBJECT_PARENT_FAMILIES:
        return SkillResult(
            status="block",
            summary="当前技能只允许 FUNCTION_BLOCK 承载 Method/Action/Property 聚合段。",
            blocking_reasons=[f"{object_family} cannot own child IEC objects in this skill contract."],
            trace=[{"step": "validate_parent_family", "detail": "Child objects on unsupported parent family."}],
        )

    manifest = build_file_manifest(request)
    segments = build_mirror_segments(child_objects)
    generation_contract = build_generation_contract(request, segments)
    artifacts: list[dict[str, Any]] = [
        {
            "type": "generation_contract",
            "path": f"{object_name}.st",
            "contract": generation_contract,
        },
        {
            "type": "file_manifest",
            "path": "generated_manifest",
            "files": manifest,
            "protocol": "codesys_st_text_v1",
        }
    ]
    artifacts.extend({"type": "st_file", "path": file_path} for file_path in manifest)
    if segments:
        artifacts.append(
            {
                "type": "mirror_segments",
                "path": f"{object_name}.st",
                "segments": segments,
            }
        )

    assumptions = [
        "The optional planner describes text organization only; no compilation or functional verification is performed.",
    ]
    if delivery_mode == "single_file":
        assumptions.append("delivery_mode=single_file is treated as one top-level IEC object per .st mirror file.")

    return SkillResult(
        status="recommend",
        summary="请求满足 CODESYS ST text 协议，可进入聚合 ST 文件生成阶段。",
        assumptions=assumptions,
        trace=[
            {"step": "validate_input", "detail": "Structured request passed required field checks."},
            {"step": "plan_manifest", "detail": "Generated one top-level IEC object file."},
            {"step": "plan_segments", "detail": "Aggregated child IEC objects into parent mirror segments."},
        ],
        artifacts=artifacts,
    )
