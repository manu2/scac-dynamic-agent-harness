"""Validate and summarize the frozen ToolRoute OTel/Toxiproxy v0.2 cohort."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/api-otel-transport-v0.2/g2-calibrations/toolroute-otel-transport"
OUTPUT = REPO / "paper/analysis/toolroute_otel_transport_v0_2_analysis.json"
MODELS = ("gpt-5.6-sol", "claude-sonnet-5", "gemini-3.7-flash")
CONDITIONS = ("A", "B", "C")
REGIMES = ("latency", "connection_error", "http_error")


def rows() -> list[dict]:
    result = []
    for trial in sorted(ROOT.iterdir()):
        if not trial.is_dir() or not (trial / "manifest.json").exists():
            continue
        manifest = json.loads((trial / "manifest.json").read_text())
        provider = manifest.get("provider_run", {})
        if not provider.get("episode_id"):
            continue
        finalization = json.loads((trial / "finalization.json").read_text())
        for name, expected in finalization["artifact_sha256"].items():
            actual = hashlib.sha256((trial / name).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"invalid finalization hash: {trial / name}")
        decision = json.loads((trial / "model-decision.json").read_text())
        action = json.loads((trial / "action-result.json").read_text())
        result.append({
            "episode_id": provider["episode_id"],
            "model": provider["model_id"],
            "condition": manifest["condition"],
            "regime": manifest["regime"],
            "faulted_tool": manifest["faulted_tool"],
            "selected_action": decision["selected_action"],
            "observable_best_actions": decision["observable_best_actions"],
            "policy_regret_ms": float(decision["policy_regret"]),
            "live_action_success": bool(action["event"]["payload"]["success"]),
            "live_http_status": action["status_code"],
            "finalization_hashes_valid": True,
        })
    expected = {(model, condition, regime) for model in MODELS for condition in CONDITIONS for regime in REGIMES}
    observed = {(row["model"], row["condition"], row["regime"]) for row in result}
    duplicates = [cell for cell, n in Counter((r["model"], r["condition"], r["regime"]) for r in result).items() if n > 1]
    if len(result) != 27 or observed != expected or duplicates:
        raise ValueError(f"expected 27-cell model/condition/regime grid; rows={len(result)} missing={expected-observed} duplicates={duplicates}")
    return result


def main() -> None:
    cohort = rows()
    by_condition = []
    for condition in CONDITIONS:
        subset = [row for row in cohort if row["condition"] == condition]
        by_condition.append({
            "condition": condition,
            "decisions": len(subset),
            "successful_live_actions": sum(row["live_action_success"] for row in subset),
            "completion_rate": sum(row["live_action_success"] for row in subset) / len(subset),
            "mean_policy_regret_ms": mean(row["policy_regret_ms"] for row in subset),
            "observable_best_actions": sum(row["policy_regret_ms"] == 0 for row in subset),
        })
    payload = {
        "cohort": {"decisions": len(cohort), "models": MODELS, "conditions": CONDITIONS, "regimes": REGIMES, "evidence_class": "separate_live_transport_replication_not_pooled_with_toolroute_v1"},
        "condition_summary": by_condition,
        "rows": cohort,
        "validation": "all listed finalization hashes validated; complete frozen 3-model × A/B/C × 3-regime grid",
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"rows": len(cohort), "output": str(OUTPUT.relative_to(REPO))}))


if __name__ == "__main__":
    main()
