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
import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

from scac_harness.events import RawTelemetryEvent
from scac_harness.reducer import DeterministicReducer, rehydrate_snapshot
from scac_harness.renderer import render_tier2_envelope
from scac_harness.scenarios.toolroute import ToolHealth, ToolRouteOracle, ToolRouteState


Condition = Literal["A", "B", "C"]
Action = Literal["tool_alpha", "tool_beta", "wait"]
_ACTIONS: tuple[Action, ...] = ("tool_alpha", "tool_beta", "wait")
_MIN_OBSERVABLE_MARGIN = 50.0


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
        self._write_once("manifest.json", {
            "kind": "development_smoke_only", "seed": seed, "condition": condition,
            "scenario": "ToolRoute-v0.4", "records_required": 3, "decision_budget": 4,
            "measurement_model": "independent_seeded_monitor_probes_v0.4",
            "primary_oracle": "observable_monitor_cost_v0.4",
            "secondary_oracle": "clairvoyant_latent_cost_diagnostic_only",
            "neutral_control": "utf8_byte_matched_opaque_structural_control_not_token_matched",
        })

    def _write_once(self, filename: str, content: object) -> None:
        """Durably publish a new artifact without ever replacing an existing one."""
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
        except FileExistsError:
            raise FileExistsError(destination) from None
        finally:
            temporary.unlink(missing_ok=True)

    def _health(self) -> dict[str, ToolHealth]:
        return self._health_for(self.seed, self._turn)

    @staticmethod
    def _health_for(seed: int, turn: int) -> dict[str, ToolHealth]:
        # Regime assignment and each potential tool outcome are derived from
        # independent hashes. Action choice cannot advance or perturb this tape.
        # Main-study-style dominance regimes: no near-tie reliability/latency
        # trade-off is scored as a primary correctness error.
        regimes = ((0.99, 100), (0.10, 4200), (0.10, 4200), (0.10, 4200))
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
        host = json.loads((directory / f"turn-{obj._turn:02d}-host.json").read_text(encoding="utf-8"))
        obj._prior_snapshot = host["cumulative_snapshot"]
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
        if json.loads(results[-1].read_text(encoding="utf-8"))["terminal"]:
            raise RuntimeError("development trial is terminal")
        turn = len(results)
        if turn >= 4:
            raise RuntimeError("development trial is terminal")
        host = json.loads((directory / f"turn-{turn - 1:02d}-host.json").read_text(encoding="utf-8"))
        obj = object.__new__(cls)
        obj.seed = int(manifest["seed"])
        obj.condition = manifest["condition"]
        obj._turn = turn
        obj._reducer = DeterministicReducer()
        # The delta is an audit/presentation artifact; the reducer receives
        # complete private state on the next turn.
        obj._prior_snapshot = host["cumulative_snapshot"]
        obj.directory = directory
        return obj

    def _telemetry(self, state: ToolRouteState) -> tuple[dict[str, object], str, list[dict[str, object]], dict[str, object]]:
        events = []
        for index, (tool, health) in enumerate(sorted(state.health.items())):
            # Probe outcomes have a dedicated hash namespace and are therefore
            # independent of action outcomes. They model host observation, not
            # a direct projection of latent success probability.
            for probe in range(3):
                draw = int(hashlib.sha256(f"{self.seed}:monitor:{state.turn}:{tool}:{probe}".encode()).hexdigest(), 16) / 2**256
                success = draw < health.success_probability
                events.append(RawTelemetryEvent(
                    timestamp_ms=(state.turn + 1) * 1000 + index * 10 + probe,
                    source="synthetic_host_probe_v0.4",
                    topic="tool_span",
                    payload={"tool_id": tool, "latency_ms": health.latency_ms, "success": success,
                             "error_class": "HTTP_503" if not success else "NONE", "retry_after_ms": health.retry_after_ms},
                ))
        observed_at_ms = (state.turn + 1) * 1000 + 22
        snapshot = self._reducer.reduce(
            trajectory_id=f"dev-smoke-{self.seed}", seq=state.turn,
            events=events, prior_snapshot=self._prior_snapshot,
            kind="full_checkpoint" if self._prior_snapshot is None else "delta",
            observed_at_ms=observed_at_ms,
        )
        cumulative = snapshot if self._prior_snapshot is None else rehydrate_snapshot(snapshot, self._prior_snapshot)
        self._prior_snapshot = cumulative
        rendered = render_tier2_envelope(snapshot)
        # Fail closed: a primary action label must be recoverable from the
        # canonical monitor state and the renderer must expose the used facts.
        best = ToolRouteOracle.observable_best_actions(snapshot)
        if (not best or any(tool not in rendered for tool in best)
                or ToolRouteOracle.observable_margin(snapshot) < _MIN_OBSERVABLE_MARGIN):
            raise RuntimeError("observable-oracle calibration failed")
        return snapshot, rendered, [event.to_dict() for event in events], cumulative

    @staticmethod
    def _task_text() -> str:
        return (
            "Task: retrieve the next required record. tool_alpha and tool_beta are functionally equivalent. "
            "Return exactly one listed action label and no other text.\n"
        )

    @staticmethod
    def _neutral_match(telemetry: str) -> str:
        """Opaque, varied UTF-8 byte control; explicitly not token matched."""
        prefix = "[NEUTRAL STRUCTURAL CONTROL]\n  opaque_fields=UNAVAILABLE\n"
        remaining = max(0, len(telemetry.encode("utf-8")) - len(prefix.encode("utf-8")))
        filler = "cedar lantern meadow cobalt river slate "
        return prefix + (filler * ((remaining // len(filler)) + 1)).encode("utf-8")[:remaining].decode("utf-8", errors="ignore")

    def _option_order(self) -> tuple[Action, ...]:
        permutations = (
            _ACTIONS, ("tool_alpha", "wait", "tool_beta"), ("tool_beta", "tool_alpha", "wait"),
            ("tool_beta", "wait", "tool_alpha"), ("wait", "tool_alpha", "tool_beta"),
            ("wait", "tool_beta", "tool_alpha"),
        )
        # Six consecutive seeds cover each of the six permutations at turn 0;
        # cyclic shifts then give every action every position within a trajectory.
        base = permutations[self.seed % len(permutations)]
        shift = self._turn % len(_ACTIONS)
        return base[shift:] + base[:shift]

    def next_turn(self) -> DevelopmentTurn:
        if self._turn >= 4:
            raise RuntimeError("development trial is terminal")
        state = ToolRouteState(self._turn, self._health())
        snapshot, telemetry, raw_events, cumulative = self._telemetry(state)
        options = self._option_order()
        task = self._task_text() + "Options: " + ", ".join(options) + "\n"
        if self.condition == "A":
            message, visible_snapshot = task, None
        elif self.condition == "B":
            message, visible_snapshot = task + self._neutral_match(telemetry), None
        else:
            message, visible_snapshot = task + telemetry, snapshot
        turn = DevelopmentTurn(self._turn, self.condition, message, state, visible_snapshot)
        self._write_once(f"turn-{self._turn:02d}-input.json", {
            "condition": self.condition, "message": message,
            "message_bytes": len(message.encode("utf-8")), "option_order": list(options),
            "visible_snapshot": visible_snapshot,
        })
        self._write_once(f"turn-{self._turn:02d}-host.json", {
            "raw_events": raw_events,
            "snapshot": snapshot,
            "cumulative_snapshot": cumulative,
            "rendered_telemetry": telemetry,
        })
        return turn

    def submit(self, action: Action, subject_id: str = "unspecified", response_text: str | None = None) -> dict[str, object]:
        if action not in _ACTIONS:
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
        prior_successes = sum(
            bool(json.loads(path.read_text(encoding="utf-8"))["success"])
            for path in sorted(self.directory.glob("turn-*-result.json"))
        )
        records_completed = prior_successes + int(success)
        terminal = records_completed >= 3 or self._turn == 3
        result = {
            "subject_id": subject_id, "response_text": response_text, "action": action, "success": success, "latency_ms": latency,
            "error_class": error,
            "policy_regret": ToolRouteOracle.observable_regret(self._prior_snapshot or {}, action),
            "clairvoyant_regret_diagnostic": ToolRouteOracle.regret(state, action),
            "records_required": 3, "records_completed": records_completed,
            "task_completed": records_completed >= 3,
            "terminal_classification": "COMPLETED" if records_completed >= 3 else ("DECISION_BUDGET_EXHAUSTED" if terminal else "RUNNING"),
            "terminal": terminal,
        }
        self._write_once(f"turn-{self._turn:02d}-result.json", result)
        if terminal:
            artifact_hashes = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(self.directory.glob("*.json"))
            }
            self._write_once("finalization.json", {"terminal_turn": self._turn, "artifact_sha256": artifact_hashes})
        self._turn += 1
        return result

    def record_rejection(self, subject_id: str, response_text: str, reason: str) -> dict[str, object]:
        """Retain malformed agent output without converting it into an action."""
        existing = len(list(self.directory.glob(f"turn-{self._turn:02d}-rejection-*.json")))
        record = {
            "subject_id": subject_id, "response_text": response_text,
            "reason": reason, "accepted": False, "turn": self._turn,
        }
        self._write_once(f"turn-{self._turn:02d}-rejection-{existing:02d}.json", record)
        return record

    def record_handoff(self, turn: int, message: str, subject_prompt: str) -> None:
        """Preserve the exact coordinator-to-subject input before subject creation."""
        input_record = json.loads((self.directory / f"turn-{turn:02d}-input.json").read_text(encoding="utf-8"))
        if input_record["message"] != message:
            raise RuntimeError("handoff message differs from immutable condition message")
        self._write_once(f"turn-{turn:02d}-handoff.json", {
            "handoff_contract": "subject_prompt_v1_double_newline_delimiter",
            "condition_message": message,
            "subject_instruction": (
                "Do not inspect the workspace or use tools. "
                "Reply with exactly one action label and nothing else."
            ),
            "subject_prompt": subject_prompt,
        })

    @classmethod
    def abort(cls, directory: Path, reason: str) -> None:
        """Close a development attempt without deleting its partial provenance."""
        directory = Path(directory)
        if (directory / "finalization.json").exists():
            raise RuntimeError("trial is already finalized")
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        obj = object.__new__(cls)
        obj.directory = directory
        obj._write_once("abort.json", {"classification": "ABORTED_DEVELOPMENT", "reason": reason, "seed": manifest["seed"]})
        artifact_hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.glob("*.json"))
        }
        obj._write_once("finalization.json", {"terminal_turn": None, "artifact_sha256": artifact_hashes, "classification": "ABORTED_DEVELOPMENT"})
