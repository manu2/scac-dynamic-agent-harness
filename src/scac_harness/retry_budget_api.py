"""Manifest-bound, tool-less RetryBudget v0.2 provider-canary runner.

The runner is intentionally scenario-owned. It reuses only the already-tested
transport-provider interface; RetryBudget owns its state machine, prompt,
observable oracle, authorization field, artifacts, and terminal accounting.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from scac_harness.retry_budget_observation import (
    RetryBudgetCondition,
    RetryBudgetObservationModel,
    observable_projection,
    prompt_record,
)
from scac_harness.scenarios.retry_budget import (
    RetryBudgetOracle,
    RetryBudgetSimulator,
    rollout_oracle_policy,
)
from scac_harness.toolroute_api import Provider, ProviderResponse


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _contains(expected: Mapping[str, object], actual: Mapping[str, object]) -> bool:
    """Return whether a request body contains an exact declared static subset."""
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if isinstance(expected_value, Mapping):
            if not isinstance(actual_value, Mapping) or not _contains(expected_value, actual_value):
                return False
        elif actual_value != expected_value:
            return False
    return True


@dataclass(frozen=True)
class RetryBudgetAuthorization:
    """Live provenance-and-manifest authorization for one paid trajectory."""

    provenance_path: Path
    manifest_path: Path
    manifest_sha256: str

    @classmethod
    def load(cls, *, provenance_path: Path, manifest_path: Path) -> "RetryBudgetAuthorization":
        provenance = json.loads(Path(provenance_path).read_text(encoding="utf-8"))
        digest = _sha256(Path(manifest_path))
        if not provenance.get("retrybudget_provider_trials_authorized", False):
            raise PermissionError("retrybudget_provider_trials_authorized=false")
        if provenance.get("retrybudget_pilot_manifest_sha256") != digest:
            raise PermissionError("frozen RetryBudget manifest hash does not match provenance")
        return cls(Path(provenance_path), Path(manifest_path), digest)

    def verify_live(self) -> None:
        provenance = json.loads(self.provenance_path.read_text(encoding="utf-8"))
        if not provenance.get("retrybudget_provider_trials_authorized", False):
            raise PermissionError("RetryBudget authorization was revoked before provider request")
        if _sha256(self.manifest_path) != self.manifest_sha256:
            raise PermissionError("frozen RetryBudget manifest changed before provider request")
        if provenance.get("retrybudget_pilot_manifest_sha256") != self.manifest_sha256:
            raise PermissionError("RetryBudget provenance binding changed before provider request")

    def verify_trajectory(
        self, *, seed: int, condition: RetryBudgetCondition, model_id: str, provider_label: str,
    ) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        target = {
            "seed": seed,
            "condition": condition,
            "model_id": model_id,
            "provider_label": provider_label,
        }
        if target in manifest.get("authorized_trajectories", []):
            return
        for grid in manifest.get("authorized_trajectory_grids", []):
            if not isinstance(grid, Mapping):
                continue
            if (
                grid.get("model_id") == model_id
                and grid.get("provider_label") == provider_label
                and seed in grid.get("seeds", [])
                and condition in grid.get("conditions", [])
            ):
                return
        raise PermissionError("trajectory is not explicitly authorized by the frozen manifest")

    def verify_request_configuration(
        self, *, provider_label: str, model_id: str, request_record: Mapping[str, object],
    ) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        expectations = manifest.get("provider_request_expectations", [])
        expected = next(
            (
                item for item in expectations
                if isinstance(item, Mapping)
                and item.get("provider_label") == provider_label
                and item.get("model_id") == model_id
            ),
            None,
        )
        if expected is None:
            raise PermissionError("provider/model has no frozen request expectation")
        if request_record.get("adapter") != expected.get("adapter"):
            raise PermissionError("provider adapter differs from the frozen request expectation")
        endpoint_suffix = expected.get("endpoint_suffix")
        endpoint = request_record.get("endpoint")
        if endpoint_suffix is not None and (not isinstance(endpoint, str) or not endpoint.endswith(str(endpoint_suffix))):
            raise PermissionError("provider endpoint differs from the frozen request expectation")
        body = request_record.get("body")
        required = expected.get("required_body_fields", {})
        if not isinstance(body, Mapping) or not isinstance(required, Mapping) or not _contains(required, body):
            raise PermissionError("provider request differs from the frozen static body contract")
        forbidden = expected.get("forbidden_body_fields", [])
        if not isinstance(forbidden, list) or any(field in body for field in forbidden):
            raise PermissionError("provider request contains a forbidden field")

    def max_provider_generations(self) -> int:
        """Read the manifest's hard paid-generation ceiling safely."""
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        limit = manifest.get("max_provider_generations")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise PermissionError("manifest has no valid max_provider_generations")
        return limit


