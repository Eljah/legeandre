#!/usr/bin/env python3
"""Verify the exact source snapshot, without executing project code."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    manifest = ROOT / "provenance/SNAPSHOT_SHA256.json"
    if not manifest.is_file():
        print("INCOMPLETE: snapshot manifest is missing", file=sys.stderr)
        return 2
    data = json.loads(manifest.read_text(encoding="utf-8"))
    bad = []
    for entry in data["files"]:
        rel = Path(entry["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Unsafe manifest path")
        path = ROOT / rel
        if not path.is_file():
            bad.append((str(rel), "missing"))
        elif path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            bad.append((str(rel), "checksum mismatch"))
    for path, reason in bad[:30]:
        print(f"FAIL {reason}: {path}")
    total = len(data["files"])
    print(f"Verified {total - len(bad)}/{total} manifest entries")
    return 1 if bad else 0

if __name__ == "__main__":
    raise SystemExit(main())
