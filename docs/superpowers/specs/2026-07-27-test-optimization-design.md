# Test Feedback Loop Optimization (Issue #26) — Design Spec

**Date:** 2026-07-27 · **Status:** Approved by Pete

## Problem

`just app-test` costs 4+ minutes wall-clock; the CI app job runs ~7-8m.
Measured hotspots: cold xcodebuild builds (2-4 min), UI tests + simulator
churn (~40s+), and CI fetching/compiling GRDB from scratch every run.
Pipeline tests (0.2s) need nothing.

## Decisions

| Decision | Choice |
|---|---|
| Local inner loop | New `just app-test-unit`: `-only-testing:RuleCheckTests` on the already-booted simulator, no erase/boot churn. Persona gates are in the unit tier, so the release gate stays in the fast path. |
| Full gate | `just app-test` unchanged in meaning (unit + UI) — the pre-PR/CI tier. |
| Timing visibility | Both recipes print wall time (`time`), so regressions are visible in every run and PRs can quote before/after. |
| CI | ~~Cache SPM checkouts + DerivedData~~ **Evaluated and dropped** (2026-07-27): warm-cache app job measured 6m43s vs 6m39s cold — the job is ~entirely one xcodebuild step, and fresh macOS runners invalidate DerivedData regardless of cache. Per the data-first rule below, the cache was removed rather than kept as cargo cult. CI <5m needs different levers (e.g., unit-only PR tier with full suite on merge — a coverage decision, not taken unilaterally); documented on #26. |
| Deferred | `build-for-testing`/`test-without-building` split (niche win — our loop nearly always changes app code); parallel CI jobs (runner spin-up eats the gain at current suite size). Revisit with data. |
| Rule | Every change ships with before/after timings; anything that doesn't measurably help is dropped. |

## Acceptance (from #26)

- Inner-loop app test run under 60s warm. **Met: 3.8s.**
- CI app job under 5m (warm cache). **Not met — cache ineffective (see
  decision above); target requires a coverage-tier decision, deferred.**
- Full suite still green; persona gates present in both tiers. **Met.**
