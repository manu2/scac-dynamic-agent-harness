from __future__ import annotations

from pathlib import Path

import pytest

from scac_harness.collectors import CgroupV2Collector, CgroupV2Unavailable


def _fake_cgroup(root: Path) -> None:
    (root / "cgroup.controllers").write_text("cpu memory pids\n")
    (root / "memory.current").write_text("100\n")
    (root / "memory.max").write_text("200\n")
    (root / "memory.events").write_text("low 0\nhigh 2\nmax 0\noom 0\noom_kill 0\n")
    (root / "cpu.max").write_text("100000 100000\n")
    (root / "cpu.stat").write_text("usage_usec 10\nnr_throttled 1\nthrottled_usec 4\n")


def test_cgroup_collector_emits_explicit_baseline_then_deltas(tmp_path: Path) -> None:
    _fake_cgroup(tmp_path)
    collector = CgroupV2Collector(tmp_path, clock_ms=lambda: 1000)
    first = collector.collect()
    assert first[0].payload["events_delta"]["high"] == 0
    assert first[1].payload["nr_throttled_delta"] == 0
    (tmp_path / "memory.events").write_text("low 0\nhigh 5\nmax 0\noom 0\noom_kill 1\n")
    (tmp_path / "cpu.stat").write_text("usage_usec 20\nnr_throttled 3\nthrottled_usec 14\n")
    second = collector.collect()
    assert second[0].payload["events_delta"] == {"high": 3, "max": 0, "oom": 0, "oom_kill": 1}
    assert second[1].payload["throttled_usec_delta"] == 10


def test_cgroup_collector_fails_closed_without_required_files(tmp_path: Path) -> None:
    collector = CgroupV2Collector(tmp_path)
    assert collector.capability().available is False
    with pytest.raises(CgroupV2Unavailable):
        collector.collect()
