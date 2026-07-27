# Solar/Lunar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Solar/Lunar visual spec (issue #29, phase 1) across four squash-merged PRs, per `docs/superpowers/specs/2026-07-27-solar-lunar-implementation-design.md`.

**Architecture:** Asset-catalog Color Sets (Any = Solar, Dark = Lunar) behind a `Palette` enum; FTS5 sentinel markers parsed into `AttributedString` for snippet highlighting; locked search/results layout on the existing `List` (accessibility tree preserved); token/type passes on reader, browse, and peripheral screens.

**Tech Stack:** SwiftUI (iOS 17), GRDB (existing), xcodegen via `just app-gen`, XCTest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-27-solar-lunar-implementation-design.md`; the design package tokens/metrics are authoritative.
- `app/` and `app/project.yml` only. Never hand-edit the `.xcodeproj`; run `just app-gen` after adding files.
- All 19 existing tests stay green; identifiers `About`, search field, scope segment labels unchanged. `just app-test-unit` is the fast loop; full `just app-test` before every PR.
- No diagram views, no Diagram/Exact-wording toggle, no Recent list, no `negative` token, no new dependencies, zero network, system fonts only, no character references.
- Conventional Commits with `Co-Authored-By: Claude` trailer; every PR body refs #29 (PR D closes it).

---

### Task A1: Snippet highlighter (TDD) + highlight tokens

**Files:**
- Create: `app/Benchside/Design/Palette.swift`
- Create: `app/Benchside/Design/Palette.xcassets/Contents.json` + `highlight.colorset/Contents.json` + `highlightInk.colorset/Contents.json`
- Create: `app/Benchside/Design/SnippetHighlighter.swift`
- Test: `app/BenchsideTests/SnippetHighlighterTests.swift`

**Interfaces:**
- Produces: `enum Palette` (`static let highlight: Color`, `static let highlightInk: Color` — full table added in PR B); `enum SnippetHighlighter` with `static let start: Character = "\u{E000}"`, `static let end: Character = "\u{E001}"`, `static func attributed(_ raw: String) -> AttributedString`.

- [ ] **Step 1: Write the failing tests** — `SnippetHighlighterTests.swift`: plain text passes through unchanged with no background runs; `"a \u{E000}hit\u{E001} b"` yields exactly one background run whose characters are `hit` and whose sentinels are stripped; two pairs yield two runs; an unclosed `\u{E000}` degrades to plain text; a stray `\u{E001}` is dropped. Assert text via `String(a.characters)` and runs via `a.runs.filter { $0.backgroundColor != nil }`.
- [ ] **Step 2: Run to verify failure** — `just app-test-unit`; expected: compile failure (`SnippetHighlighter` unresolved).
- [ ] **Step 3: Implement** — colorsets: highlight `#FAE6B6`/dark `#5B4718`, highlightInk `#6E3F10`/dark `#FAEEBD` (srgb, universal idiom + dark appearance). `Palette` exposes them. `SnippetHighlighter.attributed` single-pass: start marker (outside a match) flushes plain and opens; end marker (inside) closes the run with `backgroundColor = Palette.highlight`, `foregroundColor = Palette.highlightInk`; stray markers are dropped; unclosed match text is appended plain.
- [ ] **Step 4: `just app-gen`, verify `Palette.xcassets` landed in the Resources build phase** (`grep -c Palette.xcassets app/Benchside.xcodeproj/project.pbxproj` ≥ 2), then `just app-test-unit` green.
- [ ] **Step 5: Commit** — `feat(app): snippet highlighter with Solar/Lunar highlight tokens`

### Task A2: Repository emits match markers; results render them

**Files:**
- Modify: `app/Benchside/Data/RulesRepository.swift` (snippet SQL)
- Modify: `app/Benchside/Search/SearchView.swift` (snippet Text)
- Test: `app/BenchsideTests/RulesRepositoryTests.swift` (one new test)

**Interfaces:**
- Consumes: `SnippetHighlighter` (A1). Produces: `SearchHit.snippet` now carries `\u{E000}`/`\u{E001}` around FTS matches.

- [ ] **Step 1: Failing test** — `testSearchSnippetsCarryMatchMarkers`: search `"asleep"` (all scopes) must return ≥1 snippet containing `\u{E000}`, with balanced start/end counts.
- [ ] **Step 2: Verify failure** — markers absent today (empty-string markers in the SQL).
- [ ] **Step 3: Implement** — snippet call becomes `snippet(sections_fts, 1, char(57344), char(57345), '…', 14)`; `SearchView` renders `Text(SnippetHighlighter.attributed(hit.snippet))`.
- [ ] **Step 4:** `just app-test-unit` green, then full `just app-test` (19 + new = all green; UI flows unchanged).
- [ ] **Step 5: Commit + PR** — branch `feat/snippet-highlighting`, docs (spec + this plan) committed here; PR "feat: snippet match highlighting in search results", base `main`, refs #29.

