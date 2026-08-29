"""Tests for deterministic compact model-visible renderer and golden outputs."""

from __future__ import annotations

import json
from pathlib import Path
from scac_harness.renderer import render_tier1_system_prefix, render_tier2_envelope


FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_DIR = FIXTURES_DIR / "valid"


def test_tier1_system_prefix() -> None:
    """Tier 1 prefix must contain trust declaration, immutability statement, and unit specifications."""
    prefix = render_tier1_system_prefix()
    assert "=== SCAC HOST TELEMETRY SPECIFICATION (v0.1) ===" in prefix
    assert "host-verified" in prefix
    assert "Units:" in prefix
    assert "Missing/unsupported metrics are explicitly marked UNAVAILABLE" in prefix


def test_tier2_rendering_golden_structure() -> None:
    """Rendered turn envelope must match deterministic section structure and explicit units."""
    fixture = json.loads((VALID_DIR / "healthy_state.json").read_text(encoding="utf-8"))
    rendered = render_tier2_envelope(fixture)

    assert "=== HOST TELEMETRY [seq=0 kind=full_checkpoint" in rendered
    assert "[HARDWARE]" in rendered
    assert "memory: cur=67108864B max=268435456B headroom=0.75 state=OK" in rendered
    assert "cpu: quota=2.0cores" in rendered
    assert "[TOOLS]" in rendered
    assert "query_db: window=10 succ=10 consec_fail=0 latency_ewma=42.5ms" in rendered
    assert "[RUNTIME]" in rendered
    assert "wall_remaining=60000ms" in rendered
    assert "[ECONOMICS]" in rendered
    assert "context_tokens_rem=120000" in rendered
    assert "cost_usd=$0.0042" in rendered


def test_tier2_delta_rendering_shows_base_snapshot() -> None:
    """Delta snapshot must explicitly display its base checkpoint ID in the header."""
    fixture = json.loads((VALID_DIR / "delta_snapshot.json").read_text(encoding="utf-8"))
    rendered = render_tier2_envelope(fixture)

    assert "=== HOST TELEMETRY [seq=11 kind=delta base=" in rendered


def test_renderer_stable_section_and_tool_ordering() -> None:
    """Renderer must output sections and tools in strictly deterministic alphabetical order."""
    fixture = json.loads((VALID_DIR / "healthy_state.json").read_text(encoding="utf-8"))
    fixture["tools"]["b_tool"] = {
        "window_n": 5, "successes": 5, "consecutive_failures": 0,
        "latency_ewma_ms": 10.0, "circuit": "CLOSED", "last_error": "NONE",
    }
    fixture["tools"]["a_tool"] = {
        "window_n": 5, "successes": 5, "consecutive_failures": 0,
        "latency_ewma_ms": 10.0, "circuit": "CLOSED", "last_error": "NONE",
    }

    rendered1 = render_tier2_envelope(fixture)
    rendered2 = render_tier2_envelope(fixture)

    assert rendered1 == rendered2
    # Check section order
    hw_pos = rendered1.find("[HARDWARE]")
    tools_pos = rendered1.find("[TOOLS]")
    rt_pos = rendered1.find("[RUNTIME]")
    econ_pos = rendered1.find("[ECONOMICS]")
    assert 0 < hw_pos < tools_pos < rt_pos < econ_pos

    # Check tools alphabetical order
    a_pos = rendered1.find("a_tool:")
    b_pos = rendered1.find("b_tool:")
    assert 0 < a_pos < b_pos


def test_renderer_explicit_unavailable_rendering() -> None:
    """Unavailable metrics must be explicitly rendered as UNAVAILABLE, never converted to 0."""
    fixture = json.loads((VALID_DIR / "partially_unavailable_quota_metadata.json").read_text(encoding="utf-8"))
    rendered = render_tier2_envelope(fixture)

    assert "rate_limit_rem=UNAVAILABLE" in rendered
    assert "rate_limit_reset_ms=UNAVAILABLE" in rendered
    assert "[UNAVAILABLE_FIELDS]" in rendered
    assert "economics.rate_limit_remaining" in rendered


def test_renderer_bounded_output_size() -> None:
    """All valid fixtures must render within the strict token/character budget (< 1800 chars)."""
    for fpath in VALID_DIR.glob("*.json"):
        fixture = json.loads(fpath.read_text(encoding="utf-8"))
        rendered = render_tier2_envelope(fixture, max_chars=1800)
        assert len(rendered) < 1800, f"Fixture {fpath.name} rendered {len(rendered)} chars!"


def test_no_secrets_or_raw_headers_in_rendered_output() -> None:
    """Telemetry rendering must not contain raw authentication headers or secret patterns."""
    fixture = json.loads((VALID_DIR / "healthy_state.json").read_text(encoding="utf-8"))
    rendered = render_tier2_envelope(fixture)

    forbidden = ["bearer", "authorization", "secret", "cookie", "token gho_", "ghp_"]
    for word in forbidden:
        assert word not in rendered.lower()


def test_renderer_never_projects_recommended_constraints() -> None:
    """Tier 2 is descriptive; host policy advice cannot enter the treatment."""
    fixture = json.loads((VALID_DIR / "tool_degraded_state.json").read_text(encoding="utf-8"))
    fixture["recommended_constraints"] = ["do not call query_db"]
    rendered = render_tier2_envelope(fixture)
    assert "HOST_CONSTRAINTS" not in rendered
    assert "do not call" not in rendered
