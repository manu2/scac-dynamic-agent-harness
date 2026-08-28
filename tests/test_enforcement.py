from __future__ import annotations

import json
from pathlib import Path

from scac_harness.enforcement import (
    ImmutableArtifactStore,
    record_control,
    run_memory_positive_control,
    run_memory_preflight,
    run_timeout_positive_control,
    run_tool_fault_positive_control,
)


def test_timeout_positive_control_is_host_enforced() -> None:
    result = run_timeout_positive_control(0.05)
    assert result.status == "PASS"
    assert result.classification == "WATCHDOG_TIMEOUT"


def test_tool_fault_positive_control_is_deterministic() -> None:
    result = run_tool_fault_positive_control()
    assert result.status == "PASS"
    assert result.classification == "INJECTED_HTTP_503"


def test_memory_preflight_fails_closed_and_artifacts_are_immutable(tmp_path: Path) -> None:
    result = run_memory_preflight(tmp_path / "no-cgroup")
    assert result.status == "BLOCKED"
    store = ImmutableArtifactStore(tmp_path / "experiments")
    record = record_control(store, result)
    assert json.loads((record / "result.json").read_text())["status"] == "BLOCKED"


def test_memory_positive_control_does_not_substitute_non_cgroup_enforcement(tmp_path: Path) -> None:
    result = run_memory_positive_control(tmp_path / "no-cgroup")
    assert result.status == "BLOCKED"
    assert result.classification == "CGROUP_V2_UNAVAILABLE"
