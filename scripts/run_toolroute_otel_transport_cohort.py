"""Run exactly one frozen v0.2 OTel/Toxiproxy transport-pilot episode.

This command deliberately takes an ``episode_id`` rather than independently
chosen condition/fault/order arguments.  The manifest is the sole source of
those experimental choices, preventing a coordinator from accidentally
changing the treatment, endpoint assignment, or action order at run time.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
from typing import Mapping

from run_toolroute_otel_transport_calibration import _run_regime, _write_once
from scac_harness.otel_transport_authorization import OTelTransportAuthorization
from scac_harness.otel_transport_manifest import validate_cross_model_pilot_manifest
from scac_harness.toolroute_api import (
    AnthropicMessagesProvider,
    GeminiGenerateContentProvider,
    OpenAICompatibleProvider,
)


def _load_dotenv(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _provider(*, provider_label: str, model_id: str, manifest: Mapping[str, object]):
    expectations = manifest.get("provider_request_expectations")
    expected = next((item for item in expectations if isinstance(item, Mapping)
                     and item.get("provider_label") == provider_label and item.get("model_id") == model_id), None) if isinstance(expectations, list) else None
    if not isinstance(expected, Mapping):
        raise PermissionError("provider/model has no frozen request expectation")
    required = expected.get("required_body_fields")
    if not isinstance(required, Mapping):
        raise PermissionError("provider request expectation is malformed")
    if provider_label == "google":
        generation = required.get("generationConfig")
        if not isinstance(generation, Mapping):
            raise PermissionError("Gemini generationConfig is missing")
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required after authorization succeeds")
        return GeminiGenerateContentProvider(api_key=key, model=model_id,
                                             temperature=float(generation["temperature"]),
                                             max_output_tokens=int(generation["maxOutputTokens"]))
    if provider_label == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is required after authorization succeeds")
        return AnthropicMessagesProvider(api_key=key, model=model_id, api_version="2023-06-01",
                                         temperature=required.get("temperature"),
                                         max_output_tokens=int(required["max_tokens"]))
    if provider_label == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required after authorization succeeds")
        return OpenAICompatibleProvider(endpoint="https://api.openai.com/v1/chat/completions", api_key=key,
                                        model=model_id, temperature=required.get("temperature"),
                                        max_output_tokens=int(required["max_completion_tokens"]))
    raise PermissionError("unsupported frozen provider label")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--toxiproxy-server", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("manifests/toolroute_otel_transport_pilot.v0.2.json"))
    parser.add_argument("--provenance", type=Path, default=Path("PROVENANCE.json"))
    parser.add_argument("--dotenv", type=Path, default=Path(".env"))
    parser.add_argument("--experiments-root", type=Path, default=Path("experiments/api-otel-transport-v0.2"))
    args = parser.parse_args()
    _load_dotenv(args.dotenv)
    authorization = OTelTransportAuthorization.load(provenance_path=args.provenance, manifest_path=args.manifest)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_cross_model_pilot_manifest(manifest)
    episode = authorization.episode_spec(episode_id=args.episode_id)
    provider_label, model_id = str(episode["provider_label"]), str(episode["model_id"])
    provider = _provider(provider_label=provider_label, model_id=model_id, manifest=manifest)
    condition = str(episode["condition"])

    def decide(received_condition: str, input_record: dict[str, object], directory: Path) -> str:
        if received_condition != condition:
            raise RuntimeError("coordinator condition differs from frozen episode")
        prompt = input_record.get("prompt")
        if not isinstance(prompt, str):
            raise TypeError("condition prompt must be text")
        authorization.verify_live()
        request_record = dict(provider.request_record(prompt))
        _write_once(directory, "provider-request.json", request_record)
        authorization.verify_request_configuration(
            provider_label=provider_label, model_id=model_id, request_record=request_record,
        )
        try:
            response = provider.complete(prompt)
        except Exception as exc:
            _write_once(directory, "provider-error.json", dict(provider.error_record(exc)))
            raise
        _write_once(directory, "provider-response.json", asdict(response))
        return response.text

    option_order = tuple(str(value) for value in episode["option_order"])
    if len(option_order) != 3:
        raise PermissionError("frozen option order is malformed")
    directory = _run_regime(
        regime=str(episode["regime"]), toxiproxy_server=args.toxiproxy_server,
        experiments_root=args.experiments_root, condition=condition,
        decision_callback=decide, run_kind="provider_pilot_v0.2",
        faulted_tool=str(episode["faulted_tool"]), option_order=option_order,
        run_metadata={
            "provider_label": provider_label,
            "model_id": model_id,
            "episode_id": args.episode_id,
            "sequence": episode["sequence"],
            "pilot_manifest_path": str(args.manifest),
            "pilot_manifest_sha256": authorization.manifest_sha256,
            "authorization": "manifest_hash_bound_before_provider_request",
        },
    )
    print(json.dumps({"episode_id": args.episode_id, "trial_directory": str(directory)}))


if __name__ == "__main__":
    main()
