"""Regenerate ToolRoute v1.0 manuscript tables and figures from frozen trials.

The script reads only the three finished API-paper cohort roots. It does not
make provider calls or modify immutable experiment artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas

COHORT_DIRS = (
    Path("experiments/api-paper-v1.0-seed8"),
    Path("experiments/api-paper-v1.0-seeds9-10"),
    Path("experiments/api-paper-v1.0-seeds11-13"),
)
MODELS = ("gpt-5.6-sol", "claude-sonnet-5", "gemini-3.7-flash")
CONDITIONS = ("A", "B", "C")
MODEL_LABELS = {
    "gpt-5.6-sol": "GPT-5.6 Sol",
    "claude-sonnet-5": "Claude Sonnet 5",
    "gemini-3.7-flash": "Gemini 3.7 Flash",
}
COLORS = {"A": colors.HexColor("#8A94A6"), "B": colors.HexColor("#557CA8"), "C": colors.HexColor("#107A5A")}


def read_rows(repo: Path) -> list[dict]:
    rows = []
    for root in COHORT_DIRS:
        for result_path in sorted((repo / root).rglob("result.json")):
            manifest_path = result_path.with_name("manifest.json")
            finalization_path = result_path.with_name("finalization.json")
            if not manifest_path.exists() or not finalization_path.exists():
                raise ValueError(f"trial missing artifact beside {result_path}")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            result = json.loads(result_path.read_text(encoding="utf-8"))
            finalization = json.loads(finalization_path.read_text(encoding="utf-8"))
            if manifest.get("scenario") != "ToolRoute-v1.0-api":
                continue
            hashes = finalization.get("artifact_sha256")
            if result.get("classification") != "COMPLETED" or finalization.get("classification") != "COMPLETED" or not isinstance(hashes, dict):
                raise ValueError(f"incomplete trial: {result_path}")
            actual = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in result_path.parent.glob("*.json") if path.name != "finalization.json"
            }
            if hashes != actual:
                raise ValueError(f"finalization hashes do not validate: {result_path}")
            rows.append({
                "trial_directory": str(result_path.parent.relative_to(repo)),
                "provider": manifest["provider_label"],
                "model": manifest["model_id"],
                "seed": int(manifest["seed"]),
                "turn": int(manifest["turn"]),
                "condition": manifest["condition"],
                "action": result["action"],
                "policy_regret_ms": float(result["policy_regret"]),
                "latency_ms": float(result["latency_ms"]),
                "success": bool(result["success"]),
            })
    return rows


def validate(rows: list[dict]) -> None:
    expected = {(m, s, t, c) for m in MODELS for s in range(8, 14) for t in range(4) for c in CONDITIONS}
    observed = {(r["model"], r["seed"], r["turn"], r["condition"]) for r in rows}
    duplicates = [item for item, count in Counter((r["model"], r["seed"], r["turn"], r["condition"]) for r in rows).items() if count > 1]
    if len(rows) != 216 or observed != expected or duplicates:
        raise ValueError(f"expected frozen 216-cell grid; rows={len(rows)} missing={sorted(expected-observed)[:3]} duplicates={duplicates[:3]}")


def wilson(successes: int, n: int) -> tuple[float, float]:
    z, p = 1.96, successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt((p * (1-p) + z * z / (4*n)) / n) / denominator
    return centre-half, centre+half


def summaries(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    overall, by_model = [], []
    for condition in CONDITIONS:
        subset = [r for r in rows if r["condition"] == condition]
        successes = sum(r["success"] for r in subset)
        low, high = wilson(successes, len(subset))
        overall.append({
            "condition": condition, "decisions": len(subset),
            "mean_policy_regret_ms": mean(r["policy_regret_ms"] for r in subset),
            "successful_outcomes": successes, "completion_rate": successes / len(subset),
            "completion_wilson_low": low, "completion_wilson_high": high,
        })
    for model in MODELS:
        for condition in CONDITIONS:
            subset = [r for r in rows if r["model"] == model and r["condition"] == condition]
            successes = sum(r["success"] for r in subset)
            low, high = wilson(successes, len(subset))
            by_model.append({
                "model": model, "condition": condition, "decisions": len(subset),
                "mean_policy_regret_ms": mean(r["policy_regret_ms"] for r in subset),
                "successful_outcomes": successes, "completion_rate": successes / len(subset),
                "completion_wilson_low": low, "completion_wilson_high": high,
            })
    return overall, by_model


def block_bootstrap(rows: list[dict], left: str, right: str, metric: str, draws: int = 20000) -> dict:
    grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["model"], row["seed"], row["condition"])].append(float(row[metric]))
    blocks = [mean(grouped[(model, seed, left)]) - mean(grouped[(model, seed, right)])
              for model in MODELS for seed in range(8, 14)]
    rng = random.Random(20260831)
    sample_means = sorted(mean(rng.choice(blocks) for _ in blocks) for _ in range(draws))
    return {
        "estimate": mean(blocks), "bootstrap_95_low": sample_means[int(0.025*draws)],
        "bootstrap_95_high": sample_means[int(0.975*draws)], "blocks": len(blocks),
    }


def header(c: canvas.Canvas, title: str, subtitle: str) -> None:
    width, height = landscape(letter)
    # Explicit white paper avoids transparent-PDF rendering failures in dark viewers.
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#172033"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(48, height-42, title)
    c.setFillColor(colors.HexColor("#46546B"))
    c.setFont("Helvetica", 9.4)
    c.drawString(48, height-57, subtitle)


def footer(c: canvas.Canvas, note: str) -> None:
    width, _ = landscape(letter)
    c.setStrokeColor(colors.HexColor("#D8DEE8"))
    c.line(48, 35, width-48, 35)
    c.setFillColor(colors.HexColor("#526173"))
    c.setFont("Helvetica", 7.8)
    c.drawString(48, 22, note)


def bars(c: canvas.Canvas, x: float, y: float, width: float, height: float, values: dict[str, float], maximum: float, title: str, *, percent: bool) -> None:
    c.setStrokeColor(colors.HexColor("#AEB8C7"))
    c.rect(x, y, width, height, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#172033"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y+height+11, title)
    for tick in range(5):
        value, py = maximum*tick/4, y+height*tick/4
        c.setStrokeColor(colors.HexColor("#E5EAF1"))
        c.line(x, py, x+width, py)
        c.setFillColor(colors.HexColor("#526173"))
        c.setFont("Helvetica", 7.3)
        label = f"{value:.0f}%" if percent else f"{value:,.0f} ms"
        c.drawRightString(x-5, py-2.5, label)
    bar_width, gap = 34, (width-102)/4
    for index, condition in enumerate(CONDITIONS):
        bx, value = x+gap+index*(bar_width+gap), values[condition]
        bh = height*value/maximum if maximum else 0
        c.setFillColor(COLORS[condition])
        c.rect(bx, y, bar_width, bh, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#172033"))
        c.setFont("Helvetica-Bold", 7.6)
        label = f"{value:.1f}%" if percent else f"{value:,.0f}"
        c.drawCentredString(bx+bar_width/2, min(y+bh+5, y+height-5), label)
        c.setFont("Helvetica", 7.3)
        c.drawCentredString(bx+bar_width/2, y-12, condition)


def figure_relative(path: Path, summary: list[dict]) -> None:
    c = canvas.Canvas(str(path), pagesize=landscape(letter))
    width, _ = landscape(letter)
    header(c, "Figure 1. Verified tool state collapses policy regret within every model family",
           "Mean observable policy regret; each panel normalizes neutral same-shape control B to 100%. n = 24 decisions per bar.")
    lookup = {(r["model"], r["condition"]): r for r in summary}
    for index, model in enumerate(MODELS):
        baseline = lookup[(model, "B")]["mean_policy_regret_ms"]
        values = {condition: 100*lookup[(model, condition)]["mean_policy_regret_ms"]/baseline for condition in CONDITIONS}
        top = max(160, math.ceil(max(values.values())/20)*20)
        bars(c, 68+index*238, 180, 188, 310, values, top, MODEL_LABELS[model], percent=True)
    c.setFillColor(colors.HexColor("#107A5A"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width/2, 127, "Across all models, C is 3.1% of B's mean regret (131 ms vs 4,252 ms).")
    c.setFillColor(colors.HexColor("#46546B"))
    c.setFont("Helvetica", 8.4)
    c.drawCentredString(width/2, 111, "Normalization foregrounds within-model treatment effects; Figure A1 reports raw milliseconds.")
    footer(c, "ToolRoute v1.0 frozen cohort: 3 provider/model families x 6 seeds x 4 turns x 3 conditions. Lower is better.")
    c.save()


def figure_completion(path: Path, summary: list[dict]) -> None:
    c = canvas.Canvas(str(path), pagesize=landscape(letter))
    width, _ = landscape(letter)
    header(c, "Figure 2. Verified state improves operational completion across all model families",
           "Completion rate. n = 24 independent direct-provider decisions per bar; Wilson 95% intervals below each panel.")
    lookup = {(r["model"], r["condition"]): r for r in summary}
    for index, model in enumerate(MODELS):
        values = {condition: 100*lookup[(model, condition)]["completion_rate"] for condition in CONDITIONS}
        x = 68+index*238
        bars(c, x, 180, 188, 310, values, 100, MODEL_LABELS[model], percent=True)
        c.setFillColor(colors.HexColor("#46546B"))
        c.setFont("Helvetica", 6.8)
        note = "; ".join(f"{condition}: {100*lookup[(model,condition)]['completion_wilson_low']:.0f}-{100*lookup[(model,condition)]['completion_wilson_high']:.0f}%" for condition in CONDITIONS)
        c.drawCentredString(x+94, 160, note)
    c.setFillColor(colors.HexColor("#107A5A"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width/2, 127, "C completes 69/72 decisions (95.8%) versus 50/72 (69.4%) under the neutral envelope.")
    footer(c, "Completion is success of the selected route under the external ToolRoute evaluator. Three C wait choices remain in the denominator.")
    c.save()


def figure_raw(path: Path, summary: list[dict]) -> None:
    c = canvas.Canvas(str(path), pagesize=landscape(letter))
    header(c, "Figure A1. Raw observable policy regret by model family and information condition",
           "Absolute values corresponding to Figure 1. Separate panels preserve readable within-model scale. n = 24 decisions per bar.")
    lookup = {(r["model"], r["condition"]): r for r in summary}
    for index, model in enumerate(MODELS):
        values = {condition: lookup[(model, condition)]["mean_policy_regret_ms"] for condition in CONDITIONS}
        top = max(1000, math.ceil(max(values.values())/1000)*1000)
        bars(c, 68+index*238, 180, 188, 310, values, top, MODEL_LABELS[model], percent=False)
    footer(c, "Raw values are included for scale interpretation. Figure 1 normalizes B = 100% within each model to foreground the information contrast.")
    c.save()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("paper/analysis"))
    parser.add_argument("--figures", type=Path, default=Path("paper/figures"))
    args = parser.parse_args()
    repo = args.repo.resolve()
    output, figures = (repo/args.output).resolve(), (repo/args.figures).resolve()
    output.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    rows = read_rows(repo)
    validate(rows)
    rows.sort(key=lambda r: (r["model"], r["seed"], r["turn"], r["condition"]))
    overall, by_model = summaries(rows)
    reference = {r["condition"]: r for r in overall}
    analysis = {
        "cohort": {"decisions": len(rows), "models": list(MODELS), "seeds": list(range(8,14)), "turns": list(range(4)), "conditions": list(CONDITIONS)},
        "condition_summary": overall,
        "model_condition_summary": by_model,
        "descriptive_block_bootstrap": {
            "B_minus_C_policy_regret_ms": block_bootstrap(rows, "B", "C", "policy_regret_ms"),
            "B_minus_C_completion_rate": block_bootstrap(rows, "B", "C", "success"),
            "A_minus_C_policy_regret_ms": block_bootstrap(rows, "A", "C", "policy_regret_ms"),
            "B_to_C_regret_reduction_percent": 100*(1-reference["C"]["mean_policy_regret_ms"]/reference["B"]["mean_policy_regret_ms"]),
            "B_to_C_completion_gain_percentage_points": 100*(reference["C"]["completion_rate"]-reference["B"]["completion_rate"]),
        },
        "methods_note": "Bootstrap resamples 18 model-by-seed blocks (four shared environment turns per block). It is descriptive uncertainty and does not convert independent provider generations into paired model draws.",
    }
    write_csv(output/"toolroute_v1_decisions.csv", rows)
    write_csv(output/"toolroute_v1_condition_summary.csv", overall)
    write_csv(output/"toolroute_v1_model_condition_summary.csv", by_model)
    (output/"toolroute_v1_analysis.json").write_text(json.dumps(analysis, indent=2)+"\n", encoding="utf-8")
    figure_relative(figures/"figure_1_relative_regret.pdf", by_model)
    figure_completion(figures/"figure_2_completion.pdf", by_model)
    figure_raw(figures/"appendix_figure_a1_raw_regret.pdf", by_model)
    print(json.dumps({"rows": len(rows), "analysis": str(output.relative_to(repo)), "figures": str(figures.relative_to(repo))}))


if __name__ == "__main__":
    main()
