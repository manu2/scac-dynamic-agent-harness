"""Build the submission-ready ToolRoute manuscript PDF from frozen summaries.

The prose source is paper/toolroute_draft_transport_replication_v0.2.md. This
builder contains the formatted counterpart and never accesses provider keys or
modifies immutable experiment artifacts.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


REPO = Path(__file__).resolve().parents[1]
AUTHORS = "Manu Agrawal and Shrey Nagpal"
MATH_FONT_NAME = "HarnessSTIX"
MATH_FONT_PATH = Path("/System/Library/Fonts/Supplemental/STIXTwoText.ttf")


def phi() -> str:
    """Render Greek phi with an embedded math font, never an unsupported glyph."""

    if MATH_FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont(MATH_FONT_NAME, str(MATH_FONT_PATH)))
        return f"<font name='{MATH_FONT_NAME}'>φ</font>"
    return "<i>phi</i>"


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, alignment=TA_CENTER, textColor=colors.HexColor("#142033"), spaceAfter=7),
        "authors": ParagraphStyle("authors", parent=base["Normal"], fontName="Helvetica", fontSize=10.2, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#526173"), spaceAfter=13),
        "abstract_head": ParagraphStyle("abstract_head", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10.2, leading=12, textColor=colors.HexColor("#142033")),
        "abstract": ParagraphStyle("abstract", parent=base["BodyText"], fontName="Helvetica", fontSize=9.2, leading=12.7, alignment=TA_JUSTIFY, leftIndent=14, rightIndent=14, spaceAfter=9),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=12.6, leading=15, textColor=colors.HexColor("#142033"), spaceBefore=11, spaceAfter=5, keepWithNext=True),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.4, leading=12.5, textColor=colors.HexColor("#142033"), spaceBefore=8, spaceAfter=4, keepWithNext=True),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.05, leading=12.5, alignment=TA_JUSTIFY, spaceAfter=6),
        "caption": ParagraphStyle("caption", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=7.9, leading=9.7, alignment=TA_CENTER, textColor=colors.HexColor("#46546B"), spaceAfter=7),
        "ref": ParagraphStyle("ref", parent=base["Normal"], fontName="Helvetica", fontSize=8.05, leading=10.1, leftIndent=12, firstLineIndent=-12, spaceAfter=3),
        "table_head": ParagraphStyle("table_head", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.4, leading=8.7, alignment=TA_CENTER, textColor=colors.HexColor("#142033")),
        "table_cell": ParagraphStyle("table_cell", parent=base["Normal"], fontName="Helvetica", fontSize=7.15, leading=8.7, textColor=colors.HexColor("#142033")),
    }


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def make_table(data: list[list[str]], widths: list[float], s: dict[str, ParagraphStyle]) -> Table:
    wrapped = [[paragraph(str(cell), s["table_head"] if ri == 0 else s["table_cell"]) for cell in row] for ri, row in enumerate(data)]
    table = Table(wrapped, colWidths=widths, repeatRows=1, hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F0FA")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C6D1DF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def render_pdf_figure(source: Path, target: Path) -> None:
    subprocess.run(["sips", "-s", "format", "png", "-Z", "2500", str(source), "--out", str(target)], check=True, capture_output=True, text=True)
    if not target.exists():
        raise RuntimeError(f"failed to render {source}")


def figure(path: Path, caption: str, s: dict[str, ParagraphStyle]) -> list:
    image = Image(str(path))
    image._restrictSize(5.8 * inch, 4.5 * inch)
    return [image, Spacer(1, 3), paragraph(caption, s["caption"])]


def footer(pdf, doc) -> None:
    width, height = letter
    pdf.saveState()
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#D7DFE9"))
    pdf.line(doc.leftMargin, 0.49 * inch, width - doc.rightMargin, 0.49 * inch)
    pdf.setFillColor(colors.HexColor("#526173"))
    pdf.setFont("Helvetica", 7.3)
    pdf.drawString(doc.leftMargin, 0.32 * inch, "Agent Harness Awareness - ToolRoute")
    pdf.drawRightString(width - doc.rightMargin, 0.32 * inch, f"Page {doc.page}")
    pdf.restoreState()


def build(output: Path) -> None:
    s = styles()
    greek_phi = phi()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="toolroute-submission-figures-") as temp:
        temp_dir = Path(temp)
        fig1, fig2 = temp_dir / "figure_1.png", temp_dir / "figure_2.png"
        render_pdf_figure(REPO / "paper/figures/figure_1_conditions_log.pdf", fig1)
        render_pdf_figure(REPO / "paper/figures/figure_2_transport_replication.pdf", fig2)
        doc = SimpleDocTemplate(str(output), pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.68 * inch, title="Agent Harness Awareness", author=AUTHORS)
        story = [
            paragraph("Agent Harness Awareness: Turning Verified Telemetry into Operational Control for Tool-Using Agents", s["title"]),
            paragraph("Manu Agrawal &nbsp;&nbsp;&middot;&nbsp;&nbsp; Shrey Nagpal", s["authors"]),
            paragraph("Abstract", s["abstract_head"]),
            paragraph("Tool-using agents commonly choose among APIs from task semantics and tool descriptions while the execution harness separately observes latency, failures, and route health. This separation creates <b>operational blindness</b>: a healthy route and a degraded route can look identical at the decision where the choice matters. We introduce <b>Agent Harness Awareness</b>, a trust-separated design in which compact, fresh, host-verified operational state becomes a first-class control input while measurement, enforcement, and evaluation remain outside the model. In a frozen 216-decision direct-provider ToolRoute cohort spanning GPT-5.6 Sol, Claude Sonnet 5, and Gemini 3.7 Flash, truthful tool-health state reduced mean observable policy regret by 96.9% versus a neutral same-shape telemetry control (4,252 ms to 131 ms) and increased completion from 69.4% to 95.8%. We separately reproduce the decision effect in a standards-based live transport integration: 27 remote-model decisions over actual local TCP/HTTP routes, OpenTelemetry HTTP client spans, and Toxiproxy-injected latency, connection, and HTTP failures. There, verified state produced 9/9 successful, zero-regret selections across all model families and fault regimes, versus 5/9 completion and 8,956 ms mean regret for the neutral control. Selected, verified operational facts can become direct control inputs for autonomous agents.", s["abstract"]),
            paragraph("1. From operational blindness to closed-loop control", s["h1"]),
            paragraph("An agent can understand a user request and every tool's semantics yet still make an avoidable operational error. The missing information is often not semantic; it is the current state of the harness: which route is slow, failing, rate-limited, stale, resource-constrained, or no longer economical. When the harness knows this state but the agent does not, equivalent APIs remain indistinguishable at the moment the agent selects one.", s["body"]),
            paragraph("This is a general agent-runtime problem, not merely a routing problem. Harnesses already observe four high-value operational dimensions: <b>tools and network</b> (route health and circuit state); <b>runtime</b> (deadlines, queueing, and concurrency); <b>hardware and sandbox</b> (memory headroom, CPU pressure, storage); and <b>economics</b> (context headroom, token burn, quota, and cost). A harness-aware agent can use these facts for alternate-route selection, deadline-aware decomposition, checkpointing before budget exhaustion, resource-aware concurrency, and backpressure-aware coordination.", s["body"]),
            paragraph("We call this gap <b>operational blindness</b>. Agent Harness Awareness closes it by reducing bounded, freshness-labelled, host-verified execution state into an agent decision interface. The host retains authority over collection, reduction, safety, and enforcement. The model may adapt its next strategic action, but cannot rewrite measurements, disable constraints, or modify the evaluator.", s["body"]),
            paragraph("This paper contributes a general systems paradigm, a trust-separated state interface, a frozen 216-decision multi-model information ablation, and a separately analysed 27-decision OpenTelemetry/Toxiproxy transport replication. It is evidence that what an agent knows about its harness can be as consequential as what it knows about the user task.", s["body"]),
            paragraph("2. Agent Harness Awareness", s["h1"]),
            paragraph(f"At decision time <i>t</i>, let <i>x</i><sub>t</sub> denote the task and tool interface, <i>h</i><sub>t</sub> the host state, and <i>z</i><sub>t</sub> = {greek_phi}(<i>h</i><sub>t</sub>) a bounded host-generated projection. The proposed <b>Substrate State Telemetry (SST) contract</b> covers Tools (success history, latency, error/circuit state), Runtime (deadlines and exit state), Hardware (memory, CPU, disk, processes), and Economics (context headroom, quota, rate, cost). ToolRoute evaluates the Tools dimension; the other dimensions are direct future instantiations, not pooled evidence.", s["body"]),
            paragraph("Harness Awareness complements rather than replaces deterministic controls. The data plane—kernel, proxy, circuit breaker, retry policy, and scheduler—continues to own immediate recovery and safety. The agent control plane acts when current state changes strategy: choose a route, defer work, adopt a degraded-mode plan, or allocate time and budget differently.", s["body"]),
            paragraph("3. Two complementary ToolRoute studies", s["h1"]),
            paragraph("ToolRoute evaluates the tools-and-network dimension through two deliberately distinct studies. Study 1 is the primary controlled information ablation; Study 2 is an independently reported systems replication. Their data are never pooled.", s["body"]),
            make_table([
                ["Study", "Question", "Evidence", "Role"],
                ["Study 1", "Does truthful state improve route selection when the interface is held constant?", "216 frozen provider decisions; seeded monitor", "Primary behavioral estimate"],
                ["Study 2", "Does the effect survive an OTel-instrumented live HTTP tool path?", "27 frozen decisions; OTel, Toxiproxy, live action", "End-to-end replication"],
            ], [0.72 * inch, 2.15 * inch, 1.72 * inch, 1.28 * inch], s),
            Spacer(1, 7),
            paragraph("3.1 Study 1: controlled information ablation", s["h2"]),
            paragraph("The agent retrieves a read-only customer record through one of two functionally equivalent routes, <font name='Courier'>tool_alpha</font> and <font name='Courier'>tool_beta</font>, or chooses <font name='Courier'>wait</font>. The host owns monitoring, schedules, execution, and an external observable-cost oracle. Each decision is an independent full-checkpoint episode; models have no shell, filesystem, network-tool, schedule, oracle, or artifact access.", s["body"]),
            make_table([
                ["Condition", "Model-visible information"],
                ["A: task only", "Task and equivalent tool descriptions; no operational projection."],
                ["B: neutral envelope", "Same telemetry-shaped envelope, fields, row order, and tool rows as C, with equal neutral values."],
                ["C: verified state", "Same envelope with fresh host-owned facts for current route state."],
            ], [1.3 * inch, 4.55 * inch], s),
            Spacer(1, 7),
            paragraph("B is the structural control: it holds interface shape and technical content constant while neutralizing route-relevant values. The primary outcome is <b>observable policy regret</b>, the excess selected-action cost under an oracle restricted to facts rendered in C. The frozen direct-provider cohort contains 216 independent decisions (three model families × six seeds × four turns × three conditions); every attempt retains its prompt, sanitized request/response, snapshot, tool event, evaluation result, and finalization hashes. No request was retried.", s["body"]),
            paragraph("3.2 Study 2: live OpenTelemetry transport replication", s["h2"]),
            paragraph("The separately labelled v0.2 replication preserves the A/B/C information intervention but moves to a live instrumented tool path. Each episode makes three monitor requests per route through local TCP/HTTP proxies. Standard OpenTelemetry HTTP client spans provide duration and outcome facts; a host reducer converts them to the decision snapshot. Toxiproxy injects a predeclared latency, connection, or HTTP failure on one route, and the selected route is then executed through the same still-live proxy. The frozen replication contains 27 independent decisions (three models × three fault regimes × A/B/C) and retains raw spans, reducer events, provider records, action spans, results, and hashes.", s["body"]),
            paragraph("4. Results", s["h1"]),
            paragraph("4.1 Study 1: controlled information ablation", s["h2"]),
            paragraph("Across 72 decisions per condition, verified state reduces mean observable policy regret from 4,251.54 ms in B to 131.12 ms: a 96.9% reduction. Completion rises from 50/72 (69.4%; Wilson 95% CI 58.0–79.0%) to 69/72 (95.8%; Wilson 95% CI 88.3–98.5%), a 26.4-point increase. A is also materially worse than C (4,826.45 ms regret; 47/72 completion), demonstrating that a telemetry-shaped envelope alone does not explain the result.", s["body"]),
            *figure(fig1, "Figure 1. Mean observable policy regret for all three information conditions in the frozen 216-decision cohort. Log scaling keeps verified-state values visible; A, B, and C are independent condition means, not trajectories.", s),
            make_table([
                ["Model", "A regret", "B regret", "C regret", "C completion"],
                ["GPT-5.6 Sol", "4,723.81 ms", "3,307.00 ms", "75.50 ms", "23/24 (95.8%)"],
                ["Claude Sonnet 5", "5,031.72 ms", "4,723.81 ms", "75.50 ms", "23/24 (95.8%)"],
                ["Gemini 3.7 Flash", "4,723.81 ms", "4,723.81 ms", "242.35 ms", "23/24 (95.8%)"],
            ], [1.32 * inch, 0.96 * inch, 0.96 * inch, 0.96 * inch, 1.15 * inch], s),
            Spacer(1, 7),
            paragraph("4.2 Study 2: live transport replication", s["h2"]),
            paragraph("The transport replication reproduces the central result without relying on the synthetic monitor. Across nine B decisions, models completed 5/9 actions (55.6%) and incurred 8,956.37 ms mean observable policy regret. Across nine C decisions, models selected the observable-best route in 9/9 cases, completed 9/9 live actions, and incurred 0.00 ms mean observable policy regret. Each model has one C episode in each predeclared latency, connection-error, and HTTP-error regime.", s["body"]),
            *figure(fig2, "Figure 2. Study 2 outcome summary. All nine verified-state cells in the frozen OpenTelemetry/Toxiproxy replication selected the observable-best route and completed the subsequent live proxied HTTP action; the lower panel reports all A/B/C completion outcomes.", s),
            paragraph("The counterbalanced replication also exposes the baseline pattern that verified state corrects. Across A and B, models selected <font name='Courier'>tool_alpha</font> in 17 of 18 decisions, including 7 of 8 cases in which <font name='Courier'>tool_beta</font> was listed first. This is an observed default route-label preference in this cohort, not a claim about universal positional bias. Condition C removed its operational consequence by selecting the healthy route in every regime regardless of which route was degraded or listed first.", s["body"]),
            paragraph("5. Implications, boundaries, and agenda", s["h1"]),
            paragraph("Modern observability systems collect traces, metrics, and logs for human operators. Harness Awareness supplies the missing control-plane step: select the facts relevant to the immediate decision, preserve provenance and freshness, and expose the bounded result to the agent without giving it authority over truth or enforcement. The interface can support alternate-region routing, deadline-aware planning, quota-aware work decomposition, context-budget checkpointing, resource-aware concurrency, and multi-agent backpressure.", s["body"]),
            paragraph("The evidence is strong for the tested mechanism: current verified tool-health facts improve selection between functionally equivalent routes. The primary cohort uses a synthetic host-owned monitor; the replication uses a minimal local HTTP service and deterministic proxy faults. Neither study claims uncontrolled production-outage rates, universal service topologies, or completed evidence for hardware, runtime, and economic state. Those are next high-value tests, not prerequisites for the demonstrated control-loop effect.", s["body"]),
            paragraph("6. Conclusion", s["h1"]),
            paragraph("Agent Harness Awareness closes an operational loop that tool-using systems often leave open: the harness observes execution state while the agent chooses as if that state did not exist. In a frozen 216-decision cohort, verified state reduced mean observable policy regret by 96.9% and raised completion by 26.4 points against a neutral same-shape control. In a separately reported 27-decision OpenTelemetry/Toxiproxy replication, verified state selected the best route and completed the live action in all nine C episodes across three providers and three fault regimes. The evidence supports a clear systems direction: turn selected, verified telemetry into an active agent control input while keeping truth and enforcement in the harness.", s["body"]),
            paragraph("References", s["h1"]),
        ]
        references = [
            "[1] Shunyu Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. ICLR, 2023. arXiv:2210.03629.",
            "[2] Timo Schick et al. Toolformer: Language Models Can Teach Themselves to Use Tools. NeurIPS, 2023. arXiv:2302.04761.",
            "[3] Xiao Liu et al. AgentBench: Evaluating LLMs as Agents. ICLR, 2024. arXiv:2308.03688.",
            "[4] Shunyu Yao et al. tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains. ICLR, 2025. arXiv:2406.12045.",
            "[5] OpenTelemetry. Specification. https://opentelemetry.io/docs/specs/",
            "[6] Shopify. Toxiproxy. https://github.com/Shopify/toxiproxy",
            "[7] He and Yu. Agent-Native Telemetry: Verifiable State-Delta Evidence for Autonomous Operations. 2026. arXiv:2608.16178.",
            "[8] Aayush Gupta. ReliabilityBench: Evaluating LLM Agent Reliability Under Production-Like Stress Conditions. 2026. arXiv:2601.06112.",
            "[9] Dongsheng Zhu et al. When Tools Fail: Benchmarking Dynamic Replanning and Anomaly Recovery in LLM Agents. 2026. arXiv:2606.05806.",
        ]
        story.extend(paragraph(ref, s["ref"]) for ref in references)
        doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build(REPO / "output/pdf/agent_harness_awareness_toolroute.pdf")
