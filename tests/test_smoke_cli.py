from __future__ import annotations

import json
from pathlib import Path

from scac_harness.smoke_cli import main


def test_cli_start_submit_and_next(tmp_path: Path, capsys: object) -> None:
    assert main(["start", "--seed", "4", "--condition", "A", "--experiments-root", str(tmp_path)]) == 0
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert main(["submit", "--trial-dir", output["trial_dir"], "--subject-id", "fresh-1", "--response", "wait"]) == 0
    capsys.readouterr()  # type: ignore[attr-defined]
    assert main(["next", "--trial-dir", output["trial_dir"]]) == 0
    assert json.loads(capsys.readouterr().out)["turn"] == 1  # type: ignore[attr-defined]
