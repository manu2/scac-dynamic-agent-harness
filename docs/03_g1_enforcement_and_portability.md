# G1 Enforcement and Portability Contract

G1 enforcement is host-owned. The model and its tools cannot select the cgroup,
raise resource limits, stop the watchdog, or alter a terminal classification.

## cgroup-v2 collection

`CgroupV2Collector` accepts a single trial cgroup path and requires readable
`memory.current`, `memory.max`, `memory.events`, `cpu.max`, and `cpu.stat`, plus
the `memory` and `cpu` controllers. It rejects malformed files and counter
regression. The first sample establishes a baseline and produces explicit zero
interval deltas; later samples are deltas of the kernel counters. It uses
`nr_throttled` and `throttled_usec`, never the cgroup-v1 `throttled_time` name.

## Positive controls

- **Timeout:** a separate worker sleeps beyond a fixed budget; a host watchdog
  kills its process group. Only that kill is a passing control.
- **Tool fault:** a host-created worker emits a fixed `HTTP_503` marker and exit
  code. The marker and classification must both match.
- **Memory:** the control creates a unique child of a delegated cgroup-v2 parent,
  writes its `memory.max`, moves a barrier-held allocation worker into it, then
  requires the child `memory.events` `oom_kill` counter to increase. Python
  `MemoryError`, a generic process exit, or a timeout is not a pass.

All controls reserve a unique directory beneath `experiments/g1-controls/` and
write a result record plus stdout/stderr with exclusive creation. A missing
cgroup-v2 capability is recorded as `BLOCKED`; it must be rerun on a suitable
Linux host before G1 is marked complete.
