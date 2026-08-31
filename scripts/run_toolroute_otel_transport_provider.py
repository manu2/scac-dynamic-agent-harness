"""Execute one separately authorized OTel/Toxiproxy ToolRoute pilot decision.

The coordinator owns its loopback backends and proxy for the entire lifetime of
the monitor, provider decision, and selected live action.  This command fails
before constructing a provider request unless the distinct transport manifest
is hash-bound in provenance.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import os
from pathlib import Path

from run_toolroute_otel_transport_calibration import _run_regime, _write_once
from scac_harness.otel_transport_authorization import OTelTransportAuthorization
from scac_harness.toolroute_api import GeminiGenerateContentProvider


def _load_dotenv(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gemini-3.7-flash")
    parser.add_argument("--condition", choices=("A", "B", "C"), required=True)
    parser.add_argument("--regime", choices=("latency", "connection_error", "http_error"), required=True)
    parser.add_argument("--toxiproxy-server", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("manifests/toolroute_otel_transport_pilot.v0.1.json"))
    parser.add_argument("--provenance", type=Path, default=Path("PROVENANCE.json"))
    parser.add_argument("--dotenv", type=Path, default=Path(".env"))
    parser.add_argument("--experiments-root", type=Path, default=Path("experiments/api-otel-transport-pilot"))
    args = parser.parse_args()
    _load_dotenv(args.dotenv)
    authorization = OTelTransportAuthorization.load(provenance_path=args.provenance, manifest_path=args.manifest)
    authorization.verify_episode(regime=args.regime, condition=args.condition, model_id=args.model, provider_label="google")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required after authorization succeeds")
    provider = GeminiGenerateContentProvider(api_key=api_key, model=args.model, temperature=0.0, max_output_tokens=1024)

    def decide(condition: str, input_record: dict[str, object], directory: Path) -> str:
        prompt = input_record["prompt"]
        if not isinstance(prompt, str):
            raise TypeError("condition prompt must be text")
        authorization.verify_live()
        request_record = dict(provider.request_record(prompt))
        _write_once(directory, "provider-request.json", request_record)
        authorization.verify_request_configuration(
            provider_label="google", model_id=args.model, request_record=request_record,
        )
        try:
            response = provider.complete(prompt)
        except Exception as exc:
            _write_once(directory, "provider-error.json", dict(provider.error_record(exc)))
            raise
        _write_once(directory, "provider-response.json", asdict(response))
        return response.text

    directory = _run_regime(
        regime=args.regime, toxiproxy_server=args.toxiproxy_server,
        experiments_root=args.experiments_root, condition=args.condition,
        decision_callback=decide, run_kind="provider_pilot",
        run_metadata={
            "provider_label": "google",
            "model_id": args.model,
            "pilot_manifest_path": str(args.manifest),
            "pilot_manifest_sha256": authorization.manifest_sha256,
            "authorization": "manifest_hash_bound_before_provider_request",
        },
    )
    print(f"trial_directory={directory}")


if __name__ == "__main__":
    main()
