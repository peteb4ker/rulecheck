# Solar/Lunar Visual Spec — Implementation Design

**Date:** 2026-07-27
**Issue:** #29 (phase 1 — no diagram views)
**Sources of truth:** the claude.ai/design package (`Benchwise Handoff.dc.html`,
project `18896e4a-5646-4ede-8df9-a90bf1e89b71`) for tokens/type/metrics/locked
layouts; `docs/superpowers/2026-07-27-design-handoff.md` for boundaries;
the product spec + CLAUDE.md over both where scope conflicts.

## What this implements

The Solar/Lunar identity from the design package, applied to the existing
SwiftUI screens: one palette in two temperatures (warm paper + amber by day,
indigo + pale gold by night — dark mode is an identity, not an inversion),
the type ramp (system fonts, monospaced glyphs for every citation/breadcrumb/
section label), the locked search/results layouts, browse document cards with
hue markers, and a token pass over About/outline/error/empty states plus the
launch screen.

## Explicitly out of scope (and why)

- **SectionView diagram views + Diagram/Exact-wording toggle** — blocked on
  issue #20's authored content schema; the toggle additionally conflicts with
  the research-gate decision (declared short quotes only, never full
  verbatim). The reader gets tokens and typography only.
- **"Recent" list on the browse screen** — the mock shows it, but history is
  explicitly out of scope for v1 in the product spec and CLAUDE.md, which win
  over the mock. Deliberately omitted; a v2 candidate.
- **`negative` token** — used only by the diagram effects table (blocked
  above). Not created until something consumes it.
- **App icon** — the handoff marks it "explored and rejected — needs a real
  vector pass". Deferred to its own issue/PR.
