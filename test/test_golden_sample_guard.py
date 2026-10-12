from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from golden_sample_guard import validate_golden_manifest


class GoldenSampleGuardTests(unittest.TestCase):
    def test_rejects_manifest_without_verification_metadata(self) -> None:
        manifest = {
            "skill_name": "cr-st-expert",
            "bundles": [
                {
                    "bundle_id": "unsafe",
                    "description": "未验证样本",
                    "target_platform": "CODESYS / CODESYS V3.5",
                    "protocol": "codesys_st_text_v1",
                    "files": [],
                    "coverage": [],
                }
            ],
        }

        result = validate_golden_manifest(Path.cwd(), manifest)

        self.assertFalse(result.passed)
        self.assertTrue(any("verification_level" in issue for issue in result.issues))

    def test_rejects_candidate_file_in_golden_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp)
            (skill_dir / "examples" / "candidates").mkdir(parents=True)
            manifest = {
                "skill_name": "cr-st-expert",
                "bundles": [
                    {
                        "bundle_id": "candidate",
                        "description": "候选样本",
                        "target_platform": "CODESYS / CODESYS V3.5",
                        "protocol": "codesys_st_text_v1",
                        "verification_level": "protocol_gate",
                        "promotion_evidence": ["unit test"],
                        "files": [{"path": "candidates/FB_Draft.st", "family": "function_block"}],
                        "coverage": ["candidate"],
                    }
                ],
            }

            result = validate_golden_manifest(skill_dir, manifest)

        self.assertFalse(result.passed)
        self.assertTrue(any("must not be listed as golden sample" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
