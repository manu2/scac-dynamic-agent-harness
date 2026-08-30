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
from urllib import error, request
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
    raw_response: Mapping[str, object] | None = None


class Provider(Protocol):
    """A deliberately tool-less provider interface."""

    def complete(self, prompt: str) -> ProviderResponse: ...

    def request_record(self, prompt: str) -> Mapping[str, object]: ...

    def error_record(self, exc: Exception) -> Mapping[str, object]: ...


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

    version: str = "synthetic_host_probe_v0.6"
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


class ProviderTokenCounter(Protocol):
    """Provider-native input-token counter used to freeze a B/C control.

    The count must be produced by the same provider/model family that will
    receive the episode.  A local approximation is allowed only in unit tests
    and never establishes a paper-cohort B/C match.
    """

    name: str

    def count_tokens(self, prompt: str) -> int: ...


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

    def verify_episode(self, *, seed: int, turn: int, condition: Condition, model_id: str, provider_label: str) -> None:
        """Fail closed unless this exact paid episode is declared in the manifest."""
        manifest = json.loads(self.pilot_manifest_path.read_text(encoding="utf-8"))
        episodes = manifest.get("authorized_episodes")
        target = {"seed": seed, "turn": turn, "condition": condition, "model_id": model_id, "provider_label": provider_label}
        if isinstance(episodes, list) and target in episodes:
            return
        # A Cartesian episode grid is equally explicit but avoids an error-prone
        # 216-row manifest.  Every dimension is frozen; no wildcard model,
        # provider, seed, turn, or condition is accepted.
        grids = manifest.get("authorized_episode_grids")
        if isinstance(grids, list):
            for grid in grids:
                if not isinstance(grid, Mapping):
                    continue
                if (grid.get("model_id") == model_id and grid.get("provider_label") == provider_label
                    and seed in grid.get("seeds", []) and turn in grid.get("turns", [])
                    and condition in grid.get("conditions", [])):
                    return
        raise PermissionError("episode is not explicitly authorized by the frozen manifest")


@dataclass(frozen=True)
class AuthorizationBoundTokenizer:
    """Make provider-native token counting subject to live authorization."""

    authorization: ToolRouteAuthorization
    name: str
    counter: Callable[[str], int]

    def count(self, prompt: str) -> int:
        self.authorization.verify_live()
        return self.counter(prompt)


class OpenAICompatibleProvider:
    """Small dependency-free chat-completions adapter for a later authorized run."""

    def __init__(self, *, endpoint: str, api_key: str, model: str, temperature: float | None = None, max_output_tokens: int = 1024) -> None:
        self.endpoint, self._api_key, self.model, self.temperature = endpoint, api_key, model, temperature
        self.max_output_tokens = max_output_tokens

    def _body(self, prompt: str) -> dict[str, object]:
        body: dict[str, object] = {"model": self.model, "max_completion_tokens": self.max_output_tokens,
                                   "messages": [{"role": "user", "content": prompt}]}
        if self.temperature is not None:
            body["temperature"] = self.temperature
        return body

    def request_record(self, prompt: str) -> Mapping[str, object]:
        return {"adapter": "openai_chat_completions_v1", "endpoint": self.endpoint, "body": self._body(prompt)}

    def error_record(self, exc: Exception) -> Mapping[str, object]:
        return _safe_provider_error(exc, self._api_key)

    def complete(self, prompt: str) -> ProviderResponse:
        body = json.dumps(self._body(prompt)).encode("utf-8")
        req = request.Request(self.endpoint, data=body, method="POST", headers={
            "Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json",
        })
        with request.urlopen(req, timeout=60) as response:  # nosec B310: explicit user-authorized provider only
            payload = json.loads(response.read().decode("utf-8"))
        usage = payload.get("usage", {})
        return ProviderResponse(
            text=str(payload["choices"][0]["message"]["content"]),
            request_id=payload.get("id"), input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"), raw_response=payload,
        )

    def count_tokens(self, prompt: str) -> int:
        """Use OpenAI's native Responses input-token counter.

        Generation remains on Chat Completions for the retained transport
        preflights.  The counter is used only to match the *same user prompt*
        between B and C; a frozen paper manifest must record that distinction.
        """
        endpoint = "https://api.openai.com/v1/responses/input_tokens"
        body = {"model": self.model, "input": [{"role": "user", "content": prompt}]}
        req = request.Request(endpoint, data=json.dumps(body).encode("utf-8"), method="POST", headers={
            "Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json",
        })
        with request.urlopen(req, timeout=60) as response:  # nosec B310: explicitly authorized calibration only
            payload = json.loads(response.read().decode("utf-8"))
        value = payload.get("input_tokens")
        if not isinstance(value, int):
            raise ValueError("OpenAI input-token counter returned no integer input_tokens")
        return value