- **pipeline/, content/, sources/** — this effort owns `app/` (and
  `app/project.yml`) exclusively.

## Token architecture

`app/Benchside/Palette.xcassets` with one Color Set per token, **Any
appearance = Solar (light), Dark appearance = Lunar**. Hex values from the
handoff tables verbatim (the handoff states hex is the intended sRGB
rounding of the authoritative oklch for the asset catalog). Exposed through
a single `Palette` enum (`Palette.canvas`, …) — no raw `Color("name")`
strings at call sites.

| Token | Solar (light) | Lunar (dark) | Role |
|---|---|---|---|
| canvas | #FBF4E8 | #13112A | App background |
| surface | #FFFFFF | #1E1B3C | Result/reader cards, search field |
| sunken | #F1E4D0 | #241F45 | Segmented track, chip fill (dark table calls this "raised") |
| selected | #FFFFFF | #3B3568 | Segmented thumb (light mock thumb is white) |
| hairline | #EDDFC8 | #2E2A56 | Dividers, card borders |
| ink | #1C1611 | #F3F0FF | Titles, primary text |
| body | #463726 | #C9C3E8 | Snippets, reader body |
| secondary | #7A6A58 | #A099C8 | Breadcrumbs, captions, section labels |
| accent | #C67C22 | #E9CE7B | Selected scope, links, § citations, focus |
| accentPressed | #AF681F | #D4B863 | Pressed/active states (dark value derived: gold stepped down one lightness notch; the handoff specifies light only) |
| onAccent | #FFFFFF | #241804 | Text on filled accent (light value derived; handoff specifies dark only) |
| highlight | #FAE6B6 | #5B4718 | Search-match background |
| highlightInk | #6E3F10 | #FAEEBD | Search-match text |
| docGame | #C67C22 | #E9CE7B | Game Rules hue marker |
| docTournament | #7A4A86 | #A48BD6 | Tournament Rules hue marker |
| docPenalty | #9E4F2B | #C589CE | Penalty Guidelines hue marker |

Two mock-only grays (#8A7A63 labels, #D9C6A6 chevrons/clear button) are
**not** tokens — the token table's `secondary` covers labels; chevrons use
`secondary` at reduced opacity. Where the mocks and the token table
disagree, the token table wins (it is the named contract).

Doc-hue mapping lives on the app side keyed by document id
(`tcg-rules → docGame`, `tournament-rules → docTournament`,
`penalty-guidelines → docPenalty`), falling back to `accent` for unknown
ids — fail-soft, never crash on future documents.

## Type ramp (all Dynamic-Type text styles, never fixed points)

| Role | SwiftUI |
|---|---|
| App title | `.largeTitle.bold()`, tracking −0.9 |
| Reader title | `.largeTitle.bold()` |
| Row title | `.headline` |
| Body + snippet | `.subheadline`, `lineSpacing 3` |
| Citation, breadcrumb | `.caption.monospaced()` |
| Section label | `.caption2.monospaced()`, kerning 1.2, uppercased |
| Nav/links/prev-next | `.body` / `.subheadline` |
| Scope segment | stock segmented control (see below) |

## Screen-group designs

### 1 — Snippet match highlighting (highest value, ships first)

**Root cause of "plain snippets":** `RulesRepository.search` currently calls
`snippet(sections_fts, 1, '', '', '…', 14)` — empty start/end markers, so
match positions are discarded before the app ever sees them. The design
note's "the DB already returns snippets with match ranges" is what FTS5
*can* do, not what the query asks for.

Fix, app-side only:
- Markers become Unicode private-use sentinels `\u{E000}`/`\u{E001}` in the
  SQL (they cannot occur in rules text, which the pipeline sources from
  PDFs; the sanitizer already controls the MATCH side).
- New pure function `SnippetHighlighter.attributed(_ raw: String) ->
  AttributedString`: text between sentinel pairs gets
  `highlight` background + `highlightInk` foreground; sentinels are
  stripped; unbalanced markers degrade to plain text (never crash, never
  leak sentinels to screen).
- `SearchView` renders `Text(attributedSnippet)` instead of the plain
  string.
- PR A seeds `Palette.xcassets` with only `highlight`/`highlightInk` and
  the `Palette` enum; the full table lands in PR B (priority note: value
  first, no dead tokens).

### 2 — Palette + locked search/results layout + reader token pass

Results (locked layout):
- Keep `List` (plain style) — the UI tests query `app.cells` and rows merge
  into one accessibility element; a `LazyVStack` rewrite would silently
  change the accessibility tree. Cards are achieved with
  `.listRowBackground(Color.clear)`, hidden separators, and a card
  background per row: `surface`, radius 16, padding 14×16, inner gap 5,
  shadow `0 1 2` at 7% ink.
- Row anatomy: mono caption citation line (`§ n · parent`) in `secondary`;
  `.headline` title in `ink`; snippet `.subheadline` in `body` with
  highlight runs (PR A).
- Group headers replace `Section(title)`: 8×8 rounded (r3) hue-marker dot +
  `SECTION LABEL` style text `DOCTITLE · count` in `secondary`.
- Canvas: `.scrollContentBackground(.hidden)` + `canvas` background.
- Scope picker **stays a stock segmented control** (the handoff says
  exactly that) in its existing safe-area inset; chrome around it picks up
  canvas/hairline. Accent is applied app-wide via `.tint(Palette.accent)`.
- Search field stays `.searchable` (identifier-stable); it inherits accent
  tint. The mock's custom field chrome is approximated only as far as stock
  `.searchable` allows — no custom text-field reimplementation in this
  phase (autofocus interactions are #22's territory).

Reader (tokens/typography only):
- Breadcrumb `.caption.monospaced()` `secondary`; title `.largeTitle.bold()`
  `ink`; `§` number rendered in `accent` monospaced within the title line;
  body `.body` in `body` color, `lineSpacing` per ramp, paragraphs split on
  newlines with paragraph spacing (typography, not structure).
- "See also" label in section-label style; xref buttons tinted accent with
  ≥44pt hit targets; version footer `.caption.monospaced()` `secondary`
  above-hairline per metrics. No diagram, no toggle, no new identifiers.

### 3 — Browse document cards

Card per document (locked browse layout minus Recent): 34×34 radius-10 hue
marker, `.headline` title in `ink`, caption `N sections · vX` with the
version in monospaced; chevron in `secondary` at 50% opacity; `DOCUMENTS`
section label in section-label style. Card chrome identical to result
cards. Section counts come from a new
`RulesRepository.sectionCounts() -> [String: Int]` (single GROUP BY query;
unit-tested against the real DB).

### 4 — Peripheral screens + launch

- **AboutView / DocumentOutlineView / ErrorView + empty states:** the
  handoff explicitly says these layouts "do not exist yet — the tokens
  cover them". So: token + type-ramp pass over the existing layouts
  (canvas background, card surfaces, section-label headers, mono
  versions), no structural redesign. `ContentUnavailableView` states get
  tinted imagery and body-color copy.
- **Launch screen:** solid `canvas` (via `UILaunchScreen` /
  `UIColorName` in project.yml-managed Info.plist config) so launch →
  search feels continuous in both temperatures. If the generated-plist
  route fights xcodegen, fall back to shipping the generated launch as-is
  and note it — not worth destabilizing the build for.

## Constraints carried through every PR

- All 19 existing tests stay green (`just app-test`); existing
  accessibility identifiers/labels (`About`, search field, scope segment
  labels) are load-bearing and unchanged. New UI gets identifiers + tests.
- Contrast: token pairs were picked to clear WCAG AA per the handoff;
  anything derived here (accentPressed-dark, onAccent-light) must be
  checked at review against its actual background before merge.
- Dynamic Type: text styles only; the one layout to check at XL is the
  scope row (stock segmented truncates gracefully per handoff).
- Zero network, no new dependencies, system fonts only, no character
  references in any asset.
- The Xcode project is generated: `app/project.yml` + `just app-gen` only.

## PR sequence (squash-merged, in order)

| PR | Branch | Content |
|---|---|---|
| A | `feat/snippet-highlighting` | Sentinel markers, `SnippetHighlighter` (TDD), highlight token pair, `Palette` enum seed, results rendering; spec+plan docs ride along |
| B | `feat/solar-lunar-palette` | Full token table, type ramp, locked results layout, search chrome, reader token pass |
| C | `feat/browse-document-cards` | Browse cards, hue markers, `sectionCounts()` |
| D | `feat/peripheral-polish` | About/outline/error/empty token pass, launch screen; files the icon follow-up issue; closes #29 |

B–D stack on their predecessor until it merges; each PR notes its base.
