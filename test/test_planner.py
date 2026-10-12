from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from planner import evaluate_request
from protocol_validator import validate_example_manifest


class PlannerTests(unittest.TestCase):
    def test_rejects_top_level_name_with_extra_underscores(self) -> None:
        result = evaluate_request(
            {
                "request_id": "REQ-BAD-NAME",
                "target_platform": "CODESYS / CODESYS V3.5",
                "object_family": "FUNCTION_BLOCK",
                "object_name": "FB_JSON_ToStruct",
                "functional_description": "JSON 解析功能块。",
                "delivery_mode": "codesys_text",
            }
        )

        self.assertEqual(result.status, "clarify")
        self.assertTrue(any("no extra underscores" in item for item in result.clarifications))

    def test_rejects_child_name_with_extra_underscores(self) -> None:
        result = evaluate_request(
            {
                "request_id": "REQ-BAD-CHILD-NAME",
                "target_platform": "CODESYS / CODESYS V3.5",
                "object_family": "FUNCTION_BLOCK",
                "object_name": "FB_JsonParser",
                "functional_description": "JSON 解析功能块。",
                "delivery_mode": "codesys_text",
                "child_objects": {
                    "methods": [{"name": "M_Parse_JSON"}],
                    "actions": [],
                    "properties": [],
                },
            }
        )

        self.assertEqual(result.status, "clarify")
        self.assertTrue(any("no extra underscores" in item for item in result.clarifications))

    def test_allows_mirror_mode_when_child_objects_are_requested(self) -> None:
        result = evaluate_request(
            {
                "request_id": "REQ-001",
                "target_platform": "CODESYS / CODESYS V3.5",
                "object_family": "FUNCTION_BLOCK",
                "object_name": "FB_WinderControl",
                "functional_description": "卷绕张力控制功能块。",
                "delivery_mode": "codesys_text",
                "io": {
                    "inputs": [{"name": "bEnable", "type": "BOOL"}],
                    "outputs": [{"name": "bDone", "type": "BOOL"}],
                },
                "child_objects": {
                    "methods": [{"name": "M_Init"}],
                    "actions": [{"name": "A_Reset"}],
                    "properties": [{"name": "P_Status", "type": "DINT", "accessors": ["GET", "SET"]}],
                },
            }
        )

        self.assertEqual(result.status, "recommend")
        self.assertEqual(result.blocking_reasons, [])

    def test_recommends_single_parent_file_with_mirror_segments(self) -> None:
        result = evaluate_request(
            {
                "request_id": "REQ-002",
                "target_platform": "CODESYS / CODESYS V3.5",
                "object_family": "FUNCTION_BLOCK",
                "object_name": "FB_MotorController",
                "functional_description": "伺服电机控制功能块，支持启停、故障复位和目标速度读写。",
                "delivery_mode": "codesys_text",
                "io": {
                    "inputs": [
                        {"name": "bEnable", "type": "BOOL"},
                        {"name": "iTargetSpeed", "type": "INT"},
                    ],
                    "outputs": [{"name": "bRunning", "type": "BOOL"}],
                },
                "child_objects": {
                    "methods": [{"name": "M_Init"}, {"name": "M_ValidateSpeed"}],
                    "actions": [{"name": "A_ResetFault"}],
                    "properties": [
                        {"name": "P_TargetSpeed", "type": "INT", "accessors": ["GET", "SET"]}
                    ],
                },
            }
        )

        manifest_files = [artifact["path"] for artifact in result.artifacts if artifact["type"] == "st_file"]
        segment_artifacts = [artifact for artifact in result.artifacts if artifact["type"] == "mirror_segments"]
        contract_artifacts = [artifact for artifact in result.artifacts if artifact["type"] == "generation_contract"]

        self.assertEqual(result.status, "recommend")
        self.assertEqual(manifest_files, ["FB_MotorController.st"])
        self.assertEqual(contract_artifacts[0]["contract"]["file_name"], "FB_MotorController.st")
        self.assertTrue(contract_artifacts[0]["contract"]["implementation_comment_contract"]["required"])
        self.assertTrue(contract_artifacts[0]["contract"]["rename_policy"]["final_name_before_write"])
        self.assertEqual(
            segment_artifacts[0]["segments"],
            [
                {"kind": "METHOD", "name": "M_Init"},
                {"kind": "METHOD", "name": "M_ValidateSpeed"},
                {"kind": "ACTION", "name": "A_ResetFault"},
                {"kind": "PROPERTY", "name": "P_TargetSpeed", "accessors": ["GET", "SET"]},
            ],
        )

    def test_example_manifest_is_release_ready(self) -> None:
        skill_dir = Path(__file__).resolve().parents[1]
        manifest = json.loads((skill_dir / "examples" / "example_manifest.json").read_text(encoding="utf-8"))

        result = validate_example_manifest(skill_dir, manifest)

        self.assertTrue(result.passed, result.issues)
        self.assertEqual(result.issues, [])


if __name__ == "__main__":
    unittest.main()
