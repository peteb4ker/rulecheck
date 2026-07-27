# Test Feedback Loop Optimization (Issue #26) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get the warm app-test inner loop under 60s and the CI app job under 5m, with timings visible in every run.

**Architecture:** Tiered justfile recipes (`app-test-unit` fast tier, `app-test` full gate) + CI caching of SPM/DerivedData with a pinned derived-data path. Data-first: baseline measured before, results quoted after; no speculative machinery.

**Tech Stack:** just, xcodebuild, actions/cache.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-27-test-optimization-design.md`
- Persona gates run in BOTH tiers; full suite must stay green (43 pipeline + 19 app tests).
- Conventional Commits with the `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` trailer; PR closes #26 with before/after timings.

---

### Task 1: Baseline + tiered local recipes

- [ ] Measure baseline: time a warm `just app-test` (record) and a warm `-only-testing:BenchsideTests` run (record).
- [ ] justfile: add under the iOS block:

```just
# Fast inner loop: unit tests only (incl. persona gates), no sim churn
app-test-unit: app-db
    cd app && time xcodebuild test -project Benchside.xcodeproj -scheme Benchside \
      -destination 'platform=iOS Simulator,name={{_first-sim}}' \
      -only-testing:BenchsideTests -quiet
```

and wrap the existing `app-test` xcodebuild invocation with `time`.

- [ ] Verify: `just app-test-unit` green and under 60s warm; record time.
- [ ] Commit `feat(tooling): fast app-test-unit tier with timing output`.

### Task 2: CI caching

- [ ] `.github/workflows/ci.yml` app job: before the xcodebuild step add

```yaml
      - name: Cache SPM + DerivedData
        uses: actions/cache@v4
        with:
          path: app/ci-derived
          key: xcode-${{ runner.os }}-${{ hashFiles('app/Benchside.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved', 'app/project.yml') }}
          restore-keys: xcode-${{ runner.os }}-
```

and add `-derivedDataPath ci-derived` to the job's xcodebuild invocation (path relative to `app/`).

- [ ] Verify on the PR: first run seeds the cache; re-run (or follow-up commit) must show the app job under 5m and SPM "resolved" without fetching. Quote both timings in the PR.
- [ ] Commit `ci: cache SPM checkouts and derived data for the app job`.

## Definition of Done

- Warm `just app-test-unit` < 60s, green, persona gates included.
- CI app job < 5m on warm cache (evidence: two CI runs quoted in PR).
- `just app-test` full gate unchanged in coverage; all suites green.
