from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from repository_consistency import check_repository


class StandaloneContractTests(unittest.TestCase):
    def test_repository_check_does_not_discover_external_skills(self) -> None:
        with patch("pathlib.Path.home", side_effect=AssertionError("external discovery forbidden")):
            result = check_repository(ROOT)
        self.assertTrue(result.passed, result.issues)

    def test_document_loading_requires_no_script(self) -> None:
        manifest = json.loads((ROOT / "references/mandatory-read-manifest.json").read_text(encoding="utf-8"))
        for item in manifest["mandatory_read_order"]:
            self.assertTrue((ROOT / item["path"]).is_file())
            self.assertEqual(Path(item["path"]).suffix, ".md")
        self.assertFalse(manifest["optional_review_gate"]["required"])

    def test_static_format_is_tool_neutral(self) -> None:
        from planner import evaluate_request

        request = json.loads((ROOT / "examples/request.json").read_text(encoding="utf-8"))
        result = evaluate_request(request)
        self.assertEqual(result.status, "recommend")
        contract = next(a["contract"] for a in result.artifacts if a["type"] == "generation_contract")
        self.assertEqual(contract["protocol"], "codesys_st_text_v1")

    def test_user_library_does_not_require_builtin_knowledge(self) -> None:
        from library_dependency_contract import parse_dependency_token

        dependency, issue = parse_dependency_token("Example_Control@1.2.3")
        self.assertIsNone(issue)
        self.assertEqual(dependency["name"], "Example_Control")
        numbered, numbered_issue = parse_dependency_token("3SLicense")
        self.assertIsNone(numbered_issue)
        self.assertEqual(numbered["name"], "3SLicense")

    def test_library_display_text_is_not_an_identifier(self) -> None:
        from library_dependency_contract import parse_dependency_token

        dependency, issue = parse_dependency_token("Example Library (Vendor)")
        self.assertIsNone(dependency)
        self.assertIsNotNone(issue)


if __name__ == "__main__":
    unittest.main()
