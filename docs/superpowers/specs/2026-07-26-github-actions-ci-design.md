# Benchside — GitHub Actions CI Design Spec

**Date:** 2026-07-26
**Status:** Designed autonomously per Pete's request ("build out robust gh actions CI"); decisions documented here for review
**Issue:** #2

## Problem

CLAUDE.md's development loop depends on CI ("Branch, PR, let CI run"; "Red
check = your problem until proven otherwise"), and the content-pipeline plan
assumes CI exists (Task 10: persona tests "auto-skip … so CI without real
sources stays green"). But the initial build includes no CI: the design
spec's Testing section defines what to test, not automation, and the repo
has no `.github/` directory. Nothing runs on PRs today.

## Constraints that shape the design

1. **The repo is docs-only right now.** `pipeline/` and `app/` are planned
   but don't exist. CI must be green today and pick up each half
   automatically when it lands — no follow-up "turn on CI" PR.
2. **Source PDFs are never in git.** CI can never run `parse`, but `build`
   and `verify` need only the committed `content/*.json`, so full content
   validation works in CI without PDFs. Pipeline unit tests use generated
   fixture PDFs (reportlab) and need no real sources either.
3. **macOS minutes are expensive.** Private repo on the free plan: macOS
   runners bill at 10×. The app job must not run on every docs change.
4. **No branch protection available.** Free-plan private repos can't
   require status checks. CI is advisory until the repo goes public or the
   plan changes; the workflow culture in CLAUDE.md ("red check = your
   problem") is the enforcement mechanism meanwhile.
5. **Repo non-negotiables are checkable.** No committed PDFs, no committed
   `build/` products — cheap to enforce mechanically on every PR.

## Approaches considered

- **A. Minimal placeholder now, real CI later** — one workflow that lints
  docs; add pipeline/app jobs in their own PRs. Rejected: guarantees a
  future PR mixes CI changes with feature changes, and the non-negotiable
  guards are worth having immediately.
- **B. One workflow, existence-gated jobs (chosen)** — a single `ci.yml`
  where a cheap detect job checks what exists and what changed; downstream
  jobs run conditionally. One place to read, one status-check family,
  shared detection logic.
- **C. Split workflows with `paths:` filters** — `pipeline.yml`,
  `app.yml`, `guards.yml`, each path-triggered. Rejected: `paths:` filters
  skip whole workflows silently (a schema change in `pipeline/build.py`
  wouldn't trigger app tests), and cross-cutting conditions (exists AND
  changed AND schedule-override) don't fit workflow-level filters.

## Design

Two workflow files.

### `.github/workflows/ci.yml`

Triggers: `pull_request` (all branches), `push` to `main`, weekly
`schedule` (Monday 06:17 UTC — catches runner-image/dependency drift on a
quiet repo), and `workflow_dispatch` for manual runs.

Workflow-level `permissions: contents: read`. Concurrency group per ref,
`cancel-in-progress` on PRs only (never cancel a `main` or scheduled run).
Every job has a `timeout-minutes`.

**Job `detect`** (ubuntu, ~seconds). Checks out and emits outputs:

- `has-pipeline` — `pipeline/pyproject.toml` exists
- `has-app` — an `app/*.xcodeproj` exists
- `has-content` — any `content/*.json` exists
- `app-relevant` — true on push/schedule/dispatch; on PRs, true when the
  diff against the merge base touches `app/**`, `content/**`,
  `pipeline/src/benchside_pipeline/build.py` (the schema contract), or
  `.github/workflows/**`

**Job `guards`** (ubuntu, always runs). The repo's non-negotiables plus
workflow hygiene:

1. Fail if git tracks any `*.pdf` (spec: source PDFs are never committed).
2. Fail if git tracks anything under `build/` or any `*.db` file.
3. `sources/sources.yaml` parses as YAML (when present).
4. Every `content/*.json` parses as JSON (when present).
5. `actionlint` (pinned version) over `.github/workflows/`.

**Job `pipeline`** (ubuntu, `needs: detect`, runs when `has-pipeline`).
Python 3.12 via `actions/setup-python` with pip caching:

1. `pip install -e '.[dev]'` in `pipeline/`.
2. `pytest -v` — the full suite, fixture-based, no real PDFs needed.
3. When `has-content`: `python -m benchside_pipeline build` then `verify`
   against the committed JSON — the verify step's build-failing checks run
   on every PR, so a bad content commit can't land quietly. (`parse` is
   excluded; it needs the git-ignored PDFs.)

**Job `app`** (macos-15, `needs: detect`, runs when `has-app` AND
`app-relevant`). Discovers the single `.xcodeproj` under `app/` and its
first shared scheme via `xcodebuild -list`, then runs
`xcodebuild test` against an iPhone simulator on the runner's newest
installed iOS runtime. This includes the two persona acceptance tests,
which auto-skip when the real DB isn't built (mirroring the pipeline
plan's Task 10 behavior). Assumptions to revisit in the app PR: project
named by discovery (no hardcoding), one test-bearing scheme.

### `.github/workflows/pr-title.yml`

`pull_request` on `opened | edited | synchronize | reopened`. One tiny
ubuntu job greps the PR title against Conventional Commits using exactly
the types CLAUDE.md allows as branch prefixes:
`^(feat|fix|chore|docs|ci|refactor|test)(\([a-z0-9-]+\))?!?: .+`.
The repo squash-merges, so the PR title becomes the commit subject on
`main` — this check is what keeps `main` history conventional. No
third-party action; `github.event.pull_request.title` into a shell test.

### Action pinning

Only first-party `actions/*` actions, pinned to major versions
(`actions/checkout@v4`, `actions/setup-python@v5`). No third-party
actions; anything else (actionlint, title check) is a pinned-version
download or plain shell. Keeps the supply-chain surface at "GitHub
itself."

### Docs sync (same PR)

- README gets a CI badge and one sentence on what CI covers.
- CLAUDE.md Quality gates section notes that CI enforces the pipeline and
  app gates plus the no-PDF/no-DB guards, and that checks are advisory
  (no branch protection on the current plan) — red still means stop.

## Error handling

- Detect-job output misfires fail closed for guards (always run) and fail
  open for the app job only via `app-relevant` path narrowing — but push,
  schedule, and dispatch runs always include the app job, so a path-filter
  gap is caught at merge and weekly, never lingering.
- Guard failures print the offending file list, not just a nonzero exit.
- The app job fails with an explicit message if it can't discover exactly
  one `.xcodeproj` or any scheme, rather than xcodebuild's opaque errors.

## Testing the CI itself

- `actionlint` runs locally before commit and in the guards job forever.
- The PR that introduces CI is its own integration test: all jobs must
  run (or visibly skip, for pipeline/app) and pass on the PR before merge.
- Guard checks are exercised by inspection at review time (deliberately
  committing a PDF to test them is not worth the history pollution).

## Out of scope

- CD / release automation (TestFlight, App Store) — nothing to release.
- Branch protection / merge queue — unavailable on the current plan.
- Coverage reporting, ruff/linting for Python, SwiftLint — nothing in the
  repo's plans mandates them; add via their own issue when wanted.
- Caching Xcode DerivedData — premature before the app exists.
