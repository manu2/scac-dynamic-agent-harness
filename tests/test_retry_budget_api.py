from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scac_harness.retry_budget_api import RetryBudgetAPITrajectory, RetryBudgetAuthorization
from scac_harness.scenarios.retry_budget import RetryBudgetOracle, RetryBudgetSimulator
from scac_harness.toolroute_api import ProviderResponse


class _FakeProvider:
    def __init__(self, actions: list[str]) -> None:
        self.actions = actions
        self.request_calls = 0

    def request_record(self, prompt: str) -> dict[str, object]:
        return {"adapter": "fake_v1", "endpoint": "https://example.invalid", "body": {"model": "fake-model"}}

    def complete(self, prompt: str) -> ProviderResponse:
        self.request_calls += 1
        return ProviderResponse(self.actions.pop(0), raw_response={"fake": True})

    def error_record(self, exc: Exception) -> dict[str, object]:
        return {"exception_type": type(exc).__name__}


def _oracle_actions(seed: int) -> list[str]:
    simulator = RetryBudgetSimulator(seed)
    actions: list[str] = []
    while True:
        action = sorted(RetryBudgetOracle.best_actions(simulator.state))[0]
        actions.append(action)
        if simulator.step(action).terminal:
            return actions


def _authorization(
    tmp_path: Path, *, seed: int = 5, max_provider_generations: int = 7,
) -> RetryBudgetAuthorization:
    manifest = {
        "authorized_trajectory_grids": [{
            "model_id": "fake-model", "provider_label": "fake", "seeds": [seed], "conditions": ["C"],
        }],
        "provider_request_expectations": [{
            "model_id": "fake-model", "provider_label": "fake", "adapter": "fake_v1",
            "endpoint_suffix": ".invalid", "required_body_fields": {"model": "fake-model"}, "forbidden_body_fields": ["tools"],
        }],
        "max_provider_generations": max_provider_generations,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    provenance_path = tmp_path / "PROVENANCE.json"
    provenance_path.write_text(json.dumps({
        "retrybudget_provider_trials_authorized": True,
        "retrybudget_pilot_manifest_sha256": digest,
    }), encoding="utf-8")
    return RetryBudgetAuthorization.load(provenance_path=provenance_path, manifest_path=manifest_path)


def test_missing_authorization_fails_closed_and_finalizes(tmp_path: Path) -> None:
    episode = RetryBudgetAPITrajectory(
        seed=5, condition="C", experiments_root=tmp_path, model_id="fake-model", provider_label="fake",
    )
    result = episode.run(_FakeProvider([]), authorization=None)
    assert result["classification"] == "REJECTED_PRE_AUTHORIZATION"
    assert (episode.directory / "finalization.json").exists()


def test_authorized_full_trajectory_is_auditable_and_hides_oracle_from_prompt(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    episode = RetryBudgetAPITrajectory(
        seed=5, condition="C", experiments_root=tmp_path, model_id="fake-model", provider_label="fake",
        pilot_manifest_sha256=authorization.manifest_sha256,
    )
    result = episode.run(_FakeProvider(_oracle_actions(5)), authorization=authorization)
    assert result["classification"] == "COMPLETED"
    assert result["action_value_regret"] == 0
    inputs = sorted(episode.directory.glob("turn-*-input.json"))
    assert inputs
    assert all("action_values" not in json.loads(path.read_text())["prompt"] for path in inputs)
    finalization = json.loads((episode.directory / "finalization.json").read_text())
    actual = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in episode.directory.glob("*.json") if path.name != "finalization.json"
    }
    assert finalization["artifact_sha256"] == actual
    summary = json.loads((episode.directory / "trajectory-summary.json").read_text())
    assert summary["decision_count"] == len(inputs)
    assert summary["episode_utility_regret"] == 0


def test_unexpected_runner_error_is_finalized_without_exception_text(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)

    class _BrokenProvider(_FakeProvider):
        def request_record(self, prompt: str) -> dict[str, object]:
            raise RuntimeError("secret-bearing request detail must not be retained")

    episode = RetryBudgetAPITrajectory(
        seed=5, condition="C", experiments_root=tmp_path, model_id="fake-model", provider_label="fake",
        pilot_manifest_sha256=authorization.manifest_sha256,
    )
    result = episode.run(_BrokenProvider([]), authorization=authorization)
    assert result["classification"] == "RUNNER_ERROR"
    error = json.loads((episode.directory / "runner-error.json").read_text())
    assert error == {"exception_type": "RuntimeError"}
    assert (episode.directory / "finalization.json").exists()


def test_generation_cap_prevents_an_unbounded_nonterminal_trajectory(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path, max_provider_generations=1)
    provider = _FakeProvider(["checkpoint"])
    episode = RetryBudgetAPITrajectory(
        seed=5, condition="C", experiments_root=tmp_path, model_id="fake-model", provider_label="fake",
        pilot_manifest_sha256=authorization.manifest_sha256,
    )
    result = episode.run(provider, authorization=authorization)
    assert result["classification"] == "REJECTED_PROVIDER_GENERATION_CAP"
    assert provider.request_calls == 1
    cap = json.loads((episode.directory / "turn-01-generation-cap.json").read_text())
    assert cap["max_provider_generations"] == 1
    assert (episode.directory / "finalization.json").exists()


def test_second_manifest_bound_trajectory_is_rejected_before_provider_call(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    first = RetryBudgetAPITrajectory(
        seed=5, condition="C", experiments_root=tmp_path, model_id="fake-model", provider_label="fake",
        pilot_manifest_sha256=authorization.manifest_sha256,
    )
    first_provider = _FakeProvider(_oracle_actions(5))
    assert first.run(first_provider, authorization=authorization)["classification"] == "COMPLETED"
    duplicate = RetryBudgetAPITrajectory(
        seed=5, condition="C", experiments_root=tmp_path, model_id="fake-model", provider_label="fake",
        pilot_manifest_sha256=authorization.manifest_sha256,
    )
    duplicate_provider = _FakeProvider([])
    result = duplicate.run(duplicate_provider, authorization=authorization)
    assert result["classification"] == "REJECTED_DUPLICATE_TRAJECTORY"
    assert duplicate_provider.request_calls == 0
    assert (duplicate.directory / "finalization.json").exists()


def test_malformed_response_is_retained_and_finalized(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    episode = RetryBudgetAPITrajectory(
        seed=5, condition="C", experiments_root=tmp_path, model_id="fake-model", provider_label="fake",
        pilot_manifest_sha256=authorization.manifest_sha256,
    )
    result = episode.run(_FakeProvider(["I choose retry"]), authorization=authorization)
    assert result["classification"] == "MALFORMED_PROVIDER_RESPONSE"
    assert (episode.directory / "turn-00-provider-response.json").exists()
    assert (episode.directory / "finalization.json").exists()


def test_trajectory_artifact_must_bind_the_verified_manifest(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    episode = RetryBudgetAPITrajectory(
        seed=5, condition="C", experiments_root=tmp_path, model_id="fake-model", provider_label="fake",
        pilot_manifest_sha256="not-the-manifest-digest",
    )
    result = episode.run(_FakeProvider([]), authorization=authorization)
    assert result["classification"] == "REJECTED_MANIFEST_BINDING"
    assert (episode.directory / "finalization.json").exists()
