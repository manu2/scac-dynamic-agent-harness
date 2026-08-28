from __future__ import annotations

import json
from pathlib import Path

from scac_harness.scenarios.archive import archive_calibration


def test_calibration_archive_is_write_once(tmp_path: Path) -> None:
    record = archive_calibration(tmp_path, "example", {"seed": 1}, [{"turn": 0}])
    assert json.loads((record / "manifest.json").read_text()) == {"seed": 1}
    assert json.loads((record / "trajectory.json").read_text()) == [{"turn": 0}]
