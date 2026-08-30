from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

from scac_harness.toolroute_api import (
    AnthropicMessagesProvider,
    GeminiGenerateContentProvider,
    OpenAICompatibleProvider,
    ProviderResponse,
    Tokenizer,
    ToolRouteAPIEpisode,
    ToolRouteAuthorization,
    ToolRouteObservationModel,
    WhitespaceTokenizer,
    _safe_provider_error,
    build_toolroute_observation_checkpoint,
)


class RecordingProvider:
    def __init__(self, response: str) -> None:
        self.response, self.prompts = response, []

    def complete(self, prompt: str) -> ProviderResponse:
        self.prompts.append(prompt)
        return ProviderResponse(self.response, request_id="mock-1", input_tokens=9, output_tokens=1)

    def request_record(self, prompt: str) -> dict[str, object]:
        return {"adapter": "test", "endpoint": "https://example.invalid", "body": {"prompt": prompt}}


class FailingProvider(RecordingProvider):
    def complete(self, prompt: str) -> ProviderResponse:
        self.prompts.append(prompt)
        raise RuntimeError("simulated provider outage")


def _tokenizer() -> Tokenizer:
    return Tokenizer(WhitespaceTokenizer.name, WhitespaceTokenizer.count)


def _authorization(tmp_path: Path) -> ToolRouteAuthorization:
    manifest = tmp_path / "frozen-pilot-manifest.json"
    manifest.write_text(json.dumps({"pilot": "toolroute", "authorized_episodes": [
        {"seed": 50, "turn": 1, "condition": condition, "model_id": "mock", "provider_label": "mock"}
        for condition in ("A", "B", "C")
    ]}) + "\n")
    provenance = tmp_path / "provenance.json"
    provenance.write_text(json.dumps({
        "toolroute_provider_trials_authorized": True,
        "toolroute_pilot_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    }))
    return ToolRouteAuthorization.load(provenance_path=provenance, pilot_manifest_path=manifest)


def test_api_episode_uses_full_checkpoint_and_exact_token_b_control(tmp_path: Path) -> None:
    c = ToolRouteAPIEpisode(seed=50, turn=1, condition="C", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock")
    b = ToolRouteAPIEpisode(seed=50, turn=1, condition="B", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock")
    assert c.snapshot["kind"] == "full_checkpoint"
    assert c.snapshot["base_snapshot_id"] is None
    assert c.tokenizer.count(c.prompt) == b.tokenizer.count(b.prompt)
    assert "HOST TELEMETRY" in c.prompt and "HOST TELEMETRY" in b.prompt
    assert "tool_alpha: window=6 succ=6 consec_fail=0 latency_ewma=1000.0ms" in b.prompt
    assert "tool_beta: window=6 succ=6 consec_fail=0 latency_ewma=1000.0ms" in b.prompt
    assert "retry_after=" not in b.prompt


def test_api_episode_fails_closed_without_authorization_and_finalizes(tmp_path: Path) -> None:
    provider = RecordingProvider("tool_alpha")
    episode = ToolRouteAPIEpisode(seed=50, turn=1, condition="A", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock")
    result = episode.run(provider, authorization=None)
    assert result["classification"] == "REJECTED_PRE_AUTHORIZATION"
    assert provider.prompts == []
    assert (episode.directory / "finalization.json").exists()


def test_api_episode_captures_raw_response_and_scores_visible_oracle(tmp_path: Path) -> None:
    episode = ToolRouteAPIEpisode(seed=50, turn=1, condition="C", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock")
    result = episode.run(RecordingProvider("tool_beta\n"), authorization=_authorization(tmp_path))
    assert result["accepted"] is True
    assert result["policy_regret"] == 0
    assert json.loads((episode.directory / "provider-response.json").read_text())["text"] == "tool_beta\n"
    assert json.loads((episode.directory / "provider-request.json").read_text())["body"]["prompt"] == episode.prompt
    finalization = json.loads((episode.directory / "finalization.json").read_text())
    assert finalization["classification"] == "COMPLETED"
    for filename, digest in finalization["artifact_sha256"].items():
        assert hashlib.sha256((episode.directory / filename).read_bytes()).hexdigest() == digest


def test_api_episode_archives_malformed_provider_response(tmp_path: Path) -> None:
    episode = ToolRouteAPIEpisode(seed=50, turn=1, condition="C", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock")
    result = episode.run(RecordingProvider("choose tool_beta"), authorization=_authorization(tmp_path))
    assert result["classification"] == "MALFORMED_PROVIDER_RESPONSE"
    assert (episode.directory / "finalization.json").exists()


def test_api_episode_finalizes_provider_exception_with_request_provenance(tmp_path: Path) -> None:
    episode = ToolRouteAPIEpisode(seed=50, turn=1, condition="A", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock")
    result = episode.run(FailingProvider("unused"), authorization=_authorization(tmp_path))
    assert result["classification"] == "PROVIDER_ERROR"
    assert (episode.directory / "provider-request.json").exists()
    assert (episode.directory / "provider-error.json").exists()
    finalization = json.loads((episode.directory / "finalization.json").read_text())
    assert "provider-error.json" in finalization["artifact_sha256"]
    assert "message" not in result["provider_error"]


def test_provider_request_records_never_include_credentials() -> None:
    prompt = "choose tool_alpha"
    providers = (
        OpenAICompatibleProvider(endpoint="https://api.openai.example/v1/chat/completions", api_key="openai-secret", model="model"),
        AnthropicMessagesProvider(api_key="anthropic-secret", model="model", api_version="2023-06-01"),
        GeminiGenerateContentProvider(api_key="gemini-secret", model="model"),
    )
    for provider in providers:
        encoded = json.dumps(provider.request_record(prompt))
        assert "secret" not in encoded
        assert "tools" not in encoded
        assert "max" in encoded


def test_openai_and_opus_default_requests_omit_sampling_controls() -> None:
    openai = OpenAICompatibleProvider(endpoint="https://api.openai.example/v1/chat/completions", api_key="key", model="gpt-5.6-terra")
    opus = AnthropicMessagesProvider(api_key="key", model="claude-opus-5", api_version="2023-06-01")
    assert "temperature" not in openai.request_record("x")["body"]
    assert "temperature" not in opus.request_record("x")["body"]


class _CountResponse:
    def __init__(self, payload: dict[str, int]) -> None:
        self.payload = payload

    def __enter__(self) -> "_CountResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_provider_native_token_counters_use_provider_count_endpoints() -> None:
    providers_and_payloads = (
        (OpenAICompatibleProvider(endpoint="https://api.openai.example/v1/chat/completions", api_key="key", model="gpt-5.6-sol"), {"input_tokens": 17}, "responses/input_tokens"),
        (AnthropicMessagesProvider(api_key="key", model="claude-sonnet-5", api_version="2023-06-01"), {"input_tokens": 17}, "messages/count_tokens"),
        (GeminiGenerateContentProvider(api_key="key", model="gemini-3.7-flash"), {"totalTokens": 17}, ":countTokens"),
    )
    for provider, payload, endpoint_fragment in providers_and_payloads:
        captured = []
        def opener(req: object, timeout: int) -> _CountResponse:
            captured.append(req)
            return _CountResponse(payload)
        with patch("scac_harness.toolroute_api.request.urlopen", opener):
            assert provider.count_tokens("choose tool_alpha") == 17
        assert endpoint_fragment in captured[0].full_url


def test_safe_provider_error_retains_structured_detail_but_redacts_key() -> None:
    exc = HTTPError("https://example.invalid", 400, "Bad Request", {}, io.BytesIO(b'{"error":{"message":"bad sk-secret"}}'))
    record = _safe_provider_error(exc, "sk-secret")
    assert record["http_status"] == 400
    assert record["provider_error"]["error"]["message"] == "bad [REDACTED]"


def test_api_episode_rejects_manifest_not_bound_in_provenance(tmp_path: Path) -> None:
    manifest = tmp_path / "pilot.json"
    manifest.write_text("{}\n")
    provenance = tmp_path / "provenance.json"
    provenance.write_text('{"toolroute_provider_trials_authorized": true, "toolroute_pilot_manifest_sha256": "wrong"}\n')
    try:
        ToolRouteAuthorization.load(provenance_path=provenance, pilot_manifest_path=manifest)
    except PermissionError as exc:
        assert "hash" in str(exc)
    else:
        raise AssertionError("unbound manifest authorization was accepted")


def test_api_episode_rechecks_revoked_authorization_before_provider_request(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    json.loads(authorization.provenance_path.read_text())
    authorization.provenance_path.write_text(json.dumps({
        "toolroute_provider_trials_authorized": False,
        "toolroute_pilot_manifest_sha256": authorization.pilot_manifest_sha256,
    }))
    provider = RecordingProvider("tool_beta")
    episode = ToolRouteAPIEpisode(seed=50, turn=1, condition="C", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock")
    result = episode.run(provider, authorization=authorization)
    assert result["classification"] == "REJECTED_MANIFEST_SCOPE"
    assert provider.prompts == []


def test_api_episode_rejects_an_undeclared_paid_episode(tmp_path: Path) -> None:
    episode = ToolRouteAPIEpisode(seed=51, turn=1, condition="C", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock")
    result = episode.run(RecordingProvider("tool_beta"), authorization=_authorization(tmp_path))
    assert result["classification"] == "REJECTED_MANIFEST_SCOPE"
    assert (episode.directory / "finalization.json").exists()


def test_observation_model_is_versioned_and_supports_nonzero_noise(tmp_path: Path) -> None:
    model = ToolRouteObservationModel(success_label_error_probability=0.25, delivery_delay_ms=100)
    episode = ToolRouteAPIEpisode(seed=50, turn=1, condition="C", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock", observation_model=model)
    manifest = json.loads((episode.directory / "manifest.json").read_text())
    assert manifest["observation_model"]["success_label_error_probability"] == 0.25
    assert episode.snapshot["observed_at_ms"] == 2122
    assert episode.snapshot["subsystem_observed_at_ms"]["tool_span"] == 2012


def test_side_effect_free_checkpoint_builder_matches_episode_snapshot(tmp_path: Path) -> None:
    model = ToolRouteObservationModel(delivery_delay_ms=100)
    expected, events = build_toolroute_observation_checkpoint(seed=50, turn=1, observation_model=model)
    episode = ToolRouteAPIEpisode(seed=50, turn=1, condition="C", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock", observation_model=model)
    assert episode.snapshot == expected
    assert [event.to_dict() for event in episode.raw_events] == [event.to_dict() for event in events]


def test_fixed_actions_are_defeated_by_the_balanced_schedule(tmp_path: Path) -> None:
    regrets = {action: [] for action in ("tool_alpha", "tool_beta", "wait")}
    for seed in range(6):
        for turn in range(4):
            episode = ToolRouteAPIEpisode(seed=seed, turn=turn, condition="A", experiments_root=tmp_path, tokenizer=_tokenizer(), model_id="mock", provider_label="mock")
            for action in regrets:
                regrets[action].append(float(episode._outcome(action)["policy_regret"]))
    assert all(sum(values) > 0 for values in regrets.values())
