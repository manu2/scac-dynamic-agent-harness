"""Terminally finalize one pre-generation ToolRoute reservation after a crash."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory
    if not (directory / "manifest.json").is_file() or (directory / "finalization.json").exists():
        raise RuntimeError("directory is not an unfinished ToolRoute reservation")
    if (directory / "provider-request.json").exists():
        raise RuntimeError("refusing to recover a reservation that reached provider-request capture")
    error_path = directory / "setup-error.json"
    error_path.write_text(json.dumps({
        "classification": "REJECTED_TOKEN_CONTROL_SETUP",
        "exception_type": "RecoveredInterruptedSetup",
        "reason": "native token-control construction terminated before prompt capture",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.glob("*.json"))}
    (directory / "finalization.json").write_text(json.dumps({
        "classification": "REJECTED_TOKEN_CONTROL_SETUP", "artifact_sha256": hashes,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
