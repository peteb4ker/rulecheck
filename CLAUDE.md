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
- **Accuracy beats overlap.** Never reword a rule into something weaker to
  get clear of the paraphrase tripwire. Where the exact wording is the rule,
  quote it and declare it. The Research Gate closed on 2026-07-26 on exactly
  this: faithful paraphrase by default, short verbatim quotes where exact
  wording is load-bearing for judges. The undeclared limit is 25 consecutive
  tokens, aimed at source prose pasted in wholesale rather than at stating a
  rule precisely. Rules are systems and are not themselves copyrightable;
  what is protected is their creative expression, so the risk is reproducing
  the document, not sharing a sentence that states a rule.
  `just transformation-report` quantifies where the corpus sits: declared
  quote share against budget, the distribution of longest shared token runs,
  and how much shorter the paraphrase is than its source. It needs the PDFs,
  so it is a local and pre-release check rather than a CI gate. Read the
  median and 95th percentile, never the maximum: the tripwire fails the build
  at 12 tokens, so the maximum is censored at 11 by construction.
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
  **`main` is protected by a ruleset and a red check blocks the merge.**
  Required: `detect`, `guards`, `pipeline`, `app`, `conventional-title`
  and both CodeQL analyses, plus a pull request, no force pushes and no
  branch deletion. Public repositories get this free, which the old note
  about the plan predates.

  A ruleset rather than classic branch protection, because a ruleset
  treats a `skipped` check as passing. That is what lets the macOS `app`
  job be required even though it is skipped on content-only changes;
  classic protection would wait forever for a check that never arrives.

  Read every row of `gh pr checks`, not the tail.

## The lexicon

The game's vocabulary, classified into entity, action, state, modifier and
phase. It backs the icon set, search synonyms and eventually a knowledge graph.

The methodology is the asset, not the file. Source documents get revised and
parsing changes, so the lexicon must be re-derivable rather than hand-curated:

    just lexicon-candidates   # what is written often (frequency)
    just lexicon-structural   # what rules turn on (concepts)
    ...classify the delta...  # .claude/skills/build-lexicon/SKILL.md
    just check-lexicon        # independent validation, reports coverage

Two signals, and frequency is the weaker one. "Knock Out" ranks 2544 by
frequency and first by structure; "competitor" is written 462 times and is not
a game concept. Structure has no occurrence floor, since "mulligan" appears
four times and is still a rule.

Inflections group (evolve, evolves, evolving). Derived words do not, because
`attacker` is an entity and `attack` is an action. Never hand-edit the lexicon
into a state you could not reproduce.

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
content/lexicon/   # classified game vocabulary (not a parsed document)
build/content/     # full parsed text, verbatim (git-ignored)
build/             # rulecheck.db build product (git-ignored)
.scratch/          # local working files (git-ignored)
app/               # Xcode project: SwiftUI + GRDB, iOS 17+
docs/superpowers/  # specs, plans, research notes
```

Document order on the browse screen follows `sources/sources.yaml`, carried
through as `documents.sort_order`. Players meet the game rules first, then
tournament rules, then the penalty guidelines.

The SQLite schema in `pipeline/src/rulecheck_pipeline/build.py` is the
contract between pipeline and app. Schema changes touch both sides in the
same PR, or ship pipeline-first with backward compatibility.

## Working style

- Don't assert functionality works without having run the verification.
- Report findings before fixing things the user hasn't asked you to fix.
- Follow the superpowers workflow: brainstorm → spec → plan → execute.
