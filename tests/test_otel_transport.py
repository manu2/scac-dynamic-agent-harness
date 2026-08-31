from __future__ import annotations

import pytest
import hashlib
import json
from pathlib import Path

from scac_harness.otel_transport_authorization import OTelTransportAuthorization
from scac_harness.otel_transport_manifest import validate_cross_model_pilot_manifest
from scac_harness.otel_transport import OTEL_HTTP_SOURCE, event_from_http_client_span


def _span(*, status: int | None, error_status: bool = False) -> dict[str, object]:
    attributes: dict[str, object] = {"http.request.method": "GET", "server.address": "127.0.0.1"}
    if status is not None:
        attributes["http.response.status_code"] = status
    return {
        "start_time_unix_nano": 1_000_000_000,
        "end_time_unix_nano": 1_250_000_000,
        "status_code": "StatusCode.ERROR" if error_status else "StatusCode.UNSET",
        "span_id": "abcd",
        "trace_id": "0123",
        "attributes": attributes,
    }


def test_otel_http_span_maps_success_without_fabricating_fields() -> None:
    event = event_from_http_client_span(tool_id="tool_alpha", raw_span=_span(status=200))
    assert event.source == OTEL_HTTP_SOURCE
    assert event.payload["success"] is True
    assert event.payload["error_class"] == "NONE"
    assert event.payload["latency_ms"] == 250.0


def test_otel_http_span_maps_http_and_transport_failures_distinctly() -> None:
    http_failure = event_from_http_client_span(tool_id="tool_beta", raw_span=_span(status=503))
    transport_failure = event_from_http_client_span(tool_id="tool_beta", raw_span=_span(status=None, error_status=True))
    assert http_failure.payload["error_class"] == "HTTP_503"
    assert transport_failure.payload["error_class"] == "CONNECTION_ERROR"


def test_otel_http_adapter_rejects_missing_identity_or_failure_evidence() -> None:
    no_endpoint = _span(status=200)
    no_endpoint["attributes"] = {"http.request.method": "GET"}
    with pytest.raises(ValueError, match="identifiable"):
        event_from_http_client_span(tool_id="tool_alpha", raw_span=no_endpoint)

    unclassified_failure = _span(status=None)
    with pytest.raises(ValueError, match="neither response status nor error type"):
        event_from_http_client_span(tool_id="tool_alpha", raw_span=unclassified_failure)


def test_transport_provider_authorization_is_separate_and_fail_closed(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "status": "FROZEN_AUTHORIZED",
        "authorized_episodes": [{"regime": "latency", "condition": "C", "model_id": "gemini", "provider_label": "google"}],
        "provider_request_expectations": [{
            "provider_label": "google", "model_id": "gemini", "adapter": "test",
            "required_body_fields": {"temperature": 0.0}, "forbidden_body_fields": ["tools"],
        }],
    }), encoding="utf-8")
    provenance = tmp_path / "provenance.json"
    provenance.write_text(json.dumps({"toolroute_otel_transport_provider_trials_authorized": False}), encoding="utf-8")
    with pytest.raises(PermissionError, match="authorized=false"):
        OTelTransportAuthorization.load(provenance_path=provenance, manifest_path=manifest)

    provenance.write_text(json.dumps({
        "toolroute_otel_transport_provider_trials_authorized": True,
        "toolroute_otel_transport_pilot_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    }), encoding="utf-8")
    authorization = OTelTransportAuthorization.load(provenance_path=provenance, manifest_path=manifest)
    authorization.verify_episode(regime="latency", condition="C", model_id="gemini", provider_label="google")
    with pytest.raises(PermissionError, match="forbidden"):
        authorization.verify_request_configuration(
            provider_label="google", model_id="gemini", request_record={"adapter": "test", "body": {"temperature": 0.0, "tools": []}},
        )


def test_v02_transport_manifest_is_complete_and_rejects_triads_with_changed_order() -> None:
    manifest_path = Path(__file__).parents[1] / "manifests" / "toolroute_otel_transport_pilot.v0.2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_cross_model_pilot_manifest(manifest)
    changed = json.loads(json.dumps(manifest))
    changed["authorized_episodes"][3]["option_order"] = ["tool_beta", "tool_alpha", "wait"]
    with pytest.raises(ValueError, match="option order"):
        validate_cross_model_pilot_manifest(changed)
