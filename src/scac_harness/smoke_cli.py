"""Command-line handoff interface for development-only fresh-agent smoke runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from scac_harness.devtrial import ToolRouteDevelopmentTrial


def _emit(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCAC development-only ToolRoute smoke runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("--seed", required=True, type=int)
    start.add_argument("--condition", required=True, choices=("A", "B", "C"))
    start.add_argument("--experiments-root", default="experiments")
    submit = subparsers.add_parser("submit")
    submit.add_argument("--trial-dir", required=True)
    submit.add_argument("--response", required=True)
    submit.add_argument("--subject-id", required=True)
    next_turn = subparsers.add_parser("next")
    next_turn.add_argument("--trial-dir", required=True)
    args = parser.parse_args(argv)

    if args.command == "start":
        trial = ToolRouteDevelopmentTrial(args.seed, args.condition, Path(args.experiments_root))
        turn = trial.next_turn()
        _emit({"trial_dir": str(trial.directory), "turn": turn.turn, "message": turn.message})
    elif args.command == "submit":
        response = args.response.strip()
        trial = ToolRouteDevelopmentTrial.resume_for_submission(Path(args.trial_dir))
        _emit(trial.submit(response, subject_id=args.subject_id, response_text=args.response))
    else:
        trial = ToolRouteDevelopmentTrial.resume_for_next_turn(Path(args.trial_dir))
        turn = trial.next_turn()
        _emit({"trial_dir": str(trial.directory), "turn": turn.turn, "message": turn.message})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