class RetryBudgetAPITrajectory:
    """One full, fresh-checkpoint provider trajectory for one seed/condition."""

    def __init__(
        self,
        *,
        seed: int,
        condition: RetryBudgetCondition,
        experiments_root: Path,
        model_id: str,
        provider_label: str,
        pilot_manifest_sha256: str | None = None,
        observation_model: RetryBudgetObservationModel = RetryBudgetObservationModel(),
    ) -> None:
        self.seed, self.condition = seed, condition
        self.model_id, self.provider_label = model_id, provider_label
        self.pilot_manifest_sha256 = pilot_manifest_sha256
        self.observation_model = observation_model
        self._simulator = RetryBudgetSimulator(seed)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self._scenario_root = Path(experiments_root) / "api-preflight" / "retrybudget-v0-2"
        self.directory = self._scenario_root / f"{stamp}-{condition}-{uuid4().hex}"
        self.directory.mkdir(parents=True, mode=0o700)
        self._write_once("manifest.json", {
            "kind": "retrybudget_api_fresh_full_checkpoint_trajectory",
            "scenario": "RetryBudget-v0.2",
            "seed": seed,
            "condition": condition,
            "model_id": model_id,
            "provider_label": provider_label,
            "pilot_manifest_sha256": pilot_manifest_sha256,
            "state_delivery": "independent_full_checkpoint_only",
            "provider_tools": "none",
            "observation_model": asdict(observation_model),
            "primary_oracle": "observable_dynamic_program_v0.2",
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

    def _finalize(self, classification: str) -> None:
        hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.directory.glob("*.json"))
        }
        self._write_once("finalization.json", {"classification": classification, "artifact_sha256": hashes})

    def _reject(self, classification: str, reason: str) -> dict[str, object]:
        result = {"accepted": False, "classification": classification, "reason": reason}
        self._write_once("result.json", result)
        self._finalize(classification)
        return result

    def _claim_trajectory(self, authorization: RetryBudgetAuthorization) -> None:
        """Atomically consume the exact manifest-bound trajectory once.

        An explicit one-row manifest is insufficient by itself: a launcher can
        be run twice while authorization remains true. The claim is created
        before the first provider request. A second reservation is retained as
        a rejected attempt rather than becoming an untracked duplicate call.
        """
        claim_key = hashlib.sha256(json.dumps({
            "manifest_sha256": authorization.manifest_sha256,
            "seed": self.seed,
            "condition": self.condition,
            "model_id": self.model_id,
            "provider_label": self.provider_label,
        }, sort_keys=True).encode("utf-8")).hexdigest()
        claims = self._scenario_root / ".trajectory-claims"
        claims.mkdir(mode=0o700, exist_ok=True)
        claim = claims / f"{claim_key}.json"
        payload = {
            "manifest_sha256": authorization.manifest_sha256,
            "seed": self.seed,
            "condition": self.condition,
            "model_id": self.model_id,
            "provider_label": self.provider_label,
            "trajectory_directory": str(self.directory),
        }
        with claim.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._write_once("authorization-claim.json", payload)

    def run(self, provider: Provider, *, authorization: RetryBudgetAuthorization | None) -> dict[str, object]:
        if authorization is None:
            return self._reject("REJECTED_PRE_AUTHORIZATION", "missing verified RetryBudget authorization")
        if self.pilot_manifest_sha256 != authorization.manifest_sha256:
            return self._reject(
                "REJECTED_MANIFEST_BINDING",
                "trajectory artifact is not bound to the verified RetryBudget manifest",
            )
        try:
            authorization.verify_live()
            authorization.verify_trajectory(
                seed=self.seed,
                condition=self.condition,
                model_id=self.model_id,
                provider_label=self.provider_label,
            )
        except PermissionError as exc:
            return self._reject("REJECTED_MANIFEST_SCOPE", str(exc))
        try:
            self._claim_trajectory(authorization)
        except FileExistsError:
            return self._reject(
                "REJECTED_DUPLICATE_TRAJECTORY",
                "this manifest-bound trajectory was already claimed",
            )

        try:
            return self._run_authorized(provider, authorization=authorization)
        except Exception as exc:
            # Fail closed while retaining a redacted, finalized partial
            # trajectory. Do not archive exception text: SDK errors can carry
            # request details that do not belong in a research artifact.
            self._write_once("runner-error.json", {"exception_type": type(exc).__name__})
            return self._reject("RUNNER_ERROR", "runner exception")

    def _run_authorized(
        self, provider: Provider, *, authorization: RetryBudgetAuthorization,
    ) -> dict[str, object]:
        """Execute after the initial authorization checks have succeeded."""
        cumulative_utility, completed_work = 0, 0
        oracle_episode_utility = rollout_oracle_policy(self.seed)
        generation_limit = authorization.max_provider_generations()
        turn = 0
        while True:
            # This is checked before prompt rendering/request construction, so
            # a model cannot turn a declared seven-generation canary into a
            # larger paid experiment by repeatedly choosing nonterminal acts.
            if turn >= generation_limit:
                self._write_once(f"turn-{turn:02d}-generation-cap.json", {
                    "max_provider_generations": generation_limit,
                    "provider_generations_completed": turn,
                })
                return self._reject(
                    "REJECTED_PROVIDER_GENERATION_CAP",
                    "declared provider-generation cap reached before terminal outcome",
                )
            state = self._simulator.state
            prompt = prompt_record(
                condition=self.condition,
                seed=self.seed,
                state=state,
                observation_model=self.observation_model,
            )
            self._write_once(f"turn-{turn:02d}-input.json", prompt)
            self._write_once(f"turn-{turn:02d}-host.json", {
                "state": asdict(state),
                "observable_projection": observable_projection(state, self.observation_model),
                "action_values": RetryBudgetOracle.action_values(state),
                "best_actions": sorted(RetryBudgetOracle.best_actions(state)),
            })
            request_record = getattr(provider, "request_record", None)
            if not callable(request_record):
                raise TypeError("provider must expose a sanitized request_record")
            try:
                # A multi-turn trajectory has several paid generations. A
                # revocation or manifest replacement between them must halt the
                # next request while preserving the partial artifact.
                authorization.verify_live()
            except PermissionError as exc:
                return self._reject("REJECTED_AUTHORIZATION_REVOKED", str(exc))
            recorded_request = dict(request_record(str(prompt["prompt"])))
            self._write_once(f"turn-{turn:02d}-provider-request.json", recorded_request)
            try:
                authorization.verify_request_configuration(
                    provider_label=self.provider_label,
                    model_id=self.model_id,
                    request_record=recorded_request,
                )
            except PermissionError as exc:
                return self._reject("REJECTED_EXECUTION_CONFIG", str(exc))
            try:
                response = provider.complete(str(prompt["prompt"]))
            except Exception as exc:
                error_record = getattr(provider, "error_record", None)
                provider_error = dict(error_record(exc)) if callable(error_record) else {"exception_type": type(exc).__name__}
                self._write_once(f"turn-{turn:02d}-provider-error.json", provider_error)
                return self._reject("PROVIDER_ERROR", "provider exception")
            self._write_once(f"turn-{turn:02d}-provider-response.json", asdict(response))
            action = response.text.strip()
            if action not in RetryBudgetOracle.ACTIONS:
                return self._reject("MALFORMED_PROVIDER_RESPONSE", "response is not an exact RetryBudget action")
            outcome = self._simulator.step(action)  # type: ignore[arg-type]
            cumulative_utility += outcome.utility
            completed_work += int(outcome.completed_work)
            action_value_regret = RetryBudgetOracle.regret(state, action)
            result = {
                "accepted": True,
                "classification": "COMPLETED" if outcome.terminal else "RUNNING",
                "response_text": response.text,
                "action": action,
                "utility": outcome.utility,
                "cumulative_utility": cumulative_utility,
                "violation": outcome.violation,
                "completed_work": outcome.completed_work,
                "completed_work_total": completed_work,
                # This is a *local* dynamic-program value gap. It is useful
                # for turn-level diagnostics but must not be summed: each
                # value already assumes an optimal future continuation.
                "action_value_regret": action_value_regret,
                "oracle_actions": sorted(RetryBudgetOracle.best_actions(state)),
                "terminal": outcome.terminal,
            }
            self._write_once(f"turn-{turn:02d}-result.json", result)
            if outcome.terminal:
                self._write_once("trajectory-summary.json", {
                    "scenario": "RetryBudget-v0.2",
                    "seed": self.seed,
                    "condition": self.condition,
                    "model_id": self.model_id,
                    "provider_label": self.provider_label,
                    "decision_count": turn + 1,
                    "cumulative_utility": cumulative_utility,
                    "oracle_episode_utility": oracle_episode_utility,
                    "episode_utility_regret": oracle_episode_utility - cumulative_utility,
                    "completed_work_total": completed_work,
                    "terminal_classification": "COMPLETED",
                })
                self._finalize("COMPLETED")
                return result
            turn += 1
