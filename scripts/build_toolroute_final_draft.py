"""Build a polished final-review PDF for the ToolRoute manuscript.

This intentionally uses ReportLab because the workspace has no LaTeX engine.
It embeds the frozen-cohort figures and does not access providers or raw trial
artifacts. The Markdown manuscript remains the canonical prose source.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)


REPO = Path(__file__).resolve().parents[1]
FIGURES = (
    "figure_1_relative_regret.pdf",
    "figure_2_completion.pdf",
    "appendix_figure_a1_raw_regret.pdf",
)
AUTHORS = "Manu Agrawal and Shrey Nagpal"


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23,
                                alignment=TA_CENTER, textColor=colors.HexColor("#142033"), spaceAfter=7),
        "authors": ParagraphStyle("authors", parent=base["Normal"], fontName="Helvetica", fontSize=10.2, leading=13,
                                  alignment=TA_CENTER, textColor=colors.HexColor("#526173"), spaceAfter=2),
        "review": ParagraphStyle("review", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8.2, leading=10,
                                 alignment=TA_CENTER, textColor=colors.HexColor("#7A4B12"), spaceAfter=14),
        "abstract_head": ParagraphStyle("abstract_head", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10.2,
                                        leading=12, alignment=TA_LEFT, textColor=colors.HexColor("#142033")),
        "abstract": ParagraphStyle("abstract", parent=base["BodyText"], fontName="Helvetica", fontSize=9.35, leading=13,
                                   alignment=TA_JUSTIFY, leftIndent=18, rightIndent=18, spaceAfter=12),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=13.2, leading=16,
                             textColor=colors.HexColor("#142033"), spaceBefore=13, spaceAfter=6, keepWithNext=True),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.8, leading=13,
                             textColor=colors.HexColor("#142033"), spaceBefore=9, spaceAfter=4, keepWithNext=True),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.25, leading=13,
                               alignment=TA_JUSTIFY, spaceAfter=7),
        "caption": ParagraphStyle("caption", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8.15,
                                  leading=10.4, alignment=TA_CENTER, textColor=colors.HexColor("#46546B"), spaceAfter=9),
        "reference": ParagraphStyle("reference", parent=base["Normal"], fontName="Helvetica", fontSize=8.2, leading=10.5,
                                    alignment=TA_LEFT, leftIndent=12, firstLineIndent=-12, spaceAfter=4),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10.2,
                                alignment=TA_JUSTIFY, textColor=colors.HexColor("#46546B"), spaceAfter=6),
        "table_head": ParagraphStyle("table_head", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.6,
                                      leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#142033")),
        "table_cell": ParagraphStyle("table_cell", parent=base["Normal"], fontName="Helvetica", fontSize=7.25,
                                      leading=9, alignment=TA_LEFT, textColor=colors.HexColor("#142033")),
    }


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def render_figures(temp_dir: Path) -> dict[str, Path]:
    rendered = {}
    for filename in FIGURES:
        source = REPO / "paper" / "figures" / filename
        target = temp_dir / f"{source.stem}.png"
        subprocess.run(["sips", "-s", "format", "png", "-Z", "2400", str(source), "--out", str(target)],
                       check=True, capture_output=True, text=True)
        if not target.exists():
            raise RuntimeError(f"failed to render {source}")
        # The publication caption supplies the title and interpretation. Crop
        # the chart panel itself to remove redundant burned-in title/footer.
        with PillowImage.open(target) as image:
            width, height = image.size
            panel = image.crop((round(width * 0.06), round(height * 0.14),
                                round(width * 0.94), round(height * 0.76)))
            panel.convert("RGB").save(target)
        rendered[filename] = target
    return rendered


def figure(path: Path, caption: str, width: float, style: ParagraphStyle) -> KeepTogether:
    image = Image(str(path))
    image._restrictSize(width, 3.72 * inch)
    return KeepTogether([image, Spacer(1, 3), p(caption, style)])


def table(data, widths, s):
    wrapped = [[p(str(cell), s["table_head"] if row_index == 0 else s["table_cell"])
                for cell in row] for row_index, row in enumerate(data)]
    result = Table(wrapped, colWidths=widths, repeatRows=1, hAlign="CENTER")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F0FA")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#142033")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C6D1DF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return result


def footer(canvas, doc):
    canvas.saveState()
    width, _ = letter
    # A physical white page prevents transparent-PDF dark-viewer rendering.
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, width, letter[1], fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#D7DFE9"))
    canvas.line(doc.leftMargin, 0.52 * inch, width - doc.rightMargin, 0.52 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#526173"))
    canvas.drawString(doc.leftMargin, 0.34 * inch, "Agent Harness Awareness - ToolRoute final-review draft")
    canvas.drawRightString(width - doc.rightMargin, 0.34 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(output: Path) -> None:
    s = styles()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="toolroute-final-figures-") as temp:
        rendered = render_figures(Path(temp))
        doc = SimpleDocTemplate(
            str(output), pagesize=letter, leftMargin=0.72*inch, rightMargin=0.72*inch,
            topMargin=0.68*inch, bottomMargin=0.7*inch, title="Agent Harness Awareness",
            author=AUTHORS,
        )
        story = []
        story += [
            p("Agent Harness Awareness: Verified Operational State as a First-Class Input to Tool-Using Agents", s["title"]),
            p("Manu Agrawal &nbsp;&nbsp;&middot;&nbsp;&nbsp; Shrey Nagpal", s["authors"]),
            p("Final-review proof - formatted from the frozen ToolRoute v1.0 cohort; not yet submitted", s["review"]),
            p("Abstract", s["abstract_head"]),
            p("Tool-using agents are commonly given a task and API descriptions while remaining unaware of the operational state of the harness in which they act. This operational blindness makes a feasible route and a degraded route look identical at the moment the agent chooses. We introduce <b>Agent Harness Awareness</b>, a closed-loop design in which compact, fresh, host-verified execution state becomes a first-class input to agent decision making while measurement, scoring, and enforcement remain outside the model. We instantiate the idea in ToolRoute, a controlled routing benchmark with two functionally equivalent tools and seeded changes in observed latency and reliability. Across 216 frozen, hash-finalized direct-provider decisions from GPT-5.6 Sol, Claude Sonnet 5, and Gemini 3.7 Flash, truthful tool-health state reduced mean observable policy regret by 96.9% relative to a neutral same-shape telemetry control (4,252 ms to 131 ms) and increased operational completion from 69.4% to 95.8%. The effect appears in all three model families. These findings establish a foundational systems principle: operational observability can be an active control input, not merely an artifact for human dashboards and post-hoc debugging.", s["abstract"]),
            p("<b>Keywords:</b> tool-using agents; observability; telemetry; agent control; systems; evaluation", s["small"]),
            p("1. From operational blindness to active control", s["h1"]),
            p("An agent can reason carefully about user intent and tool semantics yet still make a poor operational choice. The reason is often not a failure to understand the task. It is that the agent sees a menu of tools but not the current state of the execution harness: which route is slow, failing, stale, rate-limited, resource-constrained, or no longer economical. To the agent, equivalent APIs remain equivalent even when the host already knows that one is degraded.", s["body"]),
            p("We call this gap <b>operational blindness</b>. Agent Harness Awareness turns verified execution telemetry from a passive observability artifact into an active control input. The interface is intentionally minimal and trust-separated: the host measures raw state, reduces it to a bounded and freshness-labelled snapshot, and retains enforcement authority outside the model. The model may use that state to choose a different high-level action; it cannot edit the measurement, scheduler, oracle, or underlying constraints.", s["body"]),
            p("This paper makes two linked contributions. First, it articulates Harness Awareness as a general systems design principle: agents should reason not only over task semantics but also over verified operational state. Second, it provides a rigorous multi-model empirical validation in the tools dimension: verified tool-health state reduces observable policy regret by 96.9% and raises operational completion from 69.4% to 95.8% across three provider/model families.", s["body"]),
            p("2. Agent Harness Awareness", s["h1"]),
            p("2.1 Trust-separated state interface", s["h2"]),
            p("At a decision time <i>t</i>, let <i>x</i><sub>t</sub> be the task and tool interface, <i>h</i><sub>t</sub> the host state, and <i>z</i><sub>t</sub> = <font name='Symbol'>f</font>(<i>h</i><sub>t</sub>) a compact snapshot emitted by the harness. ToolRoute shows why this projection matters: when <i>z</i><sub>t</sub> carries truthful route-relevant monitor facts, agents select actions with substantially lower observable cost than under task-only or neutral same-shape information. A selected, verifiable projection can therefore be a high-leverage operational input without moving measurement or enforcement authority into the model.", s["body"]),
            p("The intended contract spans four state families: <b>Tools</b> (success, latency, error/circuit state); <b>Runtime</b> (deadlines and execution policy); <b>Hardware</b> (memory, CPU, disk, processes); and <b>Economics</b> (context, quota, rate limits, and cost). ToolRoute empirically evaluates Tools. The remaining families are next empirical instantiations of the same state contract.", s["body"]),
            p("2.2 Split planes: deterministic recovery and agent adaptation", s["h2"]),
            p("The data plane - kernel, proxy, circuit breaker, retry policy, and scheduler - continues to own fast local enforcement and recovery. The agent control plane becomes useful when state changes the strategy: choose a different tool, defer an operation, select a degraded-mode plan, or allocate remaining time and budget differently. ToolRoute isolates this fundamental strategic boundary while preserving deterministic enforcement in the data plane.", s["body"]),
            p("3. ToolRoute: a controlled information ablation", s["h1"]),
            p("3.1 Task and conditions", s["h2"]),
            p("ToolRoute presents one task, two functionally equivalent tools (<font name='Courier'>tool_alpha</font>, <font name='Courier'>tool_beta</font>), and a <font name='Courier'>wait</font> option. A seeded synthetic host-owned monitor probes each tool three times and records monitor-window success count, latency EWMA, circuit/error state, and snapshot age. The model receives one independent full-checkpoint prompt per decision with no filesystem, shell, network tool, schedule, oracle, or artifact access.", s["body"]),
            table([
                ["Condition", "Model-visible information"],
                ["A: task only", "Task and equivalent tool descriptions; no operational projection."],
                ["B: neutral envelope", "Same telemetry-shaped envelope, fields, row order, and tool rows as C, with equal neutral values."],
                ["C: verified state", "Same envelope with fresh host-owned monitor facts for the current tool state."],
            ], [1.28*inch, 4.65*inch], s),
            Spacer(1, 8),
            p("Condition B is the critical structural control: holding envelope, fields, ordering, and tool rows fixed while neutralizing route-relevant values isolates the contribution of operational state from the presence and shape of the interface. It is not an exact provider-token-matching control; provider input-token counts are retained descriptively.", s["body"]),
            p("3.2 External evaluation and auditability", s["h2"]),
            p("The primary outcome is <b>observable policy regret</b>: the excess cost of the selected action under an oracle restricted to canonical monitor facts rendered in C. Successful operational outcome is a secondary binary evaluation. Every provider attempt reserved its artifact directory before invocation and preserved its prompt, sanitized request/response, monitor snapshot, tool event, evaluator result, streams, and finalization hashes. The cohort contains 3 model families x 6 seeds x 4 turns x 3 conditions = 216 independent direct-provider decisions. All records completed and finalized with valid artifact hashes; no request was retried.", s["body"]),
            p("3.3 Analysis", s["h2"]),
            p("The empirical centerpiece is B-to-C: neutral versus truthful operational state in the same interface. We report all decisions in the denominator, Wilson intervals for completion, and raw as well as normalized regret. The primary display normalizes each model family's B mean to 100%; raw milliseconds remain in the appendix. Independent provider generations remain independent; a descriptive bootstrap over 18 model-by-seed environment blocks summarizes variation without treating providers as shared-seed paired draws.", s["body"]),
            p("4. Results", s["h1"]),
            p("Truthful operational state changes the next action substantially. Across 72 decisions per condition, C reduces mean observable policy regret from 4,251.54 ms in B to 131.12 ms - a 4,120.42 ms reduction (96.9%). Completion rises from 50/72 (69.4%; Wilson 95% CI 58.0-79.0%) to 69/72 (95.8%; 95% CI 88.3-98.5%), a 26.4-point increase. Condition A is also materially worse than C (4,826.45 ms regret; 47/72, 65.3% completion).", s["body"]),
            figure(rendered["figure_1_relative_regret.pdf"], "Figure 1. Mean observable policy regret normalized within each model family to B = 100%. Verified state (C) remains sharply lower across all three model families.", 5.65*inch, s["caption"]),
            table([
                ["Model", "A regret (ms)", "B regret (ms)", "C regret (ms)", "A completion", "B completion", "C completion"],
                ["GPT-5.6 Sol", "4,723.81", "3,307.00", "75.50", "16/24 (66.7%)", "18/24 (75.0%)", "23/24 (95.8%)"],
                ["Claude Sonnet 5", "5,031.72", "4,723.81", "75.50", "15/24 (62.5%)", "16/24 (66.7%)", "23/24 (95.8%)"],
                ["Gemini 3.7 Flash", "4,723.81", "4,723.81", "242.35", "16/24 (66.7%)", "16/24 (66.7%)", "23/24 (95.8%)"],
            ], [1.06*inch, 0.73*inch, 0.73*inch, 0.73*inch, 0.88*inch, 0.88*inch, 0.88*inch], s),
            Spacer(1, 8),
            p("The cross-family repetition matters. The result is not carried by a single provider: C produces a low-regret route in every family, while A and B retain substantial avoidable cost. The three C choices of <font name='Courier'>wait</font> remain in the denominator; they are not filtered away to improve the apparent result.", s["body"]),
            figure(rendered["figure_2_completion.pdf"], "Figure 2. Operational completion by condition and model family. Verified state completes 23 of 24 decisions for each model family.", 5.65*inch, s["caption"]),
            p("4.1 What the result establishes", s["h2"]),
            p("ToolRoute provides strong empirical evidence that verified, current tool-health state is a consequential control input for operational route selection. The B-to-C controlled information ablation holds the telemetry-shaped interface fixed while changing route-relevant values. Model choices are therefore strongly sensitive to structured operational facts, rather than only to the presence of a table-shaped prompt.", s["body"]),
            p("5. Scope and research agenda", s["h1"]),
            p("The experiment isolates one decision type: two-route selection under a synthetic, immediately delivered tool-health monitor. Larger tool catalogs, noisy or delayed monitors, stateful multi-turn histories, changing task semantics, and live service integration are direct next tests. The same interface extends naturally to deadline-aware planning, hardware and concurrency adaptation, economic state, and multi-agent backpressure.", s["body"]),
            p("6. Related work", s["h1"]),
            p("ReAct [1] established the importance of interleaving reasoning with environment actions, while Toolformer [2] studied learned tool use. AgentBench [3] and tau-bench [4] show that agents can fail in evolving, stateful environments. ToolRoute focuses on a different missing observation: verified operational state at route choice. OpenTelemetry [5] provides an established foundation for traces, metrics, and logs; Harness Awareness extends selected, provenance-preserving telemetry toward an agent decision interface. Agent-Native Telemetry [6] is the closest architectural neighbor: it focuses on compact verified telemetry records and access paths, whereas ToolRoute evaluates the downstream behavioral question with a neutral same-shape control.", s["body"]),
            p("7. Conclusion", s["h1"]),
            p("Agent Harness Awareness closes a loop that current tool-using agents often leave open: the harness observes operational state, but the agent chooses as if that state did not exist. In the frozen 216-decision ToolRoute cohort, truthful tool-health state reduced observable policy regret by 96.9% against a neutral same-shape control and increased completion by 26.4 points. These results advance a transition from passive observability to closed-loop agent control: agents can reason over verified execution telemetry while the harness retains authority to measure and enforce it.", s["body"]),
            p("Appendix A. Raw policy regret", s["h1"]),
            figure(rendered["appendix_figure_a1_raw_regret.pdf"], "Figure A1. Raw mean observable policy regret in milliseconds. These are the unnormalized values behind Figure 1.", 3.3*inch, s["caption"]),
            p("References", s["h1"]),
        ]
        references = [
            "[1] Shunyu Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. ICLR, 2023. arXiv:2210.03629.",
            "[2] Timo Schick et al. Toolformer: Language Models Can Teach Themselves to Use Tools. NeurIPS, 2023. arXiv:2302.04761.",
            "[3] Xiao Liu et al. AgentBench: Evaluating LLMs as Agents. ICLR, 2024. arXiv:2308.03688.",
            "[4] Shunyu Yao et al. tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains. ICLR, 2025. arXiv:2406.12045.",
            "[5] OpenTelemetry. Specification. https://opentelemetry.io/docs/specs/",
            "[6] He and Yu. Agent-Native Telemetry: Verifiable State-Delta Evidence for Autonomous Operations. 2026. arXiv:2608.16178.",
        ]
        story.extend(p(reference, s["reference"]) for reference in references)
        doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPO / "output" / "pdf" / "toolroute_arxiv_review_draft.pdf")
    args = parser.parse_args()
    build(args.output.resolve())
    print(args.output.resolve())


if __name__ == "__main__":
    main()
