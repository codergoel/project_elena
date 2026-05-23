# Observability and alerting (Phase 10)

The API exposes structured access logs, optional Prometheus scraping, request correlation via `X-Request-ID`, and Redis quota counters suited to alerting dashboards.

## Request correlation

Middleware sets `request.state.request_id` and echoes [`X-Request-ID`](https://httpwg.org/specs/rfc7231.html). During request handling you can read the same value via `elena.observability.request_context.current_request_id` (services API package).

Access logs use the **`elena.access`** logger: one INFO line per completed HTTP exchange (method, matched route template, status, latency, request id).

## Prometheus (`GET /metrics`)

Disabled by default. Enable with **`EXPOSE_PROMETHEUS_METRICS=true`** in the API environment (`settings.expose_prometheus_metrics`). Bind scrapes to loopback or a private network segment; omit from public ingress when possible.

```bash
curl -sS localhost:8000/metrics | head
```

### Primary series

| Metric | Purpose |
| --- | --- |
| `http_requests_total{method,route,status_class}` | Error-rate numerator/denominator by route template (`2xx`–`5xx` buckets). |
| `http_request_duration_seconds_*` | End-to-end ASGI latency at middleware. |
| `elena_latex_compile_total{ok}` | PDF compile spine outcomes (`ok=false` ⇒ subprocess failure). |
| `elena_latex_compile_duration_seconds_*` | Wall time inside `compile_resume_tex`. |
| `elena_quota_rejection_total{scope}` | Trailing-edge 429 bursts (`compile`, `agent_turn`, `import_llm`, …). |
| `elena_agent_turn_total{outcome}` | LangGraph turns (`success`, `graph_exception`). |
| `elena_agent_turn_wall_seconds_*` | Wall clock around `graph.ainvoke`. |
| `elena_import_llm_calls_total{outcome}` | LLM import mapper attempts (`success`, `failure`). |

Spend / token accounting needs provider metering (Gemini, OpenAI) or fuller tracing — deferred per roadmap `10.1`.

### Example alerting snippets

Tune windows and thresholds to your tier.

```yaml
groups:
  - name: elena.alerts
    rules:
      - alert: ElenaHighFiveXXRate
        expr: |
          sum(rate(http_requests_total{status_class="5xx"}[5m]))
            /
          sum(rate(http_requests_total[5m]))
            > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: API 5xx share above 5%

      - alert: ElenaLatexCompileFailures
        expr: |
          sum(rate(elena_latex_compile_total{ok="false"}[10m]))
            /
          sum(rate(elena_latex_compile_total[10m]))
            > 0.20
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: LaTeX compile failure ratio high

      - alert: ElenaQuota429Spike
        expr: sum(rate(elena_quota_rejection_total[5m])) > 10
        for: 2m
        labels:
          severity: info
        annotations:
          summary: Redis quota saturation across scopes
```

## Backlog

1. Scrape infra exporters (Postgres, Redis, node) beside the FastAPI histograms.
2. Ship structured logs (JSON pipeline) keyed on request id alongside metrics.
3. When LangSmith/OTel is enabled, correlate trace ids with HTTP request ids (`10.1`).
