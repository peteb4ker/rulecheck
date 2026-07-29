# CLAUDE.md

Steering for AI agents working on RuleCheck.

## What this project is

> **RuleCheck lets Pokemon TCG players and professors look up rules fast — offline, search-first, answer in under two seconds.**

Every PR is evaluated against that sentence. The full design is in
[docs/superpowers/specs/2026-07-26-rulecheck-design.md](docs/superpowers/specs/2026-07-26-rulecheck-design.md);
the spec wins if this file and the spec ever disagree.

### Out of scope (do not propose)

- Rulings compendium, card legality/errata, deck building, collection tracking
- Bookmarks, history, judge tools (v2 candidates, not v1)
- Any networking in the app, analytics, error tracking, servers, remote config
- Android / cross-platform

## Non-negotiables

- **The app makes zero network calls. Ever.** No analytics, no telemetry, no
  "report a bug" upload, no CDN config. This is a shipped promise, not a default.
- **No verbatim source text in the repository.** `sources/*.pdf` is
  git-ignored and so is the full parse artifact `build/content/`. What is
  committed is `content/*.json` — structure, citations and body *lengths*,
  no prose — plus `content/fingerprints/` (one-way hashes that keep the
  paraphrase tripwire working without the text). A CI guard fails the
  build if any committed section carries a `body`.
- **Verbatim rules text is gated on the Research Gate** in the spec. Don't
  ship or publicize content decisions before that research is done.
- **No Pokemon character/species names anywhere user-facing** (app name,
  screenshots, marketing). Character names are TPCi trademarks; rules facts
  are not. The app carries the standard not-affiliated disclaimer.
- **Never push to `main`.** Branch, PR, let CI run. No bypassing hooks or
  checks (`--no-verify` is off the table), even for one-liners.
- **Don't dismiss failing CI as "pre-existing."** Red check = your problem
  until proven otherwise.

## Development loop

1. **Understand before changing.** Root-cause bugs before proposing fixes —
   confirm with code reading or a live probe, don't pattern-match from
   training data. Be honest about uncertainty; if a diagnosis is a guess,
   say so.
2. **Pull from issues.** GitHub Issues is the backlog. Work described in
   conversation gets an issue first. Adjacent problems found mid-task get
   follow-up issues, not drive-by fixes.
3. **Branch** off fresh `main` with `feat/`, `fix/`, `chore/`, `docs/`,
   `ci/`, `refactor/`, or `test/`.
4. **Implement with TDD.** Smallest diff that does the job. Plans live in
   `docs/superpowers/plans/` and are executed task-by-task.
5. **Sync docs in the same PR** when behavior changes (README, spec, this
   file when the workflow itself changes).
6. **Commit**: Conventional Commits; body says why; keep the
   `Co-Authored-By: Claude` trailer.
7. **PR**: Conventional Commits title, summary + test plan in body,
   `Closes #N`. **Squash merge.**

## Quality gates

- **Pipeline** (`pipeline/`, Python, via uv — `just test`): `pytest` green,
  always. Logic changes have unit tests — no exceptions. Every module gets
  a test file.
- **App** (`app/`, Swift): Xcode unit + UI tests green. The two persona
  acceptance tests (player: "asleep"; judge: "deck check") must pass against
  the real database before any release.
- **No placebo tests.** A bug fix's test must fail on `main` and pass with
  the fix — verify both directions. Never `.skip()` a failing test; fix the
  root cause.
- **Fail loudly.** Pipeline verify errors fail the build; app data-layer
  failures show an error screen, never a silent `print`.
- **CI enforces the gates.** `.github/workflows/ci.yml` runs the guard
  checks (no PDFs/DBs in git, manifest + content validity), pipeline
  tests, content build+verify, and app tests on app-relevant changes.
  The macOS app job bills at 10x Linux, so it runs on **pull requests
  only** — never on pushes to `main`, since squash-merge means the
  landed tree is the one the PR tested. A daily scheduled run verifies
  `main`; `gh workflow run ci.yml` forces one on demand.
  Checks are advisory (no branch protection on the current GitHub plan) —
  a red check still means stop and fix.

## Working files

Scratch — build artifacts, screenshots, drafts, anything that is working
material rather than repository content — goes in `.scratch/` at the repo
root, which is git-ignored. Not the user's Desktop, not `/tmp`.

## Layout

```
justfile           # dev commands: just setup / all / test / download …
pipeline/          # Python: ingest → parse → build → verify
sources/           # sources.yaml manifest (+ git-ignored PDFs)
content/           # committed index: structure + citations, no prose
content/fingerprints/  # one-way hashes backing the paraphrase tripwire
build/content/     # full parsed text, verbatim (git-ignored)
build/             # rulecheck.db build product (git-ignored)
.scratch/          # local working files (git-ignored)
app/               # Xcode project: SwiftUI + GRDB, iOS 17+
docs/superpowers/  # specs, plans, research notes
```

The SQLite schema in `pipeline/src/rulecheck_pipeline/build.py` is the
contract between pipeline and app. Schema changes touch both sides in the
same PR, or ship pipeline-first with backward compatibility.

## Working style

- Don't assert functionality works without having run the verification.
- Report findings before fixing things the user hasn't asked you to fix.
- Follow the superpowers workflow: brainstorm → spec → plan → execute.
