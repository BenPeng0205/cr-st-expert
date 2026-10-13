from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from repository_consistency import check_repository


class RepositoryConsistencyTests(unittest.TestCase):
    def test_teaching_counterexample_does_not_exempt_after_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "```st before\nVAR_INPUT\n    enable : BOOL;\nEND_VAR\n```\n"
                "```st\nVAR_OUTPUT\n    error : BOOL;\nEND_VAR\n```\n",
                encoding="utf-8",
            )
            result = check_repository(root)
        self.assertFalse(any("variable 'enable'" in i for i in result.issues))
        self.assertTrue(any("variable 'error'" in i for i in result.issues))

    def test_rejects_stale_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("> 更新日期: 2000-01-01\n", encoding="utf-8")
            result = check_repository(root)
        self.assertTrue(any("stale version/time metadata" in i for i in result.issues))

    def test_rejects_tab(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SKILL.md").write_text("a\tb\n", encoding="utf-8")
            result = check_repository(root)
        self.assertTrue(any("Tab is forbidden" in i for i in result.issues))

    def test_valid_minimal_repo_needs_no_external_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SKILL.md").write_text("# Standalone rules\n", encoding="utf-8")
            self.assertTrue(check_repository(root).passed)

    def test_reference_control_statement_needs_semicolon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("```st\nIF bEnable THEN\nEND_IF\n```\n", encoding="utf-8")
            result = check_repository(root)
        self.assertTrue(any("control statement terminator" in i for i in result.issues))

    def test_deployment_docs_are_checked_for_user_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "deploy").mkdir()
            sample = "X:" + chr(92) + "Users" + chr(92) + "Example" + chr(92) + "skills"
            (root / "deploy/README.md").write_text(sample, encoding="utf-8")
            result = check_repository(root)
        self.assertTrue(any("non-portable local path" in i for i in result.issues))

    def test_rejects_plcopen_style_names_in_markdown_st_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "FUNCTION_BLOCK FB_Test\nVAR_INPUT\n"
                "    Execute : BOOL := FALSE; // command\nEND_VAR\n"
                "VAR_OUTPUT\n    ErrorID : DINT; // error\nEND_VAR\n",
                encoding="utf-8",
            )
            result = check_repository(root)
        self.assertTrue(any("variable 'Execute' should use 'b' prefix" in i for i in result.issues))
        self.assertTrue(any("variable 'ErrorID' should use 'di' prefix" in i for i in result.issues))


if __name__ == "__main__":
    unittest.main()
