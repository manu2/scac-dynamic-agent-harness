# Standards-based ToolRoute transport-replication research note

**Status:** model-free validation, the preliminary Gemini v0.1 pilot, and the
fresh counterbalanced v0.2 cohort are complete. The v0.2 cohort contains 27
hash-finalized remote-model decisions across Gemini 3.7 Flash, Claude Sonnet 5,
and GPT-5.6 Sol; provider authorization is currently false. It is separately
reported from the primary ToolRoute v1.0 cohort and is not pooled with it.

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

## Implemented model-free validation

The retained implementation is `src/scac_harness/otel_transport.py` and
`scripts/run_toolroute_otel_transport_calibration.py`. It uses the standard
Requests auto-instrumentor and an SDK in-memory exporter. A span-to-event
adapter rejects an incomplete request rather than deriving health from the
request wrapper: a valid span must identify a GET endpoint, contain a valid
start/end duration, and contain either an HTTP status or OTel error evidence.
Exception messages and stack traces are deliberately excluded from the raw-span
archive; the standard exception type is sufficient for the bounded adapter.

Four complete, model-free three-regime calibration blocks were retained under
`experiments/g2-calibrations/toolroute-otel-transport/` during implementation.
The final block validated all finalization hashes and yielded:

| Regime | OTel-derived pre-decision state | Observable-best route | Live selected action |
|---|---|---|---|
| 300 ms proxy latency on alpha | alpha EWMA 303.82 ms; beta 1.37 ms | beta | HTTP 200 |
| disabled alpha proxy | alpha 0/3, `CONNECTION_ERROR`, open circuit | beta | HTTP 200 |
| beta upstream HTTP 503 | beta 0/3, `HTTP_503`, open circuit | alpha | HTTP 200 |

This establishes the integration mechanics—not an agent behavioral result. In
each retained calibration, the *host observable oracle* made the final choice
as a positive control. The next provider stage must use the exact same
persistent coordinator but obtain the action from the model, archive its
sanitized request/response, and report all attempts under the separate draft
manifest. `scripts/run_toolroute_otel_transport_provider.py` exists for that
stage and is fail-closed until the manifest SHA-256 is bound to the separate
provenance authorization field.

## Gemini v0.1 provider-pilot result and disposition

Nine Gemini 3.7 Flash calls completed across the three regimes and A/B/C under
`experiments/api-otel-transport-pilot/g2-calibrations/toolroute-otel-transport/`.
Direct post-run audit verified every finalization hash, the six real OTel spans
per episode, the parsed provider label, and the post-decision live action. The
descriptive means were A 6,768.67 ms regret with 2/3 successful actions, B
6,767.90 ms with 2/3, and C 0.00 ms with 3/3. In the latency and connection
faults, C selected the reported healthy route; in the beta-503 fault all
conditions selected the healthy alpha route.

This is promising live integration evidence, but it is **not** a cross-model
cohort. Audit found that v0.1 had an alpha-first listing pattern, an unbound
episode-level authorization metadata record, and misleading self-reported
external-subject check flags. The raw facts are retained rather than rewritten;
they remain useful to demonstrate the end-to-end path. They are not pooled with
the primary synthetic cohort or a later replication result.

`manifests/toolroute_otel_transport_pilot.v0.2.json` and
`docs/25_toolroute_otel_transport_v0_2_runbook.md` replace v0.1 for the fresh
cross-provider replication. v0.2 locks route assignment, option order, model,
provider, and per-model sequence before authorization, records the manifest and
Toxiproxy binary hashes per episode, and separates infrastructure checks from
the model's observed outcome.

## Why not the full OpenTelemetry Astronomy Shop demo?

The official Astronomy Shop is useful for later work: it is a near-real-world,
multi-service OpenTelemetry demonstration and exposes a larger observability
stack. For the current paper it would introduce a different task (diagnosis or
service remediation), many uncontrolled service dependencies, substantial setup
time, and an incompatible oracle. It would therefore dilute rather than
strengthen the clean ToolRoute question.

## Practical harness assessment and complexity

The existing SCAC harness is sufficient for a **transport-realistic controlled
replication**, not a production agent platform. That is the appropriate target.
It already owns the causal boundaries required by the paper: condition rendering,
host-only reduction, a tool executor, external evaluation, reservation-first
archives, and finalization hashes. It also already contains a native local HTTP
span capture path and a Toxiproxy transport strategy.

The missing work is a small integration adapter, not a new agent framework:

1. Replace the current direct HTTP-event construction for this extension with
   an OpenTelemetry-instrumented HTTP client and local span exporter.
2. Add a pure span-to-ToolRoute adapter that maps only the standard fields in
   the table above, preserving raw spans and a reducer-input record.
3. Add a persistent coordinator that owns two loopback services and proxies
   from monitor through selected action. Its visible task can be a normal
   read-only redundant-API task: retrieve the same customer/order record from
   either of two schema-compatible regional endpoints.
4. Add model-free lifecycle, redaction, order-balance, and oracle-margin tests;
   only then freeze a separate provider manifest.

This is **low-to-medium complexity** (roughly one focused engineering day),
because it extends existing boundaries. It does *not* need Docker, Kubernetes,
the OpenTelemetry Collector, an external vendor, or a complete agent framework.

| Candidate | What it establishes | Complexity now | Decision |
|---|---|---:|---|
| Native local HTTP + OTel SDK + Toxiproxy | Real socket calls, standard spans, controlled faults, host-to-agent state reduction | Low-medium | **Recommended** |
| MCP server plus provider-native function-calling loop | Modern protocol/tool-call mechanics in addition to telemetry | Medium-high; provider-specific schemas and loop semantics | Defer |
| Testcontainers + Toxiproxy | Containerized integration-test topology | Medium; requires Docker | Defer |
| Astronomy Shop + Collector/Jaeger/Prometheus | Multi-service production-like observability and diagnosis | High; changes task/oracle | Reject for this paper |
| Kubernetes + Chaos Mesh | Pod, resource, DNS, and network chaos | Very high; Linux/Kubernetes control plane | Future work |

The local machine currently has a runnable Toxiproxy binary but no visible
Docker, Docker Compose, or Kubernetes command. That reinforces the minimal
native path: Testcontainers and Chaos Mesh would require environment setup in
addition to experiment work.

### What is and is not realistic

The services can be intentionally simple and still be useful. Each route returns
the same read-only JSON record through a genuine HTTP request; they represent
two regional replicas or a primary/fallback API. The *transport* is real TCP/HTTP,
the telemetry is standard OTel span data, and the injected degradation uses a
widely used chaos-testing proxy. The data payload and fault schedule are
controlled so route utility remains auditable. This is a transport-realistic
integration test, not a claim that the toy record service reproduces a complete
production workload.

Using a deliberately minimal harness is a strength here. A full framework can
silently retry, choose fallback, cache responses, or rewrite tool calls; then a
measured improvement cannot be attributed cleanly to agent-visible telemetry.
The SCAC coordinator exposes only the strategic choice. Deterministic recovery
and safety remain outside the model.

MCP is relevant as a deployment adapter, not a prerequisite for the experiment:
an MCP client would translate a discovered tool into the same HTTP call and the
host-side snapshot policy would remain unchanged. Native provider function
calling similarly changes action syntax, not the information treatment. Both
are worthwhile later compatibility tests, but would add provider-specific
confounds to this pre-approval replication.

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