class AnthropicMessagesProvider:
    """Dependency-free Anthropic Messages adapter; tools are never supplied."""

    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(self, *, api_key: str, model: str, api_version: str, temperature: float | None = None, max_output_tokens: int = 1024) -> None:
        self._api_key, self.model, self.api_version = api_key, model, api_version
        self.temperature, self.max_output_tokens = temperature, max_output_tokens

    def _body(self, prompt: str) -> dict[str, object]:
        body: dict[str, object] = {"model": self.model, "max_tokens": self.max_output_tokens,
                                   "messages": [{"role": "user", "content": prompt}]}
        if self.temperature is not None:
            body["temperature"] = self.temperature
        return body

    def request_record(self, prompt: str) -> Mapping[str, object]:
        return {"adapter": "anthropic_messages_v1", "endpoint": self.endpoint, "anthropic_version": self.api_version, "body": self._body(prompt)}

    def error_record(self, exc: Exception) -> Mapping[str, object]:
        return _safe_provider_error(exc, self._api_key)

    def complete(self, prompt: str) -> ProviderResponse:
        req = request.Request(self.endpoint, data=json.dumps(self._body(prompt)).encode("utf-8"), method="POST", headers={
            "x-api-key": self._api_key, "anthropic-version": self.api_version, "content-type": "application/json",
        })
        with request.urlopen(req, timeout=60) as response:  # nosec B310: explicit authorized provider path
            payload = json.loads(response.read().decode("utf-8"))
        content = payload.get("content", [])
        text = "".join(str(block.get("text", "")) for block in content if isinstance(block, Mapping) and block.get("type") == "text")
        usage = payload.get("usage", {})
        return ProviderResponse(text=text, request_id=payload.get("id"), input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"), raw_response=payload)

    def count_tokens(self, prompt: str) -> int:
        endpoint = "https://api.anthropic.com/v1/messages/count_tokens"
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        req = request.Request(endpoint, data=json.dumps(body).encode("utf-8"), method="POST", headers={
            "x-api-key": self._api_key, "anthropic-version": self.api_version, "content-type": "application/json",
        })
        with request.urlopen(req, timeout=60) as response:  # nosec B310: explicitly authorized calibration only
            payload = json.loads(response.read().decode("utf-8"))
        value = payload.get("input_tokens")
        if not isinstance(value, int):
            raise ValueError("Anthropic token counter returned no integer input_tokens")
        return value


class GeminiGenerateContentProvider:
    """Dependency-free Gemini REST adapter; tools and server-side state are omitted."""

    def __init__(self, *, api_key: str, model: str, temperature: float = 0.0, max_output_tokens: int = 1024) -> None:
        self._api_key, self.model, self.temperature, self.max_output_tokens = api_key, model, temperature, max_output_tokens

    @property
    def endpoint(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def _body(self, prompt: str) -> dict[str, object]:
        return {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": self.temperature, "maxOutputTokens": self.max_output_tokens}}

    def request_record(self, prompt: str) -> Mapping[str, object]:
        return {"adapter": "gemini_generate_content_v1", "endpoint": self.endpoint, "body": self._body(prompt)}

    def error_record(self, exc: Exception) -> Mapping[str, object]:
        return _safe_provider_error(exc, self._api_key)

    def complete(self, prompt: str) -> ProviderResponse:
        req = request.Request(f"{self.endpoint}?key={self._api_key}", data=json.dumps(self._body(prompt)).encode("utf-8"), method="POST", headers={"content-type": "application/json"})
        with request.urlopen(req, timeout=60) as response:  # nosec B310: explicit authorized provider path
            payload = json.loads(response.read().decode("utf-8"))
        candidates = payload.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates and isinstance(candidates[0], Mapping) else []
        text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, Mapping) and not part.get("thought", False))
        usage = payload.get("usageMetadata", {})
        output = usage.get("totalTokenCount")
        if isinstance(output, int) and isinstance(usage.get("promptTokenCount"), int):
            output -= usage["promptTokenCount"]
        return ProviderResponse(text=text, request_id=payload.get("responseId"), input_tokens=usage.get("promptTokenCount"), output_tokens=output, raw_response=payload)

    def count_tokens(self, prompt: str) -> int:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:countTokens?key={self._api_key}"
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        req = request.Request(endpoint, data=json.dumps(body).encode("utf-8"), method="POST", headers={"content-type": "application/json"})
        with request.urlopen(req, timeout=60) as response:  # nosec B310: explicitly authorized calibration only
            payload = json.loads(response.read().decode("utf-8"))
        value = payload.get("totalTokens")
        if not isinstance(value, int):
            raise ValueError("Gemini token counter returned no integer totalTokens")
        return value


def _safe_provider_error(exc: Exception, api_key: str) -> dict[str, object]:
    """Retain provider diagnostics while redacting an API key from every field."""
    def redact(value: object) -> object:
        if isinstance(value, str):
            return value.replace(api_key, "[REDACTED]")
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, dict):
            return {str(key): redact(item) for key, item in value.items()}
        return value

    record: dict[str, object] = {"exception_type": type(exc).__name__}
    if isinstance(exc, error.HTTPError):
        record["http_status"] = exc.code
        try:
            raw = exc.read().decode("utf-8", errors="replace")
            record["provider_error"] = redact(json.loads(raw))
        except (OSError, UnicodeError, json.JSONDecodeError):
            record["reason"] = redact(str(exc.reason))
    else:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, str):
            record["reason"] = redact(reason)
    return record


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


