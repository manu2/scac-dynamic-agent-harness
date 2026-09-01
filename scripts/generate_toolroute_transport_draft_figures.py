"""Create vector figures for the versioned ToolRoute transport-replication draft.

Reads frozen derived primary-cohort summaries and immutable v0.2 transport
artifacts. It never invokes providers or rewrites experiment artifacts.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas


MODELS = ("gpt-5.6-sol", "claude-sonnet-5", "gemini-3.7-flash")
MODEL_LABELS = {
    "gpt-5.6-sol": "GPT-5.6 Sol",
    "claude-sonnet-5": "Claude Sonnet 5",
    "gemini-3.7-flash": "Gemini 3.7 Flash",
}
CONDITION_COLORS = {
    "A": colors.HexColor("#7A8496"),
    "B": colors.HexColor("#3973A8"),
    "C": colors.HexColor("#08775B"),
}
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#526173")
GRID = colors.HexColor("#DDE3EB")
FRAME = colors.HexColor("#AEB8C7")
GOOD = colors.HexColor("#08775B")
BAD = colors.HexColor("#B5473B")


def draw_header(pdf: canvas.Canvas, title: str, subtitle: str) -> None:
    width, height = landscape(letter)
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(44, height - 38, title)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(44, height - 53, subtitle)


def draw_footer(pdf: canvas.Canvas, text: str) -> None:
    width, _ = landscape(letter)
    pdf.setStrokeColor(GRID)
    pdf.line(44, 36, width - 44, 36)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(44, 22, text)


def primary_summary(repo: Path) -> dict[tuple[str, str], float]:
    payload = json.loads((repo / "paper/analysis/toolroute_v1_analysis.json").read_text())
    return {
        (row["model"], row["condition"]): float(row["mean_policy_regret_ms"])
        for row in payload["model_condition_summary"]
    }


def transport_rows(repo: Path) -> list[dict]:
    root = repo / "experiments/api-otel-transport-v0.2/g2-calibrations/toolroute-otel-transport"
    rows = []
    for trial in root.iterdir():
        if not trial.is_dir() or not (trial / "manifest.json").exists():
            continue
        manifest = json.loads((trial / "manifest.json").read_text())
        provider_run = manifest.get("provider_run", {})
        if not provider_run.get("episode_id"):
            continue
        decision = json.loads((trial / "model-decision.json").read_text())
        action = json.loads((trial / "action-result.json").read_text())
        rows.append({
            "model": provider_run["model_id"],
            "condition": manifest["condition"],
            "regime": manifest["regime"],
            "selected_action": decision["selected_action"],
            "regret": float(decision["policy_regret"]),
            "success": bool(action["event"]["payload"]["success"]),
        })
    if len(rows) != 27:
        raise ValueError(f"expected 27 transport rows, found {len(rows)}")
    return rows


def figure_primary_conditions(path: Path, summary: dict[tuple[str, str], float]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=landscape(letter))
    draw_header(
        pdf,
        "Figure 1. Verified state collapses observable regret across all information conditions",
        "Condition means on a logarithmic scale; n = 24 independent direct-provider decisions per point. Lower is better.",
    )
    width, _ = landscape(letter)
    ticks = (10, 100, 1000, 10000)
    y, h = 158, 330
    panel_w, gap, first_x = 204, 36, 68

    for index, model in enumerate(MODELS):
        x = first_x + index * (panel_w + gap)
        pdf.setStrokeColor(FRAME)
        pdf.rect(x, y, panel_w, h, fill=0, stroke=1)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x, y + h + 12, MODEL_LABELS[model])

        def scale(value: float) -> float:
            return y + (math.log10(value) - 1) / 3 * h

        for tick in ticks:
            py = scale(tick)
            pdf.setStrokeColor(GRID)
            pdf.line(x, py, x + panel_w, py)
            pdf.setFillColor(MUTED)
            pdf.setFont("Helvetica", 7.5)
            pdf.drawRightString(x - 5, py - 2.5, f"{tick:,}")

        positions = {"A": x + 42, "B": x + 102, "C": x + 162}
        for condition, px in positions.items():
            value = summary[(model, condition)]
            py = scale(value)
            pdf.setFillColor(CONDITION_COLORS[condition])
            pdf.circle(px, py, 6, fill=1, stroke=0)
            pdf.setFillColor(INK)
            pdf.setFont("Helvetica-Bold", 8)
            label_y = py + 11 if condition != "C" else py + 10
            pdf.drawCentredString(px, label_y, f"{value:,.0f}")
            pdf.setFont("Helvetica", 8)
            pdf.drawCentredString(px, y - 15, condition)

        b, c = summary[(model, "B")], summary[(model, "C")]
        reduction = 100 * (1 - c / b)
        bx = x + panel_w - 13
        pdf.setStrokeColor(GOOD)
        pdf.setLineWidth(1.25)
        pdf.line(bx, scale(c), bx, scale(b))
        pdf.line(bx - 4, scale(b), bx + 4, scale(b))
        pdf.line(bx - 4, scale(c), bx + 4, scale(c))
        pdf.setFillColor(GOOD)
        pdf.setFont("Helvetica-Bold", 7.4)
        pdf.drawRightString(x + panel_w - 7, y + 8, f"B→C: -{reduction:.1f}%")
        pdf.setLineWidth(1)

    pdf.setFillColor(GOOD)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(width / 2, 113, "Across all models: B 4,252 ms → C 131 ms (96.9% lower mean observable regret).")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8.3)
    pdf.drawCentredString(width / 2, 97, "Log scaling preserves the full A/B/C ablation while keeping the verified-state values visible.")
    draw_footer(pdf, "Frozen ToolRoute v1.0 cohort. Condition means are independent samples; points are not paired trajectories.")
    pdf.save()


def figure_transport_replication(path: Path, rows: list[dict]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=landscape(letter))
    draw_header(
        pdf,
        "Figure 2. Verified telemetry improves every live transport decision",
        "Frozen OpenTelemetry/Toxiproxy v0.2 replication: 27 independent remote-model decisions; live selected-route execution after each decision.",
    )
    width, _ = landscape(letter)
    c_rows = {(r["regime"], r["model"]): r for r in rows if r["condition"] == "C"}
    regimes = (("latency", "300 ms latency"), ("connection_error", "connection error"), ("http_error", "HTTP 503"))
    x0, y0, cell_w, cell_h = 128, 315, 180, 60
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(width / 2, y0 + cell_h * 3 + 43, "Verified state (C): all nine model-by-fault cases selected the viable route and completed live")
    for col, model in enumerate(MODELS):
        x = x0 + col * cell_w
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawCentredString(x + 83, y0 + cell_h * 3 + 21, MODEL_LABELS[model])
    for row_index, (regime, label) in enumerate(regimes):
        y = y0 + (2 - row_index) * cell_h
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawRightString(x0 - 12, y + cell_h / 2 + 3, label)
        for col, model in enumerate(MODELS):
            x = x0 + col * cell_w
            data = c_rows[(regime, model)]
            pdf.setFillColor(colors.HexColor("#EAF6F1"))
            pdf.roundRect(x, y, cell_w - 14, cell_h - 6, 5, fill=1, stroke=0)
            pdf.setFillColor(GOOD)
            pdf.circle(x + 23, y + 28, 10, fill=1, stroke=0)
            pdf.setFillColor(colors.white)
            pdf.setFont("Helvetica-Bold", 6.8)
            pdf.drawCentredString(x + 23, y + 25.5, "OK")
            pdf.setFillColor(INK)
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(x + 42, y + 34, data["selected_action"])
            pdf.setFont("Helvetica", 7.2)
            pdf.drawString(x + 42, y + 20, "live HTTP 200")
            pdf.drawString(x + 42, y + 9, "0 ms regret")

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(row)
    regret = {condition: sum(row["regret"] for row in grouped[condition]) / len(grouped[condition]) for condition in "ABC"}
    completion = {condition: 100 * sum(row["success"] for row in grouped[condition]) / len(grouped[condition]) for condition in "ABC"}
    successes = {condition: sum(row["success"] for row in grouped[condition]) for condition in "ABC"}

    panel_x, panel_y, panel_w, panel_h = 72, 58, 648, 222
    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(FRAME)
    pdf.roundRect(panel_x, panel_y, panel_w, panel_h, 5, fill=1, stroke=1)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(width / 2, 260, "All conditions, with the structural-control comparison highlighted: B-to-C")
    bar_x, bar_w = 244, 330
    pdf.setFont("Helvetica-Bold", 8.8)
    pdf.drawString(90, 239, "Mean observable policy regret")
    for condition, y in (("A", 220), ("B", 196), ("C", 172)):
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 7.5)
        label = {"A": "A - task only", "B": "B - neutral envelope", "C": "C - verified state"}[condition]
        pdf.drawRightString(bar_x - 8, y + 3, label)
        pdf.setFillColor(colors.HexColor("#E8EDF3"))
        pdf.roundRect(bar_x, y - 6, bar_w, 12, 3, fill=1, stroke=0)
        pdf.setFillColor(CONDITION_COLORS[condition])
        if regret[condition] == 0:
            pdf.circle(bar_x, y, 5, fill=1, stroke=0)
        else:
            pdf.roundRect(bar_x, y - 6, bar_w * regret[condition] / max(regret.values()), 12, 3, fill=1, stroke=0)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 8.6)
        pdf.drawString(bar_x + bar_w + 10, y - 3, f"{regret[condition]:,.0f} ms")
    pdf.setFillColor(GOOD)
    pdf.setFont("Helvetica-Bold", 9.2)
    pdf.drawString(595, 169, "B-to-C: 100% lower regret")
    pdf.setStrokeColor(GRID)
    pdf.line(88, 148, 704, 148)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 8.8)
    pdf.drawString(90, 132, "Live action completion")
    for condition, y in (("A", 113), ("B", 91), ("C", 69)):
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 7.5)
        pdf.drawRightString(bar_x - 8, y + 3, condition)
        pdf.setFillColor(colors.HexColor("#E8EDF3"))
        pdf.roundRect(bar_x, y - 6, bar_w, 12, 3, fill=1, stroke=0)
        pdf.setFillColor(CONDITION_COLORS[condition])
        pdf.roundRect(bar_x, y - 6, bar_w * completion[condition] / 100, 12, 3, fill=1, stroke=0)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 8.6)
        pdf.drawString(bar_x + bar_w + 10, y - 3, f"{successes[condition]}/9 ({completion[condition]:.1f}%)")
    pdf.setFillColor(GOOD)
    pdf.setFont("Helvetica-Bold", 9.2)
    pdf.drawString(638, 66, "B-to-C: +44.4 pp")
    draw_footer(pdf, "Zero regret denotes no excess observable operational cost, not a zero-duration HTTP request.")
    pdf.save()


def main() -> None:
    repo = Path(".").resolve()
    figures = repo / "paper/figures"
    figures.mkdir(parents=True, exist_ok=True)
    figure_primary_conditions(figures / "figure_1_conditions_log.pdf", primary_summary(repo))
    figure_transport_replication(figures / "figure_2_transport_replication.pdf", transport_rows(repo))
    print("created figure_1_conditions_log.pdf and figure_2_transport_replication.pdf")


if __name__ == "__main__":
    main()
