from __future__ import annotations

import json
from pathlib import Path

from scac_harness.scenarios.archive import archive_calibration


def test_calibration_archive_is_write_once(tmp_path: Path) -> None:
    record = archive_calibration(tmp_path, "example", {"seed": 1}, [{"turn": 0}])
    assert record.parent.name == "example"
    assert json.loads((record / "manifest.json").read_text()) == {"seed": 1}
    assert json.loads((record / "trajectory.json").read_text()) == [{"turn": 0}]


def test_calibration_namespace_rejects_path_like_scenario(tmp_path: Path) -> None:
    try:
        archive_calibration(tmp_path, "../toolroute", {}, [])
    except ValueError:
        pass
    else:
        raise AssertionError("artifact namespace must not permit a path")
