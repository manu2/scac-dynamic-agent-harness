"""Isolated, full-checkpoint ToolRoute API-pilot runner.

The runner owns the hidden schedule and evaluator.  A provider receives only a
single rendered prompt and has no tool or filesystem interface.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Callable, Literal, Mapping, Protocol
from urllib import request
from uuid import uuid4

from scac_harness.events import RawTelemetryEvent
from scac_harness.reducer import DeterministicReducer
from scac_harness.renderer import render_tier2_envelope
from scac_harness.scenarios.toolroute import ToolHealth, ToolRouteOracle, ToolRouteState


Condition = Literal["A", "B", "C"]
Action = Literal["tool_alpha", "tool_beta", "wait"]
_ACTIONS: tuple[Action, ...] = ("tool_alpha", "tool_beta", "wait")
_MIN_OBSERVABLE_MARGIN = 50.0


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class Provider(Protocol):
    """A deliberately tool-less provider interface."""

    def complete(self, prompt: str) -> ProviderResponse: ...


@dataclass(frozen=True)
class Tokenizer:
    name: str
    count: Callable[[str], int]


@dataclass(frozen=True)
class ToolRouteObservationModel:
    """Versioned synthetic monitor assumptions, retained with every episode.

    ``success_label_error_probability`` represents monitor misclassification;
    delivery delay applies before reducer observation.  The default is the
    baseline calibration, while non-zero settings support sensitivity runs that
    must remain outside the primary cohort unless predeclared there.
    """

    version: str = "synthetic_host_probe_v0.5"
    probes_per_tool: int = 3
    success_label_error_probability: float = 0.0
    event_drop_probability: float = 0.0
    delivery_delay_ms: int = 0

    def __post_init__(self) -> None:
        if self.probes_per_tool < 1:
            raise ValueError("probes_per_tool must be positive")
        for value in (self.success_label_error_probability, self.event_drop_probability):
            if not 0.0 <= value < 1.0:
                raise ValueError("observation error and drop probabilities must be in [0, 1)")
        if self.delivery_delay_ms < 0:
            raise ValueError("delivery_delay_ms must be non-negative")


class WhitespaceTokenizer:
    """Test-only tokenizer; never valid for a paper provider cohort."""

    name = "test-whitespace-tokenizer"

    @staticmethod
    def count(text: str) -> int:
        return len(text.split())


@dataclass(frozen=True)
class ToolRouteAuthorization:
    """A checked, immutable authorization for an API pilot invocation.

    A caller cannot enable a model request by passing an arbitrary boolean.  It
    must bind the repository provenance record to the exact frozen manifest.
    """

    provenance_path: Path
    pilot_manifest_path: Path
    pilot_manifest_sha256: str

    @classmethod
    def load(cls, *, provenance_path: Path, pilot_manifest_path: Path) -> "ToolRouteAuthorization":
        provenance = json.loads(Path(provenance_path).read_text(encoding="utf-8"))
        digest = hashlib.sha256(Path(pilot_manifest_path).read_bytes()).hexdigest()
        if not provenance.get("toolroute_provider_trials_authorized", False):
            raise PermissionError("toolroute_provider_trials_authorized=false")
        if provenance.get("toolroute_pilot_manifest_sha256") != digest:
            raise PermissionError("frozen ToolRoute pilot manifest hash does not match provenance")
        return cls(Path(provenance_path), Path(pilot_manifest_path), digest)

    def verify_live(self) -> None:
        """Recheck both immutable inputs immediately before a provider request."""
        provenance = json.loads(self.provenance_path.read_text(encoding="utf-8"))
        current_digest = hashlib.sha256(self.pilot_manifest_path.read_bytes()).hexdigest()
        if not provenance.get("toolroute_provider_trials_authorized", False):
            raise PermissionError("ToolRoute authorization was revoked before provider request")
        if current_digest != self.pilot_manifest_sha256 or provenance.get("toolroute_pilot_manifest_sha256") != current_digest:
            raise PermissionError("frozen ToolRoute pilot manifest changed before provider request")


class OpenAICompatibleProvider:
    """Small dependency-free chat-completions adapter for a later authorized run."""

    def __init__(self, *, endpoint: str, api_key: str, model: str, temperature: float = 0.0) -> None:
        self.endpoint, self._api_key, self.model, self.temperature = endpoint, api_key, model, temperature

    def complete(self, prompt: str) -> ProviderResponse:
        body = json.dumps({
            "model": self.model,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = request.Request(self.endpoint, data=body, method="POST", headers={
            "Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json",
        })
        with request.urlopen(req, timeout=60) as response:  # nosec B310: explicit user-authorized provider only
            payload = json.loads(response.read().decode("utf-8"))
        usage = payload.get("usage", {})
        return ProviderResponse(
            text=str(payload["choices"][0]["message"]["content"]),
            request_id=payload.get("id"), input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"),
        )


def _health_for(seed: int, turn: int) -> dict[str, ToolHealth]:
    regimes = ((0.99, 100), (0.10, 4200), (0.10, 4200), (0.10, 4200))
    probability, latency = regimes[turn]
    rotate = int(hashlib.sha256(f"{seed}:regime:{turn}".encode()).hexdigest(), 16) % 2
    degraded, healthy = ("tool_alpha", "tool_beta") if rotate == 0 else ("tool_beta", "tool_alpha")
    return {
        degraded: ToolHealth(probability, latency, 2000 if probability <= 0.20 else None),
        healthy: ToolHealth(0.99, 180),
    }


def _option_order(seed: int, turn: int) -> tuple[Action, ...]:
    permutations: tuple[tuple[Action, ...], ...] = (
        _ACTIONS, ("tool_alpha", "wait", "tool_beta"), ("tool_beta", "tool_alpha", "wait"),
        ("tool_beta", "wait", "tool_alpha"), ("wait", "tool_alpha", "tool_beta"),
        ("wait", "tool_beta", "tool_alpha"),
    )
    base = permutations[seed % len(permutations)]
    shift = turn % len(_ACTIONS)
    return base[shift:] + base[:shift]


def _task(options: tuple[Action, ...]) -> str:
    return (
        "Task: retrieve the next required record. tool_alpha and tool_beta are functionally equivalent. "
        "Return exactly one listed action label and no other text.\nOptions: " + ", ".join(options) + "\n"
    )


class ToolRouteAPIEpisode:
    """One independent, full-checkpoint provider decision episode."""

    def __init__(
        self, *, seed: int, turn: int, condition: Condition, experiments_root: Path,
        tokenizer: Tokenizer, model_id: str, provider_label: str,
        observation_model: ToolRouteObservationModel = ToolRouteObservationModel(),
    ) -> None:
        if turn not in range(4):
            raise ValueError("ToolRoute API episode turn must be in [0, 3]")
        self.seed, self.turn, self.condition = seed, turn, condition
        self.tokenizer, self.model_id, self.provider_label = tokenizer, model_id, provider_label
        self.observation_model = observation_model
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.directory = Path(experiments_root) / "api-preflight" / "toolroute" / f"{stamp}-{condition}-{uuid4().hex}"
        self.directory.mkdir(parents=True, mode=0o700)
        self._write_once("manifest.json", {
            "kind": "toolroute_api_independent_full_checkpoint", "scenario": "ToolRoute-v0.4-api-preflight",
            "seed": seed, "turn": turn, "condition": condition, "model_id": model_id,
            "provider_label": provider_label, "tokenizer": tokenizer.name,
            "state_delivery": "independent_full_checkpoint_only", "provider_tools": "none",
            "observation_model": asdict(observation_model),
            "primary_oracle": "observable_monitor_cost_v0.4", "secondary_oracle": "clairvoyant_latent_cost_diagnostic_only",
        })
        self.snapshot, self.raw_events = self._full_checkpoint()
        self.rendered = render_tier2_envelope(self.snapshot)
        if ToolRouteOracle.observable_margin(self.snapshot) < _MIN_OBSERVABLE_MARGIN:
            raise RuntimeError("observable-oracle calibration failed")
        self.options = _option_order(seed, turn)
        self.prompt = self._prompt()
        self._write_once("input.json", {
            "condition": condition, "prompt": self.prompt, "prompt_tokens": tokenizer.count(self.prompt),
            "option_order": list(self.options), "visible_snapshot": self.snapshot if condition == "C" else None,
        })
        self._write_once("host.json", {
            "raw_events": [event.to_dict() for event in self.raw_events], "full_checkpoint": self.snapshot,
            "rendered_telemetry": self.rendered,
        })

    def _write_once(self, filename: str, content: object) -> None:
        destination = self.directory / filename
        if destination.exists():
            raise FileExistsError(destination)
        temporary = self.directory / f".{filename}.{uuid4().hex}.tmp"
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(content, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def _full_checkpoint(self) -> tuple[dict[str, object], list[RawTelemetryEvent]]:
        reducer, prior = DeterministicReducer(), None
        all_events: list[RawTelemetryEvent] = []
        snapshot: dict[str, object] | None = None
        for observed_turn in range(self.turn + 1):
            events: list[RawTelemetryEvent] = []
            for index, (tool, health) in enumerate(sorted(_health_for(self.seed, observed_turn).items())):
                for probe in range(self.observation_model.probes_per_tool):
                    draw = int(hashlib.sha256(f"{self.seed}:monitor:{observed_turn}:{tool}:{probe}".encode()).hexdigest(), 16) / 2**256
                    success = draw < health.success_probability
                    flip = int(hashlib.sha256(f"{self.seed}:monitor-label:{observed_turn}:{tool}:{probe}".encode()).hexdigest(), 16) / 2**256
                    if flip < self.observation_model.success_label_error_probability:
                        success = not success
                    drop = int(hashlib.sha256(f"{self.seed}:monitor-drop:{observed_turn}:{tool}:{probe}".encode()).hexdigest(), 16) / 2**256
                    if drop < self.observation_model.event_drop_probability:
                        continue
                    events.append(RawTelemetryEvent(
                        timestamp_ms=(observed_turn + 1) * 1000 + index * 10 + probe + self.observation_model.delivery_delay_ms,
                        source=self.observation_model.version, topic="tool_span",
                        payload={"tool_id": tool, "latency_ms": health.latency_ms, "success": success,
                                 "error_class": "HTTP_503" if not success else "NONE", "retry_after_ms": health.retry_after_ms},
                    ))
            all_events.extend(events)
            snapshot = reducer.reduce(
                trajectory_id=f"toolroute-api-{self.seed}-{self.turn}", seq=observed_turn, events=events,
                prior_snapshot=prior, kind="full_checkpoint",
                observed_at_ms=(observed_turn + 1) * 1000 + 22 + self.observation_model.delivery_delay_ms,
            )
            prior = snapshot
        assert snapshot is not None
        return snapshot, all_events

    def _neutral_prompt(self, task: str, target_tokens: int) -> str:
        prefix = task + "[NEUTRAL STRUCTURAL CONTROL]\n"
        prompt = prefix
        while self.tokenizer.count(prompt) < target_tokens:
            prompt += " opaque"
        if self.tokenizer.count(prompt) != target_tokens:
            raise ValueError("tokenizer cannot construct an exactly token-matched B control")
        return prompt

    def _prompt(self) -> str:
        task = _task(self.options)
        c_prompt = task + self.rendered
        if self.condition == "A":
            return task
        if self.condition == "B":
            return self._neutral_prompt(task, self.tokenizer.count(c_prompt))
        return c_prompt

    def _outcome(self, action: Action) -> dict[str, object]:
        state = ToolRouteState(self.turn, _health_for(self.seed, self.turn))
        health = state.health.get(action)
        if health is None:
            success, latency, error = False, ToolRouteOracle.WAIT_LATENCY_MS, None
        else:
            draw = int(hashlib.sha256(f"{self.seed}:outcome:{self.turn}:{action}".encode()).hexdigest(), 16) / 2**256
            success, latency, error = draw < health.success_probability, health.latency_ms, None
            if not success:
                error = "HTTP_503"
        return {
            "action": action, "success": success, "latency_ms": latency, "error_class": error,
            "policy_regret": ToolRouteOracle.observable_regret(self.snapshot, action),
            "clairvoyant_regret_diagnostic": ToolRouteOracle.regret(state, action),
        }

    def _finalize(self, classification: str) -> None:
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(self.directory.glob("*.json"))}
        self._write_once("finalization.json", {"classification": classification, "artifact_sha256": hashes})

    def run(self, provider: Provider, *, authorization: ToolRouteAuthorization | None) -> dict[str, object]:
        if authorization is None:
            result = {"accepted": False, "classification": "REJECTED_PRE_AUTHORIZATION", "reason": "missing verified ToolRoute authorization"}
            self._write_once("result.json", result); self._finalize(result["classification"])
            return result
        if not authorization.pilot_manifest_path.is_file() or not authorization.provenance_path.is_file():
            raise PermissionError("authorization source disappeared before provider request")
        authorization.verify_live()
        response = provider.complete(self.prompt)
        response_record = asdict(response)
        self._write_once("provider-response.json", response_record)
        cleaned = response.text.strip()
        if cleaned not in _ACTIONS:
            result = {"accepted": False, "classification": "MALFORMED_PROVIDER_RESPONSE", "response_text": response.text}
            self._write_once("result.json", result); self._finalize(result["classification"])
            return result
        result = {"accepted": True, "classification": "COMPLETED", "response_text": response.text, **self._outcome(cleaned)}
        self._write_once("result.json", result); self._finalize(result["classification"])
        return result
