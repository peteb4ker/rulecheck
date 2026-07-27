# Benchside — Design Spec

**Date:** 2026-07-26
**Status:** Approved by Pete (brainstorming session)
**Name:** Benchside — repo, project, and public App Store name (availability check in Research Gate)

## What this is

Benchside is a free, fully offline iOS app that lets Pokemon TCG players and
professors (judges) look up rules fast. A search-first interface over the
official core game rulebook and the Play! Pokemon tournament documents,
optimized for "phone in hand, answer in under two seconds, no venue Wi-Fi."

## Personas

**The casual player.** Mid-game, types "asleep", wants the special-condition
mechanic explained in seconds. Searches by mechanic name (one or two words),
reads one section, done. Doesn't know or care about document names or section
numbers. Corpus: the trading card game rules reference.

**The professor/judge.** Mid-tournament, needs an authoritative citation —
exact wording, section number, and confidence it's the current revision.
Searches "deck check penalty", "time extension". Cares about breadcrumbs
(`Tournament Rules Handbook § 5.2`), verbatim text, and document version/date.
Corpus: tournament rules handbook + penalty guidelines.

These personas are acceptance anchors:

1. Player types **"asleep"** → first result is the Asleep special-condition
   section from the game rules.
2. Judge types **"deck check"** → first result is the relevant tournament
   handbook section, citable by section number.

Both run as automated tests against the real shipped database.

## Decisions locked in

| Decision | Choice |
|---|---|
| Content scope | Core game rulebook + tournament rules handbook + penalty guidelines. Informal names used throughout this spec; the exact TPCi document titles and versions are pinned in `sources.yaml` at ingest time |
| Lookup UX | Search-first: instant as-you-type full-text search; browse as secondary |
| Offline | Fully offline; all content bundled; app makes zero network calls |
| Content source | Ingest official TPCi documents; surface rule text verbatim by default, gated on the Research Gate below |
| Stack | Native SwiftUI, iOS 17+, GRDB as the only dependency |
| Content updates | Baked in; new app release when TPCi revises a document |
| Pricing | Free, no ads, no IAP for v1; future tiers possible (nothing structural needed now) |
| v1 features | Search + read only. No bookmarks, history, or judge tools in v1 |
| Name | Benchside everywhere — repo, Xcode project, and App Store |

## Architecture

Two halves: a content pipeline that runs on the development Mac, and a thin
SwiftUI app that ships with the pipeline's output.

### Content pipeline (`pipeline/`, Python)

1. **Ingest** — source PDFs live in `sources/`, registered in `sources.yaml`
   (document name, version, publication date, origin URL). PDFs are
   git-ignored if the Research Gate concludes we cannot redistribute them;
   the pipeline reads them locally either way.
2. **Parse** — extract each document into a tree: document → chapter →
   section → subsection. Each node gets a stable human-readable ID
   (e.g. `trh-5.2`), title, body text, and breadcrumb path. Cross-references
   ("see section 7.1") are detected and stored as links.
3. **Build** — emit one SQLite file:
   - `documents` (id, name, version, publication date — shown in-app)
   - `sections` (id, doc, breadcrumb, title, body, sort order)
   - FTS5 virtual table over title + body, title weighted higher
4. **Verify** — fails the build on empty sections, broken cross-references,
   or duplicate IDs.

The parsed intermediate JSON per document is committed to `content/` so
content changes are reviewable as git diffs, even though PDFs and the DB are
build products.

### iOS app (`app/`, SwiftUI)

- **Data layer** — GRDB over the bundled read-only SQLite file. A single
  `RulesRepository` exposes: `search(query:scope:)`, `section(id:)`,
  `children(of:)`, `documents()`. Nothing above it knows SQL exists.
  Search uses FTS5 with `bm25()` ranking and `snippet()` for highlighted
  excerpts.