---

### Task B1: Full palette + type helpers

**Files:**
- Modify: `app/Benchside/Design/Palette.swift`; add colorsets: canvas, surface, sunken, selected, hairline, ink, body, secondary, accent, accentPressed, onAccent, docGame, docTournament, docPenalty (hex per spec table)
- Create: `app/Benchside/Design/TypeRamp.swift` — `extension View`: `sectionLabelStyle()` (`.caption2.monospaced()`, kerning 1.2, uppercase, `Palette.secondary`), `citationStyle()` (`.caption.monospaced()`); `extension DocumentInfo { var hue: Color }` mapping doc ids → docGame/docTournament/docPenalty, fallback accent
- Test: `app/BenchsideTests/PaletteTests.swift` — every token resolves to a non-default color in the catalog; hue mapping covers the three ids + fallback

- [ ] TDD loop as A1; commit `feat(app): full Solar/Lunar token table behind Palette`.

### Task B2: Locked results layout + search chrome

**Files:**
- Modify: `app/Benchside/Search/SearchView.swift`

Keep `List` + `NavigationLink` (cells are load-bearing for UI tests). Apply: `.scrollContentBackground(.hidden)`, `Palette.canvas` background, `.tint(Palette.accent)` at root; rows get clear list background, hidden separators, card chrome (`surface`, radius 16, padding 14×16, gap 5, shadow 0/1/2 @ 7% ink); row anatomy citation-line (`§ n · parent`, citationStyle, secondary) / title (`.headline`, ink) / snippet (`.subheadline`, body color, lineSpacing 3, highlight runs); group headers = 8×8 r3 hue dot + `DOCTITLE · N` sectionLabelStyle. Scope picker stays the stock segmented control in its inset with canvas/hairline chrome.

- [ ] Full `just app-test` green (identifiers untouched); XL Dynamic Type spot-check in simulator (scope row truncates, never wraps); commit `feat(app): Solar/Lunar search and results chrome`.

### Task B3: Reader token/typography pass

**Files:**
- Modify: `app/Benchside/Reader/SectionView.swift`

Breadcrumb citationStyle/secondary; title `.largeTitle.bold()` ink with `§ number` in accent monospaced; body `.body`, `Palette.body`, lineSpacing 3, paragraphs split on `\n` with 12pt spacing (typography only); See-also as section label + accent-tinted ≥44pt buttons; version footer citationStyle above a hairline. No new identifiers, no diagram/toggle.

- [ ] Full `just app-test` green; commit `feat(app): reader Solar/Lunar token and typography pass`; PR `feat/solar-lunar-palette` stacked on A, refs #29.

---

### Task C1: Browse document cards

**Files:**
- Modify: `app/Benchside/Data/RulesRepository.swift` — add `sectionCounts() -> [String: Int]` (single `GROUP BY doc_id` query)
- Modify: `app/Benchside/Search/SearchView.swift` — browse section: `DOCUMENTS` sectionLabel header; per-doc card (34×34 r10 hue marker, `.headline` title, `N sections · vX` caption with mono version, chevron secondary @ 50%)
- Test: `app/BenchsideTests/RulesRepositoryTests.swift` — counts match `sections(inDocument:).count` for all three docs, tournament-rules = 119

- [ ] TDD loop; no Recent list (v1 scope); full `just app-test` green; PR `feat/browse-document-cards` stacked on B, refs #29.

---

### Task D1: Peripheral screens + launch + close-out

**Files:**
- Modify: `app/Benchside/AboutView.swift`, `app/Benchside/Reader/DocumentOutlineView.swift`, `app/Benchside/ErrorView.swift` — token/type pass only (canvas, surface cards, sectionLabel headers, mono versions, tinted `ContentUnavailableView`)
- Modify: `app/project.yml` — launch screen `UIColorName: canvas` via target `info` properties if compatible with `GENERATE_INFOPLIST_FILE`; otherwise ship generated launch unchanged and record the decision in the PR body
- File follow-up issue: app icon (vector pass, character-free directions from handoff)

- [ ] Full `just app-test` green; dark+light screenshots of every screen at default and XL Dynamic Type attached to the PR; PR `feat/peripheral-polish` stacked on C, **closes #29**.
