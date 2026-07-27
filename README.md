# Benchside

[![CI](https://github.com/peteb4ker/benchside/actions/workflows/ci.yml/badge.svg)](https://github.com/peteb4ker/benchside/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/peteb4ker/benchside)](https://github.com/peteb4ker/benchside/releases)

A free, fully offline iOS app for Pokemon TCG players and professors (judges)
to look up rules fast. Search-first, works with zero connectivity, answers in
under two seconds.

**Status:** content pipeline complete; iOS app not yet started. See the
[design spec](docs/superpowers/specs/2026-07-26-benchside-design.md).

## Running the pipeline

One-time bootstrap:

```bash
brew install uv
uv tool install rust-just
just setup
just download   # PDFs are git-ignored, so a fresh clone needs this once (network)
```

Day to day:

```bash
just all        # parse → build → verify (offline; ends "verify OK")
just test       # pytest suite
just download   # fetch official PDFs (network; exits 1 if TPCi revised a doc)
```

`just` with no arguments lists every recipe. PDFs land in `sources/`
(never committed; `sources.yaml` records each document's origin URL and
sha256). Parsed JSON goes to `content/` (committed, reviewable); the app
database to `build/benchside.db` (git-ignored). Re-run `just all` after
any `sources.yaml` edit or document revision.

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