- **Screens** (no tab bar in v1):
  1. **Search** (home) — search field focused on launch; results as you
     type, grouped by document, each showing breadcrumb, title, highlighted
     snippet. A segmented scope control above results: **All / Game Rules /
     Tournament**; last selection persists (`@AppStorage`). Below an empty
     search field: the document list as browse entry points.
  2. **Reader** — one section: breadcrumb, section number in the title,
     verbatim body, tappable cross-references, prev/next navigation,
     document version + date shown discreetly.
  3. **About** — document versions, unofficial-status disclaimer ("not
     affiliated with or endorsed by The Pokemon Company International,
     Nintendo, Creatures, or GAME FREAK"), licenses, privacy statement
     (zero network calls).
- **State** — plain `@Observable` models. No persistence beyond the bundled
  DB and the `@AppStorage` scope preference.

### Data flow

Bundled SQLite → `RulesRepository` → observable view models → SwiftUI.
Search keystrokes debounced ~150 ms. Scope filter adds a `WHERE doc IN (...)`
clause. Tapping a hit pushes the Reader with a section ID; cross-reference
taps push further Readers.

## Error handling

The app has no network and a read-only bundled database, so the failure
surface is deliberately tiny:

- **Corrupt/missing DB** — repository fails gracefully to an error screen;
  never crashes.
- **FTS query syntax** — user input is never passed to FTS5 raw; the
  repository tokenizes input into sanitized prefix-match tokens.
- **Zero results** — explicit empty state with a hint ("try fewer or
  different words") and the browse list as fallback.

## Testing

- **Pipeline:** Python unit tests for structure extraction, ID stability,
  and cross-reference detection using small fixture PDFs. The verify step
  doubles as an integration test on real sources.
- **App:** unit tests for `RulesRepository` against a fixture DB built by
  the same pipeline code; FTS input-sanitizer tests; the two persona
  acceptance tests run against the real shipped DB so ranking regressions
  are caught; a handful of UI tests covering search → read →
  cross-reference navigation.
- **Release gate:** manual spot-check of new content against source
  documents; verify version strings.

## Research Gate (pre-ship, parallel with development)

A discrete research step, findings written to `docs/superpowers/research/`
with citations. Verbatim body text is the default the pipeline produces;
this gate decides per-document whether verbatim survives to ship or gets a
rewrite pass. The pipeline and app are identical either way.

1. **Copyright status of rules text.** Game mechanics are not copyrightable
   (17 USC §102(b); *Baker v. Selden* line), but TPCi's literal prose
   generally is. Document where the line sits per document, the risk of
   verbatim surfacing, and any merger-doctrine/fair-use arguments.
   Output: ship/rewrite decision per document.
2. **Pokemon Terms of Use.** Analyze
   <https://www.pokemon.com/us/legal/terms-of-use> (Pete's reference) for
   terms governing reuse of downloaded documents.
3. **Precedents.** How unofficial companion/rulings apps (Pokemon and MTG
   judge apps) have fared on the App Store.
4. **Name availability.** "Benchside" on the App Store plus a USPTO
   trademark scan. Quick web screens found no collisions. Prior candidates
   rejected: "Prof's Companion" (existing tutoring business), "TopCut"
   (topcut.cards, an existing Pokemon website). Names containing Pokemon
   character/species names (e.g., "Rotom") are out of bounds — character
   names are TPCi trademarks and actively enforced, unlike rules facts.
5. **App Store posture.** Disclaimer wording and Apple guideline 5.2
   (intellectual property) requirements for unofficial companion apps.

## Repo layout

```
pipeline/          # Python: ingest, parse, build, verify
sources/           # source PDFs + sources.yaml manifest
content/           # parsed intermediate JSON (committed, reviewable)
app/               # Xcode project: Benchside (SwiftUI + GRDB)
docs/superpowers/  # specs, plans, research notes
```

## Out of scope for v1

- Bookmarks, history, judge tools (penalty matrix, timers, randomizers)
- Rulings compendium and card legality/errata content
- Remote content refresh, any networking, analytics
- Android / cross-platform
- Paid tiers (future possibility; nothing in v1 blocks them)
