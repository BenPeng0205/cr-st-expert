"""Build a deterministic public ZIP without Git history or local reports."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from public_asset_guard import check_public_assets, public_files


def build_package(root: Path, output: Path) -> dict:
    root = root.resolve()
    output = output.resolve()
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    if output.exists() or manifest_path.exists():
        raise FileExistsError("package or manifest exists; refusing to overwrite")
    result = check_public_assets(root)
    if not result.passed:
        raise ValueError("public asset check failed: " + "; ".join(result.issues))
    entries = []
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in public_files(root):
            rel = path.relative_to(root).as_posix()
            data = path.read_bytes()
            info = zipfile.ZipInfo("cr-st-expert/" + rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
            entries.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    manifest = {
        "schema_version": 1,
        "package_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "file_count": len(entries),
        "files": entries,
        "release_eligibility": "NOT_RELEASE_ELIGIBLE",
    }
    with manifest_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = build_package(args.root, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
