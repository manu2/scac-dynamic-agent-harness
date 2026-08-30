"""Command-line handoff interface for development-only fresh-agent smoke runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from scac_harness.devtrial import ToolRouteDevelopmentTrial

_HANDOFF_INSTRUCTION = (
    "Do not inspect the workspace or use tools. "
    "Reply with exactly one action label and nothing else."
)
_HANDOFF_DELIMITER = "\n\n"


def _emit(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _handoff_payload(trial: ToolRouteDevelopmentTrial, turn: object) -> dict[str, object]:
    """Freeze the exact fresh-subject handoff outside the condition message."""
    message = turn.message  # type: ignore[attr-defined]
    subject_prompt = message + _HANDOFF_DELIMITER + _HANDOFF_INSTRUCTION
    trial.record_handoff(turn.turn, message, subject_prompt)  # type: ignore[attr-defined]
    return {
        "trial_dir": str(trial.directory),
        "turn": turn.turn,  # type: ignore[attr-defined]
        "message": message,
        "subject_prompt": subject_prompt,
        "handoff_contract": "subject_prompt_v1_double_newline_delimiter",
    }


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
    abort = subparsers.add_parser("abort")
    abort.add_argument("--trial-dir", required=True)
    abort.add_argument("--reason", required=True)
    args = parser.parse_args(argv)

    if args.command == "start":
        trial = ToolRouteDevelopmentTrial(args.seed, args.condition, Path(args.experiments_root))
        turn = trial.next_turn()
        _emit(_handoff_payload(trial, turn))
    elif args.command == "submit":
        response = args.response.strip()
        trial = ToolRouteDevelopmentTrial.resume_for_submission(Path(args.trial_dir))
        if response not in {"tool_alpha", "tool_beta", "wait"}:
            _emit(trial.record_rejection(args.subject_id, args.response, "response_is_not_exact_action_label"))
            return 2
        _emit(trial.submit(response, subject_id=args.subject_id, response_text=args.response))
    elif args.command == "next":
        trial = ToolRouteDevelopmentTrial.resume_for_next_turn(Path(args.trial_dir))
        turn = trial.next_turn()
        _emit(_handoff_payload(trial, turn))
    else:
        ToolRouteDevelopmentTrial.abort(Path(args.trial_dir), args.reason)
        _emit({"trial_dir": args.trial_dir, "classification": "ABORTED_DEVELOPMENT"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
