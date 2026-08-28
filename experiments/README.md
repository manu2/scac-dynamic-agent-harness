# Experiments

Raw calibration and trial artifacts are immutable. A runner must atomically
reserve a trial directory before any provider call and must persist terminal
metadata for success, transport failure, malformed output, refusal, timeout, and
enforcement failure.

`g1-controls/` contains immutable local enforcement-control attempts. A blocked
control is evidence of missing capability, not a passing result. In particular,
memory enforcement is certified only by the child cgroup's kernel-reported OOM
event, never by a Python `MemoryError` or a host-level substitute.
