"""Separate authorization guard for the OTel/Toxiproxy replication pilot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class OTelTransportAuthorization:
    """Bind one provider call to an independently frozen transport manifest."""

    provenance_path: Path
    manifest_path: Path
    manifest_sha256: str

    @classmethod
    def load(cls, *, provenance_path: Path, manifest_path: Path) -> "OTelTransportAuthorization":
        provenance = json.loads(Path(provenance_path).read_text(encoding="utf-8"))
        manifest_bytes = Path(manifest_path).read_bytes()
        manifest = json.loads(manifest_bytes)
        digest = hashlib.sha256(manifest_bytes).hexdigest()
        if not provenance.get("toolroute_otel_transport_provider_trials_authorized", False):
            raise PermissionError("toolroute_otel_transport_provider_trials_authorized=false")
        if manifest.get("status") != "FROZEN_AUTHORIZED":
            raise PermissionError("OTel transport manifest is not frozen and authorized")
        if provenance.get("toolroute_otel_transport_pilot_manifest_sha256") != digest:
            raise PermissionError("frozen OTel transport pilot manifest hash does not match provenance")
        return cls(Path(provenance_path), Path(manifest_path), digest)

    def verify_live(self) -> None:
        provenance = json.loads(self.provenance_path.read_text(encoding="utf-8"))
        manifest_bytes = self.manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        digest = hashlib.sha256(manifest_bytes).hexdigest()
        if not provenance.get("toolroute_otel_transport_provider_trials_authorized", False):
            raise PermissionError("OTel transport authorization was revoked before provider request")
        if manifest.get("status") != "FROZEN_AUTHORIZED":
            raise PermissionError("OTel transport manifest is no longer frozen and authorized")
        if digest != self.manifest_sha256 or provenance.get("toolroute_otel_transport_pilot_manifest_sha256") != digest:
            raise PermissionError("frozen OTel transport pilot manifest changed before provider request")

    def verify_episode(
        self, *, regime: str, condition: str, model_id: str, provider_label: str,
    ) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        target = {
            "regime": regime,
            "condition": condition,
            "model_id": model_id,
            "provider_label": provider_label,
        }
        episodes = manifest.get("authorized_episodes")
        if not isinstance(episodes, list) or target not in episodes:
            raise PermissionError("episode is outside the frozen OTel transport manifest")

    def verify_request_configuration(
        self, *, provider_label: str, model_id: str, request_record: Mapping[str, object],
    ) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        expectations = manifest.get("provider_request_expectations")
        if not isinstance(expectations, list):
            raise PermissionError("manifest lacks provider request expectations")
        expected = next((item for item in expectations if isinstance(item, Mapping)
                         and item.get("provider_label") == provider_label and item.get("model_id") == model_id), None)
        if expected is None or request_record.get("adapter") != expected.get("adapter"):
            raise PermissionError("provider adapter differs from frozen OTel transport manifest")
        body = request_record.get("body")
        required = expected.get("required_body_fields")
        if not isinstance(body, Mapping) or not isinstance(required, Mapping):
            raise PermissionError("provider request shape is invalid")
        for field, value in required.items():
            if body.get(field) != value:
                raise PermissionError(f"provider request field {field!r} differs from manifest")
        forbidden = expected.get("forbidden_body_fields", [])
        if not isinstance(forbidden, list) or any(field in body for field in forbidden):
            raise PermissionError("provider request contains a forbidden manifest field")
