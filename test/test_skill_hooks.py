from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SkillHookTests(unittest.TestCase):
    def test_skill_supports_review_without_tools(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("没有工具时也必须完成规范审查", skill)
        self.assertIn("脚本未执行", skill)
        self.assertIn("自然语言输入即可", skill)

    def test_review_scope_and_evidence_boundaries_are_explicit(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("完整项目 review 时必须全量扫描", skill)
        self.assertIn("脚本只在用户选择", skill)
        self.assertIn("不能声称全项目通过", skill)
        self.assertIn("offline_pou_logic_verified", skill)

    def test_no_external_execution_requirement(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("不强制联动任何其他技能", skill)
        self.assertIn("不自动记录外部记忆", skill)
        self.assertIn("未知接口不能编造", skill)

    def test_mandatory_manifest_is_self_contained(self) -> None:
        manifest = json.loads((ROOT / "references/mandatory-read-manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["fail_closed"])
        for item in manifest["mandatory_read_order"]:
            self.assertEqual(Path(item["path"]).suffix, ".md")
            self.assertTrue((ROOT / item["path"]).is_file())
            self.assertNotIn("..", Path(item["path"]).parts)
        self.assertFalse(manifest["optional_review_gate"]["required"])


if __name__ == "__main__":
    unittest.main()
