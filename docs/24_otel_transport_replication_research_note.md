# Standards-based ToolRoute transport-replication research note

**Status:** researched candidate only. No implementation, provider authorization,
or result collection is authorized by this note.

## Decision question

Can ToolRoute obtain genuine tool-health observations from an existing telemetry
standard and test the resulting agent interface in a few hours, without turning
the first paper into a new microservice/SRE benchmark?

## Recommended source path

Use **OpenTelemetry HTTP client spans** as the source of truth for a small
socket-backed ToolRoute replication:

```text
instrumented HTTP client -> Toxiproxy -> local HTTP tool service
          |                                      |
          +-- standard OTel spans <--------------+
                         |
              host-owned reducer / freshness policy
                         |
              compact, provenance-labelled agent snapshot
                         |
                 A/B/C model decision -> same live HTTP route
```

The OpenTelemetry Python libraries can automatically create HTTP client spans;
the HTTP semantic conventions provide standard request, server, status, error,
and timing evidence. A minimal study can use the SDK's local exporter rather
than deploy a Collector. This is not a reinvention of telemetry collection: the
only project-specific part is the *decision interface* that reduces selected
spans to the bounded state used by ToolRoute.

| Standard source fact | Bounded agent field |
|---|---|
| span start/end times | rolling latency EWMA |
| HTTP/span success status | window success count and circuit/error state |
| `error.type` or transport exception | last error class |
| `server.address` / stable route mapping | tool identifier |
| span end time | snapshot age/freshness label |

The OpenTelemetry Collector is a valid production deployment boundary: its
filter, attributes, resource, and transform processors can redact, select,
enrich, or rename telemetry before export. It is unnecessary for this small
replication, where an in-process exporter eliminates Docker/Collector failure
modes while preserving the same standard span semantics.

## Fault path

Toxiproxy is appropriate only as the deterministic transport-fault mechanism.
It provides documented latency, disable/down, timeout, reset, bandwidth, and
packet-loss controls over real TCP connections. The coordinator must keep the
backend and proxies alive from monitoring through the provider response and
actual execution. It must **not** reuse the old cross-session fresh-subagent
start/submit path, whose backend lifecycle defect is retained as TR-025.

## Minimal candidate protocol

If approved after model-free validation, run a separately labelled appendix
replication, never pooled with the frozen 216-decision synthetic cohort:

1. Precommit two equivalent loopback HTTP routes and three unambiguous regimes:
   a latency-degraded route, a disabled/connection-error route, and an HTTP
   error route.
2. Instrument monitor and selected-action calls with OpenTelemetry. Capture
   three real spans per route, reduce only canonical standard facts, render the
   same A/B/C envelope, then execute the selected route through the still-live
   proxy.
3. Use a persistent single-process coordinator, reservation-first archives,
   sanitized provider records, no retries, and terminal hashes.
4. Before any provider call, demonstrate model-free route/oracle margins,
   redaction, A/B structural identity, monitor/action lifecycle integrity, and
   artifact finalization.
5. If those gates pass, precommit a compact 18-decision scope: two providers,
   three regimes, and A/B/C. Report every attempted decision. Include it only
   as an end-to-end transport replication if the predeclared B-to-C direction
   is present for each provider; otherwise retain and report it as a negative
   integration result without changing the primary paper claim.

## Claim boundary

This would justify: **the ToolRoute decision interface can consume standard,
live HTTP telemetry captured on the same socket-backed tool path that executes
the selected action.** It would not justify production-outage, broad
microservice, or universal-harness claims.

The broader architectural statement remains appropriate: OpenTelemetry and MCP
provide collection and trace-context interoperability, while Harness Awareness
defines a trust-separated policy layer that selects fresh, decision-relevant
facts for an agent. That layer should be conditional, bounded, redacted, and
freshness-labelled—not an unconditional dump of raw telemetry into every prompt.

## Why not the full OpenTelemetry Astronomy Shop demo?

The official Astronomy Shop is useful for later work: it is a near-real-world,
multi-service OpenTelemetry demonstration and exposes a larger observability
stack. For the current paper it would introduce a different task (diagnosis or
service remediation), many uncontrolled service dependencies, substantial setup
time, and an incompatible oracle. It would therefore dilute rather than
strengthen the clean ToolRoute question.

## Sources

- OpenTelemetry Python instrumentation libraries:
  <https://opentelemetry.io/docs/languages/python/libraries/>
- OpenTelemetry HTTP semantic conventions:
  <https://opentelemetry.io/docs/specs/semconv/http/http-spans/>
- OpenTelemetry Collector transformation guidance:
  <https://opentelemetry.io/docs/collector/transforming-telemetry/>
- Shopify Toxiproxy:
  <https://github.com/Shopify/toxiproxy>
- OpenTelemetry Astronomy Shop demo:
  <https://github.com/open-telemetry/opentelemetry-demo>
