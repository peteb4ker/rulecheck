# Benchside

[![CI](https://github.com/peteb4ker/benchside/actions/workflows/ci.yml/badge.svg)](https://github.com/peteb4ker/benchside/actions/workflows/ci.yml)

A free, fully offline iOS app for Pokemon TCG players and professors (judges)
to look up rules fast. Search-first, works with zero connectivity, answers in
under two seconds.

**Status:** design phase. See the
[design spec](docs/superpowers/specs/2026-07-26-benchside-design.md).

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
