# Benchside

[![CI](https://github.com/peteb4ker/benchside/actions/workflows/ci.yml/badge.svg)](https://github.com/peteb4ker/benchside/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/peteb4ker/benchside)](https://github.com/peteb4ker/benchside/releases)

A free, fully offline iOS app for Pokemon TCG players and professors (judges)
to look up rules fast. Search-first, works with zero connectivity, answers in
under two seconds.

**Status:** content pipeline complete; iOS app not yet started. See the
[design spec](docs/superpowers/specs/2026-07-26-benchside-design.md).

## Running the pipeline

One-time setup (Python 3.12+; PDFs go in `sources/`, registered in
`sources/sources.yaml`, and are never committed):

```bash
cd pipeline && python3.13 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'
```

Then, from `pipeline/` with the venv active:

```bash
python -m benchside_pipeline all --root ..
```

runs parse → build → verify and must end with `verify OK`. It writes
reviewable per-document JSON to `content/` (committed) and the app database
to `build/benchside.db` (git-ignored). Re-run after any `sources.yaml` edit
or document revision; `pytest` runs the suite, including two persona
acceptance tests against the built database.

## Layout

```
pipeline/          # Python: ingest, parse, build, verify rules content
sources/           # source PDFs + sources.yaml manifest
content/           # parsed intermediate JSON (committed, reviewable)
app/               # Xcode project: Benchside (SwiftUI + GRDB)
docs/superpowers/  # specs, plans, research notes
```

## CI

Every PR runs [CI](.github/workflows/ci.yml): repo guards (no committed
PDFs or build products, manifest/content validity, workflow lint),
pipeline `pytest` plus a build+verify of committed content, and the app's
`xcodebuild test` when app-relevant paths change. PR titles must be
Conventional Commits (squash merge uses them as commit subjects).

Benchside is not affiliated with or endorsed by The Pokemon Company
International, Nintendo, Creatures, or GAME FREAK.
