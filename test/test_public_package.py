from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from public_asset_guard import check_public_assets, public_files
from build_public_package import build_package


class PublicPackageTests(unittest.TestCase):
    def test_corrupt_public_image_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skill"
            for p in public_files(ROOT):
                target = root / p.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, target)
            (root / "docs/images/cover-en.png").write_bytes(b"not a PNG")
            result = check_public_assets(root)
            self.assertFalse(result.passed)
            self.assertTrue(any("invalid PNG signature" in issue for issue in result.issues))

    def test_public_set_excludes_private_state(self) -> None:
        paths = {p.relative_to(ROOT).as_posix() for p in public_files(ROOT)}
        self.assertIn("SKILL.md", paths)
        self.assertIn("README.zh-CN.md", paths)
        self.assertIn("LICENSE", paths)
        self.assertFalse(any(p.startswith(("output/", ".git/", "evolution/")) for p in paths))
        self.assertFalse(any("TODO" in p for p in paths))

    def test_sensitive_text_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skill"
            for p in public_files(ROOT):
                target = root / p.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, target)
            samples = [
                "X:" + chr(92) + "Users" + chr(92) + "Example",
                ".".join(["192", "168", "7", "9"]),
                "sk-" + "x" * 24,
                "password" + " = " + chr(34) + "sensitive-value" + chr(34),
            ]
            for sample in samples:
                with self.subTest(sample_type=samples.index(sample)):
                    (root / "README.md").write_text(sample, encoding="utf-8")
                    self.assertFalse(check_public_assets(root).passed)

    def test_package_has_matching_hashes_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "skill.zip"
            manifest = build_package(ROOT, output)
            self.assertEqual(manifest["package_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(len(archive.namelist()), manifest["file_count"])
                for item in manifest["files"]:
                    data = archive.read("cr-st-expert/" + item["path"])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            with self.assertRaises(FileExistsError):
                build_package(ROOT, output)


if __name__ == "__main__":
    unittest.main()
