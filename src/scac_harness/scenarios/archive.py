"""Write-once archival for deterministic, no-provider G2 calibrations."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4


def archive_calibration(
    experiments_root: Path,
    scenario: str,
    manifest: dict[str, object],
    trajectory: list[dict[str, object]],
) -> Path:
    """Atomically reserve and archive one deterministic calibration trajectory."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", scenario):
        raise ValueError("scenario must be a lowercase artifact namespace")
    parent = Path(experiments_root) / "g2-calibrations" / scenario
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = parent / f"{stamp}-{scenario}-{uuid4().hex}"
    directory.mkdir(mode=0o700)
    for filename, value in (("manifest.json", manifest), ("trajectory.json", trajectory)):
        with (directory / filename).open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    # Provider trajectories already use a terminal hash manifest. G2
    # calibrations must have the same tamper-evident closeout so a later review
    # can distinguish a complete calibration from an interrupted write.
    artifact_hashes = {
        filename: hashlib.sha256((directory / filename).read_bytes()).hexdigest()
        for filename in ("manifest.json", "trajectory.json")
    }
    with (directory / "finalization.json").open("x", encoding="utf-8") as handle:
        json.dump({"classification": "COMPLETED", "artifact_sha256": artifact_hashes}, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return directory
