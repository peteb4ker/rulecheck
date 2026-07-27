# Benchside

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

Benchside is not affiliated with or endorsed by The Pokemon Company
International, Nintendo, Creatures, or GAME FREAK.
