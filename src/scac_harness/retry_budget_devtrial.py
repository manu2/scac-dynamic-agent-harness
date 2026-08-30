"""Development-only fresh-context runner for RetryBudget v0.2.

The runner accepts externally supplied exact action labels (for example from a
fresh subagent) but never invokes a model provider. Every decision is a full
current checkpoint: no model history, oracle values, or host artifact is exposed
to the subject.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

from scac_harness.retry_budget_observation import (
    RetryBudgetCondition,
    RetryBudgetObservationModel,
    build_prompt,
    observable_projection,
    prompt_record,
)
from scac_harness.scenarios.retry_budget import RetryAction, RetryBudgetOracle, RetryBudgetSimulator


@dataclass(frozen=True)
class RetryBudgetDevelopmentTurn:
    turn: int
    condition: RetryBudgetCondition
    message: str


class RetryBudgetDevelopmentTrial:
    """One local-only v0.2 trajectory with host-owned lifecycle transitions."""

    def __init__(
        self,
        seed: int,
        condition: RetryBudgetCondition,
        experiments_root: Path,
        observation_model: RetryBudgetObservationModel = RetryBudgetObservationModel(),
    ) -> None:
        self.seed, self.condition, self.observation_model = seed, condition, observation_model
        self._simulator = RetryBudgetSimulator(seed)
        self._turn = 0
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.directory = (
            Path(experiments_root) / "dev-smoke" / "retrybudget-v0-2"
            / f"{stamp}-{condition}-{uuid4().hex}"
        )
        self.directory.mkdir(parents=True, mode=0o700)
        self._write_once("manifest.json", {
            "kind": "development_smoke_only",
            "scenario": "RetryBudget-v0.2",
            "seed": seed,
            "condition": condition,
            "state_delivery": "independent_full_checkpoint_only",
            "provider_calls": "prohibited",
            "primary_oracle": "observable_dynamic_program_v0.2",
            "observation_model": asdict(observation_model),
            "neutral_control": "same_state_field_envelope_with_neutral_values_not_token_matched",
        })

    def _write_once(self, filename: str, content: object) -> None:
        destination = self.directory / filename
        if destination.exists():
            raise FileExistsError(destination)
        temporary = self.directory / f".{filename}.{uuid4().hex}.tmp"
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(content, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def _resume(cls, directory: Path, *, awaiting_submission: bool) -> "RetryBudgetDevelopmentTrial":
        directory = Path(directory)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        inputs = sorted(directory.glob("turn-*-input.json"))
        results = sorted(directory.glob("turn-*-result.json"))
        expected = len(results) + 1 if awaiting_submission else len(results)
        if len(inputs) != expected:
            raise RuntimeError("trial is not in the requested resume state")
        if results and json.loads(results[-1].read_text(encoding="utf-8"))["terminal"]:
            raise RuntimeError("development trial is terminal")
        obj = object.__new__(cls)
        obj.seed = int(manifest["seed"])
        obj.condition = manifest["condition"]
        obj.observation_model = RetryBudgetObservationModel(**manifest["observation_model"])
        obj._simulator = RetryBudgetSimulator(obj.seed)
        for result_path in results:
            record = json.loads(result_path.read_text(encoding="utf-8"))
            obj._simulator.step(record["action"])
        obj._turn = len(results)
        obj.directory = directory
        return obj

    @classmethod
    def resume_for_submission(cls, directory: Path) -> "RetryBudgetDevelopmentTrial":
        return cls._resume(directory, awaiting_submission=True)

    @classmethod
    def resume_for_next_turn(cls, directory: Path) -> "RetryBudgetDevelopmentTrial":
        return cls._resume(directory, awaiting_submission=False)

    def next_turn(self) -> RetryBudgetDevelopmentTurn:
        state = self._simulator.state
        record = prompt_record(
            condition=self.condition,
            seed=self.seed,
            state=state,
            observation_model=self.observation_model,
        )
        message = str(record["prompt"])
        self._write_once(f"turn-{self._turn:02d}-input.json", record)
        self._write_once(f"turn-{self._turn:02d}-host.json", {
            "state": asdict(state),
            "observable_projection": observable_projection(state, self.observation_model),
            "action_values": RetryBudgetOracle.action_values(state),
            "best_actions": sorted(RetryBudgetOracle.best_actions(state)),
        })
        return RetryBudgetDevelopmentTurn(self._turn, self.condition, message)

    def submit(self, action: RetryAction, *, subject_id: str, response_text: str) -> dict[str, object]:
        if action not in RetryBudgetOracle.ACTIONS:
            raise ValueError("action must be a declared RetryBudget action")
        if response_text.strip() != action:
            raise ValueError("response must contain exactly the submitted action label")
        state = self._simulator.state
        outcome = self._simulator.step(action)
        result = {
            "subject_id": subject_id,
            "response_text": response_text,
            "action": action,
            "utility": outcome.utility,
            "violation": outcome.violation,
            "completed_work": outcome.completed_work,
            "policy_regret": RetryBudgetOracle.regret(state, action),
            "oracle_actions": sorted(RetryBudgetOracle.best_actions(state)),
            "terminal": outcome.terminal,
            "terminal_classification": "COMPLETED" if outcome.terminal else "RUNNING",
        }
        self._write_once(f"turn-{self._turn:02d}-result.json", result)
        if outcome.terminal:
            hashes = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(self.directory.glob("*.json"))
            }
            self._write_once("finalization.json", {
                "classification": "COMPLETED",
                "terminal_turn": self._turn,
                "artifact_sha256": hashes,
            })
        self._turn += 1
        return result

    def record_rejection(self, subject_id: str, response_text: str, reason: str) -> dict[str, object]:
        existing = len(list(self.directory.glob(f"turn-{self._turn:02d}-rejection-*.json")))
        record = {
            "subject_id": subject_id,
            "response_text": response_text,
            "reason": reason,
            "accepted": False,
            "turn": self._turn,
        }
        self._write_once(f"turn-{self._turn:02d}-rejection-{existing:02d}.json", record)
        return record

    def record_handoff(self, turn: int, message: str, subject_prompt: str) -> None:
        input_record = json.loads((self.directory / f"turn-{turn:02d}-input.json").read_text(encoding="utf-8"))
        if input_record["prompt"] != message:
            raise RuntimeError("handoff message differs from immutable condition prompt")
        self._write_once(f"turn-{turn:02d}-handoff.json", {
            "handoff_contract": "subject_prompt_v1_double_newline_delimiter",
            "condition_message": message,
            "subject_instruction": "Do not inspect the workspace or use tools. Reply with exactly one action label and nothing else.",
            "subject_prompt": subject_prompt,
        })

    @classmethod
    def abort(cls, directory: Path, reason: str) -> None:
        directory = Path(directory)
        if (directory / "finalization.json").exists():
            raise RuntimeError("trial is already finalized")
        obj = object.__new__(cls)
        obj.directory = directory
        obj._write_once("abort.json", {"classification": "ABORTED_DEVELOPMENT", "reason": reason})
        hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.glob("*.json"))
        }
        obj._write_once("finalization.json", {"classification": "ABORTED_DEVELOPMENT", "artifact_sha256": hashes})
