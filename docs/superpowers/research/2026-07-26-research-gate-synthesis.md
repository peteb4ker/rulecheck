# Research Gate — Synthesis & Recommendations

> **Superseded 2026-07-28:** the app was renamed **Benchwise -> Rule Check** (Xcode project `Benchside` -> `RuleCheck`). This document is kept as the record of what was decided at the time; the names below are historical.

**Date:** 2026-07-26 · **Issue:** #16 · **Status:** DECIDED (Pete, 2026-07-26)

**Decisions:**
1. **Content: Hybrid.** Faithful paraphrase is the default for all shipped
   text; short verbatim quotes are permitted only where exact wording is
   load-bearing for judges (e.g., penalty definitions), under fair-use
   excerpt logic. Parsed verbatim JSON remains an internal accuracy
   reference only. Scoping lands as Plan 1.2.
2. **Repo: private until paraphrase.** Revisit going public after Plan 1.2
   replaces shipped verbatim content (history handling included).
3. **Name: Benchwise.** Formal USPTO TESS/EUIPO pass before App Store
   submission. Repo/codename rename is optional housekeeping, Pete's call.
**Method:** four parallel research streams plus a follow-up naming stream; full
notes with citations live beside this file:
[copyright](2026-07-26-copyright.md) ·
[terms of use](2026-07-26-terms-of-use.md) ·
[precedents & App Store](2026-07-26-precedents-app-store.md) ·
[name check](2026-07-26-name-benchside.md) ·
[name candidates](2026-07-26-name-candidates.md)

> Research notes, not legal advice. If any decision here becomes
> load-bearing for real money or real risk, have a lawyer read the notes.

## The three questions this gate exists to answer

### 1. Verbatim rules text — ship it or rewrite it?

**Recommendation: rewrite. Ship faithful paraphrase; drop verbatim from the
shipped app.** All three legal-ish streams converge:

- **Copyright:** rules/mechanics are uncopyrightable (17 USC §102(b),
  *Baker v. Selden*, *Morrissey*, *Allen*, *Affiliated Hospital Products*,
  *DaVinci Editrice*) — but the protection that *does* exist covers exactly
  the thing verbatim shipping copies: TPCi's prose. Wholesale verbatim
  copying is the fact pattern that loses (*Tetris Holding*); faithful
  paraphrase is the fact pattern that has won on the merits (*Affiliated
  Hospital Products*). Fair use is a shaky fit for whole-document
  reproduction with only search/navigation added.
- **Terms of Use:** pokemon.com's ToU §5 grants "personal, noncommercial
  home use only" and prohibits "download[ing] quantities of content to a
  database" and derivative works — on-point for both the pipeline and the
  app. It is pure browsewrap (weak under *Nguyen v. Barnes & Noble*), and
  notably the two Play! handbooks carry **no in-document copyright notice
  at all** (only the rulebook does) — but browsewrap weakness is a defense,
  not a permission.
- **Precedents:** verbatim rules apps thrive in MTG — but WotC freely
  publishes its rules as unrestricted downloads and tolerates the practice.
  TPCi has no analogous policy, historically ran its own rules app (Card
  Dex, sunset), and enforces hard when triggered (though never once, in
  anything found, against rules text — 22 years of the community rulings
  compendium untouched). No precedent combines Pokemon + app + verbatim.

**What this means concretely:** the pipeline gains a rewrite stage —
authoring faithful paraphrase per section, with the parsed verbatim JSON as
the internal reference for accuracy (local processing for personal use is
the defensible end of the ToU spectrum; publishing is what changes the
analysis). Structure, IDs, breadcrumbs, search, and the app design are all
unaffected. Scope and plan for this land as "Plan 1.2" once approved.

### 2. Can the repo go public?

**Not while `content/*.json` contains verbatim TPCi text.** Public repo =
redistribution, the weakest position in every stream. Options in order of
recommendation: (a) go public only after the shipped content is paraphrase
and verbatim JSON is removed from history or quarantined; (b) split repos
(public code, private content); (c) stay private indefinitely. No urgency —
revisit when Plan 1.2 completes.

### 3. The name

**"Benchside" is dead for the App Store** — a live iOS app with the exact
name exists (Reforce Labs, Sports, since 2023;
apps.apple.com id6445801735). The repo/codename can remain until a rename
is convenient; the public name cannot.

Pre-screened replacement shortlist (full evidence in
[name candidates](2026-07-26-name-candidates.md)):

1. **Rulebench** — clean on App Store, web, Justia trademarks, TCG
   community.
2. **Judgecall** — clean everywhere; judgecall.com parked/for-sale.
3. **Deckside** — clean for software; one unrelated apparel-class mark.
4. **Benchwise** — no store/trademark hit, but active unrelated companies
   use it.

Dropped for collisions: Prof Desk (education LMS), Tablejudge (feature name
inside "Judges Toolkit for Pokemon"). Whatever is chosen gets a formal
USPTO TESS pass before App Store submission (Justia-only screening here).

## Posture notes (apply regardless of decisions)

- Naming pattern that survives review: generic/descriptive name, optionally
  "for Pokemon TCG" as *descriptor* (live precedent: "Judges Toolkit for
  Pokemon", id1170164207 — also the closest thing to a competitor found:
  judging utilities, not a rules reference; Benchside's search-first rules
  lookup remains differentiated).
- Standard disclaimer, converged industry text: "not affiliated with,
  endorsed, sponsored, or specifically approved by The Pokemon Company
  International, Nintendo, Creatures, or GAME FREAK." Already in README.
- No character names/art anywhere; Reference/Utilities category; zero
  network calls (already non-negotiable) removes the scraping enforcement
  vector entirely.
- TPCi enforcement is reactive (per former CLO's public statements), so
  posture at launch matters more than legal theory: free, unofficial,
  character-free, paraphrased = nothing to react to.

## Gaps (tracked, non-blocking)

- Full Play! Pokemon Terms of Use text unreachable (bot-blocked); only
  snippets reviewed. Governs tournament participation, not content
  licensing, per what was recoverable.
- Press/media Assets Use Terms login-gated (401); relevance unconfirmed.
- Formal USPTO TESS + EUIPO pass deferred until a finalist name is chosen.
