"""Retain model-free calibration of the frozen ToolRoute observation model."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
from uuid import uuid4

from scac_harness.scenarios.toolroute import ToolRouteOracle
from scac_harness.toolroute_api import ToolRouteObservationModel, build_toolroute_observation_checkpoint


def _write_once(directory: Path, filename: str, value: object) -> None:
    target = directory / filename
    temporary = directory / f".{filename}.{uuid4().hex}.tmp"
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush(); os.fsync(handle.fileno())
    try:
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    root = Path("experiments") / "g2-calibrations" / "toolroute-observation"
    directory = root / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid4().hex}"
    directory.mkdir(parents=True, mode=0o700)
    configurations = {
        "baseline": ToolRouteObservationModel(),
        "label_error_10pct": ToolRouteObservationModel(success_label_error_probability=0.10),
        "event_drop_10pct": ToolRouteObservationModel(event_drop_probability=0.10),
        "delivery_delay_500ms": ToolRouteObservationModel(delivery_delay_ms=500),
        "stale_delivery_2500ms": ToolRouteObservationModel(delivery_delay_ms=2500),
    }
    _write_once(directory, "manifest.json", {
        "kind": "toolroute_observation_model_calibration_v1", "not_model_evidence": True,
        "seeds": list(range(6)), "turns": list(range(4)), "minimum_observable_margin_ms": 50.0,
        "configurations": {name: asdict(config) for name, config in configurations.items()},
    })
    records: list[dict[str, object]] = []
    for name, config in configurations.items():
        for seed in range(6):
            for turn in range(4):
                snapshot, events = build_toolroute_observation_checkpoint(seed=seed, turn=turn, observation_model=config)
                try:
                    margin = ToolRouteOracle.observable_margin(snapshot)
                    regrets = {action: ToolRouteOracle.observable_regret(snapshot, action) for action in ("tool_alpha", "tool_beta", "wait")}
                    tool_observed = snapshot["subsystem_observed_at_ms"].get("tool_span")
                    age_ms = int(snapshot["observed_at_ms"]) - int(tool_observed) if tool_observed is not None else None
                    eligible = margin >= 50.0 and age_ms is not None and age_ms <= int(snapshot["fresh_for_ms"])
                    error = None
                except (ValueError, KeyError, AssertionError) as exc:
                    margin, regrets, eligible, error = None, None, False, repr(exc)
                records.append({"configuration": name, "seed": seed, "turn": turn, "eligible": eligible,
                                "observable_margin_ms": margin, "tool_age_ms": age_ms, "fixed_policy_regret": regrets,
                                "error": error, "raw_events": [event.to_dict() for event in events], "snapshot": snapshot})
    _write_once(directory, "state-records.json", {"records": records})
    summary: dict[str, object] = {}
    for name in configurations:
        rows = [row for row in records if row["configuration"] == name]
        eligible = [row for row in rows if row["eligible"]]
        margins = [float(row["observable_margin_ms"]) for row in eligible if row["observable_margin_ms"] is not None]
        fixed_mean = {action: statistics.mean(float(row["fixed_policy_regret"][action]) for row in eligible) for action in ("tool_alpha", "tool_beta", "wait")} if eligible else {}
        summary[name] = {"states": len(rows), "eligible_states": len(eligible), "excluded_states": len(rows) - len(eligible),
                         "minimum_margin_ms": min(margins) if margins else None, "mean_fixed_policy_regret": fixed_mean}
    _write_once(directory, "summary.json", summary)
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.glob("*.json"))}
    _write_once(directory, "finalization.json", {"classification": "COMPLETED", "artifact_sha256": hashes})
    print(directory)


if __name__ == "__main__":
    main()