def build_toolroute_observation_checkpoint(
    *, seed: int, turn: int, observation_model: ToolRouteObservationModel,
) -> tuple[dict[str, object], list[RawTelemetryEvent]]:
    """Build a side-effect-free full checkpoint for model-free calibration."""
    if turn not in range(4):
        raise ValueError("ToolRoute observation turn must be in [0, 3]")
    reducer, prior = DeterministicReducer(), None
    all_events: list[RawTelemetryEvent] = []
    snapshot: dict[str, object] | None = None
    for observed_turn in range(turn + 1):
        events: list[RawTelemetryEvent] = []
        for index, (tool, health) in enumerate(sorted(_health_for(seed, observed_turn).items())):
            for probe in range(observation_model.probes_per_tool):
                draw = int(hashlib.sha256(f"{seed}:monitor:{observed_turn}:{tool}:{probe}".encode()).hexdigest(), 16) / 2**256
                success = draw < health.success_probability
                flip = int(hashlib.sha256(f"{seed}:monitor-label:{observed_turn}:{tool}:{probe}".encode()).hexdigest(), 16) / 2**256
                if flip < observation_model.success_label_error_probability:
                    success = not success
                drop = int(hashlib.sha256(f"{seed}:monitor-drop:{observed_turn}:{tool}:{probe}".encode()).hexdigest(), 16) / 2**256
                if drop < observation_model.event_drop_probability:
                    continue
                events.append(RawTelemetryEvent(
                    timestamp_ms=(observed_turn + 1) * 1000 + index * 10 + probe,
                    source=observation_model.version, topic="tool_span",
                    payload={"tool_id": tool, "latency_ms": health.latency_ms, "success": success,
                             "error_class": "HTTP_503" if not success else "NONE", "retry_after_ms": health.retry_after_ms},
                ))
        all_events.extend(events)
        snapshot = reducer.reduce(
            trajectory_id=f"toolroute-observation-{seed}-{turn}", seq=observed_turn, events=events,
            prior_snapshot=prior, kind="full_checkpoint",
            observed_at_ms=(observed_turn + 1) * 1000 + 22 + observation_model.delivery_delay_ms,
        )
        prior = snapshot
    assert snapshot is not None
    return snapshot, all_events


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
            "kind": "toolroute_api_independent_full_checkpoint", "scenario": "ToolRoute-v0.6-api-preflight",
            "seed": seed, "turn": turn, "condition": condition, "model_id": model_id,
            "provider_label": provider_label, "tokenizer": tokenizer.name,
            "state_delivery": "independent_full_checkpoint_only", "provider_tools": "none",
            "observation_model": asdict(observation_model),
            "primary_oracle": "observable_monitor_cost_v0.6", "secondary_oracle": "clairvoyant_latent_cost_diagnostic_only",
        })
        self.snapshot, self.raw_events = self._full_checkpoint()
        self.rendered = render_tier2_envelope(self.snapshot)
        if ToolRouteOracle.observable_margin(self.snapshot) < _MIN_OBSERVABLE_MARGIN:
            raise RuntimeError("observable-oracle calibration failed")
        self.options = _option_order(seed, turn)
        try:
            self.prompt = self._prompt()
        except Exception as exc:
            # Reservation happens before any provider contact.  A tokenizer
            # mismatch is still an attempted setup and must be terminal.
            self._write_once("setup-error.json", {
                "classification": "REJECTED_TOKEN_CONTROL_SETUP",
                "exception_type": type(exc).__name__, "reason": str(exc),
            })
            self._finalize("REJECTED_TOKEN_CONTROL_SETUP")
            raise
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
        return build_toolroute_observation_checkpoint(
            seed=self.seed, turn=self.turn, observation_model=self.observation_model,
        )

    def _neutral_prompt(self, task: str, target_tokens: int) -> str:
        # Keep the exact telemetry envelope and field layout visible in C, but
        # replace every route-relevant value with the same benign value for
        # both tools.  B therefore controls for telemetry-shaped attention and
        # prompt length without encoding an action preference.
        neutral = self.rendered
        lines = []
        for line in neutral.splitlines():
            if line.startswith("  tool_alpha:") or line.startswith("  tool_beta:"):
                tool = line.split(":", 1)[0].strip()
                lines.append(
                    f"  {tool}: window=0 succ=0 consec_fail=0 latency_ewma=0.0ms "
                    "last_err=NONE circuit=CLOSED age=10ms"
                )
            else:
                lines.append(line)
        prefix = task + "\n".join(lines)
        prompt, current = prefix, self.tokenizer.count(prefix)
        # Provider tokenizers are discrete and need not assign one token to the
        # same padding atom.  Greedily use only empirically observed deltas
        # that do not overshoot the target; fail closed if none is available.
        padding_atoms = (" neutral", " .", " 0", " x", " _", "\n")
        while current < target_tokens:
            remaining = target_tokens - current
            choices: list[tuple[int, str]] = []
            for atom in padding_atoms:
                candidate_count = self.tokenizer.count(prompt + atom)
                delta = candidate_count - current
                if 0 < delta <= remaining:
                    choices.append((delta, atom))
            if not choices:
                break
            delta, atom = max(choices)
            prompt += atom
            current += delta
        if current != target_tokens:
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
        try:
            authorization.verify_live()
            authorization.verify_episode(seed=self.seed, turn=self.turn, condition=self.condition, model_id=self.model_id, provider_label=self.provider_label)
        except PermissionError as exc:
            result = {"accepted": False, "classification": "REJECTED_MANIFEST_SCOPE", "reason": str(exc)}
            self._write_once("result.json", result); self._finalize(result["classification"])
            return result
        request_record = getattr(provider, "request_record", None)
        if not callable(request_record):
            raise TypeError("provider must expose a sanitized request_record")
        self._write_once("provider-request.json", dict(request_record(self.prompt)))
        try:
            response = provider.complete(self.prompt)
        except Exception as exc:
            # Do not archive a transport exception's text: some HTTP libraries
            # echo a request URL, and Gemini carries its API key in the query.
            record_error = getattr(provider, "error_record", None)
            provider_error = dict(record_error(exc)) if callable(record_error) else {"exception_type": type(exc).__name__}
            self._write_once("provider-error.json", provider_error)
            result = {"accepted": False, "classification": "PROVIDER_ERROR", "provider_error": provider_error}
            self._write_once("result.json", result); self._finalize(result["classification"])
            return result
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
