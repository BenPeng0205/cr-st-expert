from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VerificationBoundaryTests(unittest.TestCase):
    def test_static_review_cannot_claim_functional_verification(self) -> None:
        for rel in ["SKILL.md", "docs/离线POU测试规则.md"]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("offline_pou_logic_verified", text)
            self.assertIn("仿真", text)
            self.assertNotIn(chr(0xFFFD), text)

    def test_skill_has_no_required_test_project(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("不负责启动编译器或建立测试工程", text)
        self.assertNotIn("POUs/OfflineTest/", text)


if __name__ == "__main__":
    unittest.main()
