"""Check the exact, tool-independent public file set using the standard library."""
from __future__ import annotations

import argparse
import json
import re
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

PUBLIC_FILES = (
    "SKILL.md", "README.md", "README.zh-CN.md", "LICENSE", "requirements.txt", "config.yaml",
    "command.yaml", "test-prompts.json", "deploy/README.md",
    "docs/product-contract.md", "docs/golden-sample-policy.md",
    "docs/离线POU测试规则.md",
)
PUBLIC_DIRS = ("assets", "docs/images", "rules", "references", "templates", "examples", "scripts", "test", "evals")
PUBLIC_IMAGE_FILES = {"docs/images/cover-en.png", "docs/images/cover-zh.png"} | {
    f"docs/images/rule-{number:02}-{language}{layout}.png"
    for number in range(1, 9) for language in ("en", "zh") for layout in ("", "-mobile")
}
SKIP_PARTS = {"__pycache__", ".pytest_cache", "output", ".git"}
PRIVATE_PATH = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:Users|home)/[A-Za-z0-9_.-]+/)")
PRIVATE_IP = re.compile(r"\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b")
CREDENTIAL = re.compile(r"(?:AKIA[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY)")
SECRET_ASSIGNMENT = re.compile(r'''(?i)(?:password|passwd|api_key|apikey|client_secret|access_token)\s*[:=]\s*["'][^"']{6,}["']''')
INTERNAL_MARKERS = (
    "cr-" + "motion-expert", "cr-" + "codesys-cli", "st-" + "graph",
    "llm-" + "synchronizer", "cr-" + "synchronizer-st-expert",
    "Lic" + "OS", "evolve-" + "anything", "ai-" + "workspace",
)


@dataclass
class PublicAssetResult:
    passed: bool
    issues: list[str] = field(default_factory=list)


def public_files(root: Path) -> list[Path]:
    root = root.resolve()
    files = [root / rel for rel in PUBLIC_FILES]
    for rel in PUBLIC_DIRS:
        directory = root / rel
        if not directory.is_dir():
            raise ValueError(f"missing public directory: {rel}")
        files.extend(p for p in directory.rglob("*") if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_PARTS))
    for path in files:
        if not path.is_file():
            raise ValueError(f"missing public file: {path.relative_to(root)}")
        if path.is_symlink():
            raise ValueError(f"public symlink forbidden: {path.relative_to(root)}")
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError("public file escapes package root") from exc
    return sorted(set(files), key=lambda p: p.relative_to(root).as_posix())


def check_public_assets(root: Path) -> PublicAssetResult:
    issues: list[str] = []
    try:
        files = public_files(root)
    except ValueError as exc:
        return PublicAssetResult(False, [str(exc)])
    for path in files:
        rel = path.relative_to(root.resolve()).as_posix()
        if path.suffix.lower() == ".png":
            if rel not in PUBLIC_IMAGE_FILES:
                issues.append(f"{rel}: unapproved image path")
                continue
            data = path.read_bytes()
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                issues.append(f"{rel}: invalid PNG signature")
                continue
            cursor = 8
            chunks = []
            metadata = []
            try:
                while cursor < len(data):
                    size = struct.unpack_from(">I", data, cursor)[0]
                    kind = data[cursor + 4:cursor + 8]
                    payload = data[cursor + 8:cursor + 8 + size]
                    stored_crc = struct.unpack_from(">I", data, cursor + 8 + size)[0]
                    if len(payload) != size or zlib.crc32(kind + payload) & 0xFFFFFFFF != stored_crc:
                        raise ValueError("invalid PNG chunk")
                    chunks.append(kind)
                    if kind == b"IHDR":
                        width, height = struct.unpack_from(">II", payload)
                        if not (0 < width <= 10000 and 0 < height <= 20000):
                            raise ValueError("invalid PNG dimensions")
                    if kind in {b"tEXt", b"iTXt", b"eXIf"}:
                        metadata.append(payload.decode("utf-8", errors="ignore"))
                    if kind == b"zTXt":
                        keyword, packed = payload.split(b"\0", 1)
                        if not packed or packed[0] != 0:
                            raise ValueError("invalid PNG text compression")
                        metadata.append(keyword.decode("utf-8", errors="ignore") + zlib.decompress(packed[1:]).decode("utf-8", errors="ignore"))
                    cursor += 12 + size
                if chunks[:1] != [b"IHDR"] or chunks[-1:] != [b"IEND"] or b"IDAT" not in chunks or cursor != len(data):
                    raise ValueError("invalid PNG structure")
            except (ValueError, struct.error, zlib.error):
                issues.append(f"{rel}: invalid PNG structure")
                continue
            text = "\n".join(metadata)
        else:
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                issues.append(f"{rel}: invalid UTF-8")
                continue
        if chr(0xFFFD) in text:
            issues.append(f"{rel}: replacement character")
        for pattern, label in [(PRIVATE_PATH, "machine path"), (PRIVATE_IP, "private IP"), (CREDENTIAL, "credential"), (SECRET_ASSIGNMENT, "secret assignment")]:
            for number, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    issues.append(f"{rel}:{number}: {label}")
        for marker in INTERNAL_MARKERS:
            if marker.casefold() in text.casefold():
                issues.append(f"{rel}: internal dependency marker")
    return PublicAssetResult(not issues, issues)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = check_public_assets(args.root)
    print(json.dumps({"passed": result.passed, "issues": result.issues}, ensure_ascii=False, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
