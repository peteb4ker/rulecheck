# Benchwise — Design Session Hand-off

> **Superseded 2026-07-28:** the app was renamed **Benchwise -> Rule Check** (Xcode project `Benchside` -> `RuleCheck`). This document is kept as the record of what was decided at the time; the names below are historical.

For a design-focused Claude session working on the app's look and feel.
Read this, then CLAUDE.md, then the
[design spec](specs/2026-07-26-rulecheck-design.md). This document doesn't
repeat what those say; it adds the visual-design context and boundaries.

## What you're styling

**Benchwise** (Xcode project name: Benchside) is a free, fully offline iOS
rules reference for Pokemon TCG players and judges ("professors"). One
sentence: *look up rules fast — offline, search-first, answer in under two
seconds.* It is deliberately calm, utilitarian, and trustworthy — a tool a
judge cites mid-tournament, not a game companion with splash and particle
effects.

Two personas, one app: the **casual player** (types "asleep" mid-game,
reads one section, done) and the **judge** (needs the exact citation —
`§ 5.6.1`, document version — with total confidence). Speed-to-answer and
legibility beat delight everywhere they conflict.

## Current state (v1, merged)

Native SwiftUI, iOS 17.0+, intentionally stock-HIG: system fonts, SF
Symbols, standard `List`/`NavigationStack`, automatic dark mode, no custom
styling anywhere yet. That was a deliberate ship-fast baseline — the
"zhuzz" is now welcome, within the boundaries below.

Screens (all in `app/Benchside/`):

- **SearchView** (`Search/SearchView.swift`) — home. Always-visible search
  bar (`.navigationBarDrawer(displayMode: .always)`), segmented scope
  picker in a `.safeAreaInset` (All / Game Rules / Tournament), then
  either: browse list of the three documents (empty query), grouped search
  results (breadcrumb caption + title + snippet per row), or
  `ContentUnavailableView` states. Toolbar: info button → About.
- **SectionView** (`Reader/SectionView.swift`) — the reader. Breadcrumb
  caption, title (with `§ number` when citable), verbatim body in a
  `ScrollView`, "See also" cross-reference buttons, document version
  footer, prev/next in a bottom toolbar.
- **DocumentOutlineView** (`Reader/DocumentOutlineView.swift`) — flat
  section list per document, children indented 16pt.
- **AboutView** (`AboutView.swift`) — document versions, the not-affiliated
  disclaimer, zero-network statement, GRDB license note.
- **ErrorView** (`ErrorView.swift`) — `ContentUnavailableView` wrapper.
- **App icon: none yet** — this is the biggest visual gap. No launch
  screen design either (system-generated).

Data comes from `RulesRepository` (`Data/RulesRepository.swift`); view
model in `Search/SearchViewModel.swift`. You should not need to touch the
data layer for visual work.

## Hard boundaries (non-negotiable, from CLAUDE.md + research gate)

1. **No Pokemon character/species names or likenesses anywhere** — app
   icon, colors-as-character-reference (no Pikachu yellow + red cheek
   motif), screenshots, copy. Generic TCG vocabulary (bench, deck, prize,
   energy) is fine as *words*; TPCi's marks and art are not. The app icon
   especially must be original and character-free.
2. **Zero network calls.** No remote fonts, no fetched assets. Everything
   bundled.
3. **No new dependencies** without an explicit decision — currently GRDB is
   the only one. Custom fonts are possible but must be bundled and
   licensed; system fonts (incl. SF Rounded/Serif/Mono variants) are free
   wins.
4. **Legibility first.** Judges read this at arm's length in bad venue
   lighting. Dynamic Type must keep working; contrast ≥ WCAG AA; dark mode
   is a first-class citizen (venues are dim).
5. **The two persona acceptance tests and all UI tests must stay green**
   (`just app-test`, 19 tests). UI tests query by accessibility
   label/identifier — keep identifiers stable (`About`, search field,
   scope segment labels) or update the tests in the same PR.

## Where the visual identity is open

Everything not listed above. Specifically worth designing:

- **App icon** (the gap): character-free, reads at small sizes, feels like
  "rules, fast". Bench/whistle/book/section-mark (§) directions all open.
- **Accent color + palette**: currently default blue. A distinct accent
  (light+dark variants) would carry the brand through segmented control,
  links, and xref buttons.
- **Typography**: reader body is `.body` system; a serif or rounded
  variant for reader text, tuned line spacing/measure, and a stronger
  title treatment could lift it. Monospace for `§` citations is a nice
  judge-flavored touch.
- **Result rows**: breadcrumb/title/snippet hierarchy works but is plain;
  snippet match-highlighting (the DB delivers snippets — currently
  rendered as plain text) is an open opportunity.
- **Reader polish**: paragraph spacing (bodies are `\n`-joined lines),
  version-footer treatment, "See also" styling.
- **Empty/zero states, launch experience, About layout.**

## Working in this repo

- Follow CLAUDE.md: superpowers workflow (brainstorm → spec → plan →
  execute), work from a GitHub issue, branch + PR, squash merge, CI must
  be green. File an issue for the design work before coding.
- **The Xcode project is generated.** Never hand-edit
  `app/Benchside.xcodeproj` — edit `app/project.yml` and run
  `just app-gen`. New asset catalogs/resources get wired there.
- Build/test loop: `just app-db` once after a fresh checkout (copies the
  built database into Resources — Xcode Run fails on a missing
  `benchside.db` otherwise), then `just app-test` (full suite) or Xcode
  Run. Simulator: iPhone 17 Pro, iOS 26.5 installed on this machine.
- Signing for device installs is set locally in Xcode and is wiped by
  `just app-gen` (known papercut; DEVELOPMENT_TEAM not yet in project.yml).
- SwiftUI gotcha that cost us hours: view models are owned in `@State` at
  the root (`BenchsideApp.swift` — see the comment there). Don't construct
  observable models inline in `body`.

## Known issues that touch design

- #8 — several tcg-rules sections have garbled multi-column body text
  (being fixed pipeline-side; don't design around it, it's temporary).
- #22 — search autofocus on launch was removed (FocusState/identity bug);
  restoring it is open and may interact with any search-bar redesign.
- Content is verbatim-pending-rewrite (#20): body text will be replaced by
  paraphrase before public release. Reader design should not assume exact
  current line lengths.

## Definition of done for a design pass

- All 19 tests green; personas unaffected.
- Dark + light screenshots of every screen at default and XL Dynamic Type.
- No new IP exposure (icon + palette + copy reviewed against boundary #1).
- Docs synced (README screenshot section if screenshots are added).
