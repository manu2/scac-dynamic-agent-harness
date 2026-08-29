from __future__ import annotations

import json
from pathlib import Path

from scac_harness.smoke_cli import main


def test_cli_start_submit_and_next(tmp_path: Path, capsys: object) -> None:
    assert main(["start", "--seed", "4", "--condition", "A", "--experiments-root", str(tmp_path)]) == 0
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert output["subject_prompt"] == output["message"] + "\n\nDo not inspect the workspace or use tools. Reply with exactly one action label and nothing else."
    assert (Path(output["trial_dir"]) / "turn-00-handoff.json").exists()
    assert main(["submit", "--trial-dir", output["trial_dir"], "--subject-id", "fresh-1", "--response", "wait"]) == 0
    capsys.readouterr()  # type: ignore[attr-defined]
    assert main(["next", "--trial-dir", output["trial_dir"]]) == 0
    next_output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert next_output["turn"] == 1
    assert (Path(output["trial_dir"]) / "turn-01-handoff.json").exists()


def test_cli_retains_malformed_response(tmp_path: Path, capsys: object) -> None:
    main(["start", "--seed", "4", "--condition", "A", "--experiments-root", str(tmp_path)])
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert main(["submit", "--trial-dir", output["trial_dir"], "--subject-id", "fresh-1", "--response", "- tool_alpha"]) == 2
    rejected = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert rejected["accepted"] is False and rejected["response_text"] == "- tool_alpha"


def test_cli_abort_finalizes_partial_attempt(tmp_path: Path, capsys: object) -> None:
    main(["start", "--seed", "4", "--condition", "A", "--experiments-root", str(tmp_path)])
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert main(["abort", "--trial-dir", output["trial_dir"], "--reason", "revision"]) == 0
    assert json.loads(capsys.readouterr().out)["classification"] == "ABORTED_DEVELOPMENT"  # type: ignore[attr-defined]
