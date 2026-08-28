"""Host-owned G1 enforcement and positive-control execution.

The routines here are intentionally model-free.  A failed preflight is a
blocked control, never a passing substitute for kernel enforcement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Sequence
from uuid import uuid4

from scac_harness.collectors import CgroupV2Collector, CgroupV2Unavailable


@dataclass(frozen=True)
class ControlResult:
    name: str
    status: str  # PASS, FAIL, or BLOCKED
    classification: str
    detail: str
    returncode: int | None
    stdout: str
    stderr: str
    started_at_ms: int
    ended_at_ms: int


class ImmutableArtifactStore:
    """Atomically reserve a unique G1 record directory and write once-only files."""

    def __init__(self, experiments_root: Path) -> None:
        self.root = Path(experiments_root) / "g1-controls"

    def reserve(self, control_name: str) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        path = self.root / f"{stamp}-{control_name}-{uuid4().hex}"
        path.mkdir(mode=0o700)
        return path

    @staticmethod
    def write_json_once(directory: Path, filename: str, value: object) -> None:
        with (directory / filename).open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")

    @staticmethod
    def write_text_once(directory: Path, filename: str, value: str) -> None:
        with (directory / filename).open("x", encoding="utf-8") as handle:
            handle.write(value)


def _now_ms() -> int:
    return time.monotonic_ns() // 1_000_000


def run_timeout_positive_control(timeout_s: float = 0.15) -> ControlResult:
    """Verify the host watchdog kills a process that exceeds its declared budget."""
    started = _now_ms()
    command = [sys.executable, "-c", "import time; time.sleep(60)"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout_s)
        return ControlResult("timeout", "FAIL", "EXITED_BEFORE_TIMEOUT", "worker ended before watchdog fired", process.returncode, stdout, stderr, started, _now_ms())
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        return ControlResult("timeout", "PASS", "WATCHDOG_TIMEOUT", "host watchdog killed overdue worker", process.returncode, stdout, stderr, started, _now_ms())


def run_tool_fault_positive_control() -> ControlResult:
    """Verify an injected deterministic tool fault is externally observable."""
    started = _now_ms()
    command = [sys.executable, "-c", "import sys; print('SCAC_TOOL_FAULT HTTP_503', file=sys.stderr); sys.exit(75)"]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    passed = completed.returncode == 75 and "SCAC_TOOL_FAULT HTTP_503" in completed.stderr
    return ControlResult(
        "tool_fault",
        "PASS" if passed else "FAIL",
        "INJECTED_HTTP_503" if passed else "UNEXPECTED_TOOL_RESULT",
        "deterministic host-owned tool fault observed" if passed else "fault marker or exit code missing",
        completed.returncode,
        completed.stdout,
        completed.stderr,
        started,
        _now_ms(),
    )


def run_memory_preflight(cgroup_root: Path) -> ControlResult:
    """Check that memory enforcement is possible; do not simulate a cgroup pass."""
    started = _now_ms()
    try:
        capability = CgroupV2Collector(cgroup_root).capability()
        if not capability.available:
            raise CgroupV2Unavailable(capability.reason or "unavailable")
        if not os.access(cgroup_root, os.W_OK):
            raise CgroupV2Unavailable(f"cgroup root is not writable: {cgroup_root}")
    except CgroupV2Unavailable as exc:
        return ControlResult("memory", "BLOCKED", "CGROUP_V2_UNAVAILABLE", str(exc), None, "", "", started, _now_ms())
    return ControlResult("memory", "FAIL", "NOT_EXECUTED", "cgroup v2 is available but allocation control is not yet executed", None, "", "", started, _now_ms())


def _read_counter(path: Path, name: str) -> int:
    for line in path.read_text(encoding="utf-8").splitlines():
        key, value = line.split()
        if key == name:
            return int(value)
    raise RuntimeError(f"missing {name} in {path}")


def run_memory_positive_control(
    cgroup_parent: Path,
    memory_max_bytes: int = 32 * 1024 * 1024,
    timeout_s: float = 10.0,
) -> ControlResult:
    """Prove cgroup memory enforcement with an observed child-cgroup OOM kill.

    The caller must supply a delegated, writable cgroup-v2 parent dedicated to
    this control.  The routine creates and removes only its own unique child.
    It never falls back to rlimits, a Python ``MemoryError``, or a synthetic
    success: only an increment in the kernel's ``memory.events:oom_kill`` is a
    passing result.
    """
    started = _now_ms()
    parent = Path(cgroup_parent)
    preflight = run_memory_preflight(parent)
    if preflight.status == "BLOCKED":
        return preflight
    child = parent / f"scac-g1-memory-{uuid4().hex}"
    process: subprocess.Popen[str] | None = None
    stdout = ""
    stderr = ""
    try:
        child.mkdir(mode=0o700)
        (child / "memory.max").write_text(f"{memory_max_bytes}\n", encoding="utf-8")
        before_oom_kill = _read_counter(child / "memory.events", "oom_kill")
        # The worker is held at a barrier until its PID has been moved into the
        # child cgroup, eliminating a host-memory allocation race.
        command = [
            sys.executable,
            "-c",
            "import sys; sys.stdin.read(1); blocks=[]; "
            "\nwhile True: blocks.append(bytearray(1024 * 1024))",
        ]
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        (child / "cgroup.procs").write_text(f"{process.pid}\n", encoding="utf-8")
        assert process.stdin is not None
        process.stdin.write("go")
        process.stdin.close()
        process.stdin = None
        try:
            stdout, stderr = process.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            return ControlResult(
                "memory", "FAIL", "CONTROL_TIMEOUT", "allocation worker did not trigger cgroup OOM within timeout",
                process.returncode, stdout, stderr, started, _now_ms(),
            )
        after_oom_kill = _read_counter(child / "memory.events", "oom_kill")
        passed = after_oom_kill > before_oom_kill and process.returncode is not None and process.returncode != 0
        return ControlResult(
            "memory",
            "PASS" if passed else "FAIL",
            "CGROUP_OOM_KILL" if passed else "OOM_NOT_OBSERVED",
            f"oom_kill {before_oom_kill}->{after_oom_kill}; returncode={process.returncode}",
            process.returncode,
            stdout,
            stderr,
            started,
            _now_ms(),
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return ControlResult("memory", "BLOCKED", "CGROUP_ENFORCEMENT_UNVERIFIABLE", str(exc), None, stdout, stderr, started, _now_ms())
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        # This only removes the exact empty child directory created above.  A
        # non-empty / non-removable cgroup is retained for operator inspection.
        try:
            child.rmdir()
        except OSError:
            pass


def record_control(store: ImmutableArtifactStore, result: ControlResult) -> Path:
    """Write an immutable artifact bundle for every control attempt."""
    directory = store.reserve(result.name)
    store.write_json_once(directory, "result.json", asdict(result))
    store.write_text_once(directory, "stdout.txt", result.stdout)
    store.write_text_once(directory, "stderr.txt", result.stderr)
    return directory
