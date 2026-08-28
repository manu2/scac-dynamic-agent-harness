"""Offline A/B/C ToolRoute development runner for fresh-context smoke tests.

This module is deliberately labelled development-only. It accepts an externally
supplied action (for example from a fresh Codex subagent) but does not call a
model provider. The hidden fault tape never appears in A/B messages; C receives
only a host-derived reduced telemetry projection.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from scac_harness.events import RawTelemetryEvent
from scac_harness.reducer import DeterministicReducer
from scac_harness.renderer import render_tier2_envelope
from scac_harness.scenarios.toolroute import ToolHealth, ToolRouteOracle, ToolRouteState


Condition = Literal["A", "B", "C"]
Action = Literal["tool_alpha", "tool_beta", "wait"]


@dataclass(frozen=True)
class DevelopmentTurn:
    turn: int
    condition: Condition
    message: str
    state: ToolRouteState
    snapshot: dict[str, object] | None


class ToolRouteDevelopmentTrial:
    """One pre-pilot trajectory with a private deterministic potential-outcome tape."""

    def __init__(self, seed: int, condition: Condition, experiments_root: Path) -> None:
        self.seed = seed
        self.condition = condition
        self._turn = 0
        self._reducer = DeterministicReducer()
        self._prior_snapshot: dict[str, object] | None = None
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.directory = Path(experiments_root) / "dev-smoke" / f"{stamp}-toolroute-{condition}-{uuid4().hex}"
        self.directory.mkdir(parents=True, mode=0o700)
        self._write_once("manifest.json", {"kind": "development_smoke_only", "seed": seed, "condition": condition, "scenario": "ToolRoute-v0.1"})

    def _write_once(self, filename: str, content: object) -> None:
        with (self.directory / filename).open("x", encoding="utf-8") as handle:
            json.dump(content, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def _health(self) -> dict[str, ToolHealth]:
        return self._health_for(self.seed, self._turn)

    @staticmethod
    def _health_for(seed: int, turn: int) -> dict[str, ToolHealth]:
        # Regime assignment and each potential tool outcome are derived from
        # independent hashes. Action choice cannot advance or perturb this tape.
        regimes = ((0.98, 100), (0.20, 4200), (0.80, 800), (0.20, 4200))
        degraded_probability, degraded_latency = regimes[turn]
        rotate = int(hashlib.sha256(f"{seed}:regime:{turn}".encode()).hexdigest(), 16) % 2
        degraded, healthy = ("tool_alpha", "tool_beta") if rotate == 0 else ("tool_beta", "tool_alpha")
        return {
            degraded: ToolHealth(degraded_probability, degraded_latency, 2000 if degraded_probability <= 0.20 else None),
            healthy: ToolHealth(0.99, 180),
        }

    @classmethod
    def resume_for_submission(cls, directory: Path) -> ToolRouteDevelopmentTrial:
        """Reconstruct the action-submission state from immutable prior records."""
        directory = Path(directory)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        inputs = sorted(directory.glob("turn-*-input.json"))
        results = sorted(directory.glob("turn-*-result.json"))
        if len(inputs) != len(results) + 1:
            raise RuntimeError("trial is not awaiting exactly one action submission")
        obj = object.__new__(cls)
        obj.seed = int(manifest["seed"])
        obj.condition = manifest["condition"]
        obj._turn = len(results)
        obj._reducer = DeterministicReducer()
        obj._prior_snapshot = None
        obj.directory = directory
        return obj

    @classmethod
    def resume_for_next_turn(cls, directory: Path) -> ToolRouteDevelopmentTrial:
        """Resume only after a submitted action, restoring the prior SST snapshot."""
        directory = Path(directory)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        inputs = sorted(directory.glob("turn-*-input.json"))
        results = sorted(directory.glob("turn-*-result.json"))
        if len(inputs) != len(results) or not results:
            raise RuntimeError("trial is not ready to compile its next turn")
        turn = len(results)
        if turn >= 4:
            raise RuntimeError("development trial is terminal")
        host = json.loads((directory / f"turn-{turn - 1:02d}-host.json").read_text(encoding="utf-8"))
        obj = object.__new__(cls)
        obj.seed = int(manifest["seed"])
        obj.condition = manifest["condition"]
        obj._turn = turn
        obj._reducer = DeterministicReducer()
        obj._prior_snapshot = host["snapshot"]
        obj.directory = directory
        return obj

    def _telemetry(self, state: ToolRouteState) -> tuple[dict[str, object], str, list[dict[str, object]]]:
        events = []
        for index, (tool, health) in enumerate(sorted(state.health.items())):
            events.append(RawTelemetryEvent(
                timestamp_ms=(state.turn + 1) * 1000 + index,
                source="host_health_monitor",
                topic="tool_span",
                payload={"tool_id": tool, "latency_ms": health.latency_ms, "success": health.success_probability >= 0.9, "error_class": "HTTP_503", "retry_after_ms": health.retry_after_ms},
            ))
        observed_at_ms = (state.turn + 1) * 1000 + 1
        snapshot = self._reducer.reduce(
            trajectory_id=f"dev-smoke-{self.seed}", seq=state.turn,
            events=events, prior_snapshot=self._prior_snapshot,
            kind="full_checkpoint" if self._prior_snapshot is None else "delta",
            observed_at_ms=observed_at_ms,
        )
        self._prior_snapshot = snapshot
        return snapshot, render_tier2_envelope(snapshot), [event.to_dict() for event in events]

    @staticmethod
    def _task_text() -> str:
        return (
            "Task: retrieve the next required record. tool_alpha and tool_beta are functionally equivalent. "
            "Choose exactly one action: tool_alpha, tool_beta, or wait. Return only the action label.\n"
        )

    @staticmethod
    def _neutral_match(telemetry: str) -> str:
        prefix = "[NEUTRAL CONTROL]\n"
        # Fixed, opaque padding matches bytes without encoding tool health,
        # names, latency, error classes, probabilities, or instructions.
        return prefix + ("n" * max(0, len(telemetry.encode("utf-8")) - len(prefix.encode("utf-8"))))

    def next_turn(self) -> DevelopmentTurn:
        if self._turn >= 4:
            raise RuntimeError("development trial is terminal")
        state = ToolRouteState(self._turn, self._health())
        snapshot, telemetry, raw_events = self._telemetry(state)
        task = self._task_text()
        if self.condition == "A":
            message, visible_snapshot = task, None
        elif self.condition == "B":
            message, visible_snapshot = task + self._neutral_match(telemetry), None
        else:
            message, visible_snapshot = task + telemetry, snapshot
        turn = DevelopmentTurn(self._turn, self.condition, message, state, visible_snapshot)
        self._write_once(f"turn-{self._turn:02d}-input.json", {
            "condition": self.condition, "message": message,
            "message_bytes": len(message.encode("utf-8")),
            "visible_snapshot": visible_snapshot,
        })
        self._write_once(f"turn-{self._turn:02d}-host.json", {
            "raw_events": raw_events,
            "snapshot": snapshot,
            "rendered_telemetry": telemetry,
        })
        return turn

    def submit(self, action: Action, subject_id: str = "unspecified", response_text: str | None = None) -> dict[str, object]:
        if action not in {"tool_alpha", "tool_beta", "wait"}:
            raise ValueError("action must be tool_alpha, tool_beta, or wait")
        if response_text is not None and response_text.strip() != action:
            raise ValueError("response must contain exactly the submitted action label")
        state = ToolRouteState(self._turn, self._health())
        health = state.health.get(action)
        if health is None:
            success, latency, error = False, 500, None
        else:
            draw = int(hashlib.sha256(f"{self.seed}:outcome:{self._turn}:{action}".encode()).hexdigest(), 16) / 2**256
            success, latency, error = draw < health.success_probability, health.latency_ms, None
            if not success:
                error = "HTTP_503"
        result = {
            "subject_id": subject_id, "response_text": response_text, "action": action, "success": success, "latency_ms": latency,
            "error_class": error, "policy_regret": ToolRouteOracle.regret(state, action),
            "terminal": self._turn == 3,
        }
        self._write_once(f"turn-{self._turn:02d}-result.json", result)
        self._turn += 1
        return result
