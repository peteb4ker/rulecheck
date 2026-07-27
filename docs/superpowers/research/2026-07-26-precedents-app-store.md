# Research: Unofficial TCG Rules Apps — Precedent & Apple Policy

Compiled 2026-07-26 for Benchside (unofficial, offline Pokemon TCG rules reference app).

---

## 1. Live precedents — Pokemon TCG specifically

**No dedicated "Pokemon TCG rules/rulings reference" iOS app was found.** Everything findable in the Pokemon TCG iOS ecosystem is collection tracking / card scanning / deck building, not rules text delivery:

| App | Store | What it ships | Disclaimer | Notes |
|---|---|---|---|---|
| **TrainerBOX** (dev: Gabriel Axel Estevez Reyes) | iOS, id6752110435 | Collection manager, deck builder, card search, sample-hand tester, tournament record tracking, card-prize consult tool. No rules text. | "TrainerBOX is an unofficial, fan-made utility for managing trading card game (TCG) collections and decks. It is not affiliated with, endorsed, sponsored, or specifically approved by The Pokémon Company, Nintendo, or Creatures Inc." | Launched ~Nov 2025, v1.1.0 as of Jul 2026. 4.8★ (6 ratings) — too new/small to be a real signal either way. Has IAP up to $699 (aggressive monetization, unrelated risk factor). |
| **Pokedata: Scan and Track TCG** | iOS id6504906730 | Card scan/value tracking | "not affiliated with, sponsored or endorsed by... The Pokemon Company International" | Card scanner, not rules |
| **TCG - Card Scanner for Pokémon** | iOS id6743366115 | Card scanner | "not affiliated with, endorsed by, or sponsored by The Pokémon Company, Nintendo" | Card scanner, not rules |
| **TCG Live for Pokemon (TCGP)** | iOS id6670340801 | Live-game companion | "not affiliated, endorsed, or supported by Nintendo or The Pokémon Company International" | Companion tool |
| **TCG Card Game Scanner: Kardex** | iOS id6752235140 | Card scanner | "not affiliated with, sponsored, or endorsed by The Pokémon Company International, Nintendo, Creatures Inc., or GAME FREAK Inc." | Card scanner |
| **Yugipedia Deck Builder** (Yu-Gi-Oh, adjacent TCG) | iOS id1026470546 | Deck builder, card DB | "not affiliated with, sponsored, endorsed, or approved by Studio Dice, Shueisha, TV Tokyo, or Konami" | Confirms the disclaimer pattern generalizes across TCG IP owners |

**The actual rules-reference precedent for Pokemon TCG is not an app — it's a website: the Pokémon (TCG) Rulings Compendium**, at `compendium.pokegym.net`.

- **History**: Founded ~February 2000 by "Team Compendium," a group of League/TO/Judge community members. Moved to compendium.pokegym.net on **March 23, 2004**. (Source: pojo.com feature article and the PokeGym community announcement thread — both pages 403'd on direct fetch but corroborated via search snippets; the pokegym.net forum thread title is "Pokemon TCG Compendium Announcement.")
- **Content**: Compiles official rulings on card interactions, organized by set/era ("Compendium VMAX" is the current all-sets edition; older "Compendium EX" etc. exist as archived versions). This is **rulings/interpretations**, arguably a mix of paraphrase and close reproduction of official ruling language — not the verbatim rulebook itself, though it draws directly on official Pokemon USA/PUI-issued rulings.
- **Official tolerance, not endorsement**: A widely-cited quote attributed to Pokemon USA/PUI in response to a question about endorsing the Compendium: **"You can say that Pokémon USA thinks you're a great resource. Endorse? Sure."** This is informal tolerance/blessing, not a license agreement — no policy document memorializes it.
- **Longevity**: Still online at least 22+ years after founding (2000–2026), still indexed and apparently still active (site nav shows "Rulings," "Resources for Judges," "Resources for Players" sections as of this search — direct fetch blocked by 403 on the crawler, so current maintenance cadence couldn't be independently confirmed today; searches show it surfacing in 2026-current results).
- **Takedown history found: NONE.** No search turned up any TPCi/Nintendo/PUI cease-and-desist, DMCA, or legal action against compendium.pokegym.net in its 22+ year history. This is the strongest single precedent for Benchside: a text-based, non-visual, no-card-art rules/rulings resource has operated in the open for over two decades without enforcement action, and with an informal nod of tolerance from the rights holder.
- **Caveat**: A website is not an app; it isn't distributed through Apple's review gate, doesn't claim offline/bundled distribution of content, and (per available evidence) doesn't reproduce the verbatim rulebook — it reproduces *rulings interpretations*. Benchside's plan to ship verbatim rules text inside a bundled offline database is a meaningfully different posture and is exactly what the project's own "Research Gate" (per CLAUDE.md) is meant to catch.

Other Pokemon rules-adjacent web resources found (not apps, for context only): PTCG Resource (sites.google.com/view/pokemonresource), a fan-run Google Sites rules/rulings page; torsive.com's "Pokemon TCG Quick Reference Rules Guide" blog post. Neither reports enforcement history; both are low-visibility fan sites, not app-store-distributed software.

---

## 2. Live precedents — adjacent TCGs (Magic: The Gathering is the richest vein)

Multiple MTG rules/judge apps are live on iOS **today**, several of which ship the full Comprehensive Rules (CR), Magic Tournament Rules (MTR), and Infraction Procedure Guide (IPG) verbatim, offline:

| App | Developer | Content shipped | Disclaimer | Signal |
|---|---|---|---|---|
| **MTG Guide** (id378754271) | Michael Wybrow | Full card text/rulings for all sets, **Comprehensive Rules**, **MTR**, **IPG**, format legality, TCGplayer pricing, draft timer, deck-check tools | "This app is not produced or endorsed by Wizards of the Coast, Inc." | **Long-lived and thriving**: 4.7★ from 719 ratings, actively updated (v4.1 May 2025, v4.0 Apr 2025 with a "Liquid Glass" redesign — i.e., still being maintained for the newest iOS design language). This is the single strongest adjacent-TCG precedent: verbatim CR/MTR/IPG, monetized (freemium $0.99/mo or $6.99/yr), years of continuous operation, no reported takedown. |
| **Bugko** | Keng Siang Ooi | Offline Comprehensive Rules (searchable), IPG, MTR, multi-language card text, life counter, collection tracking, draft timer | "Magic: The Gathering... card design, text, images, expansions, and symbols are trademark and copyright of Wizards of the Coast, Hasbro, LLC. Bugko is not affiliated with, endorsed, sponsored, or specifically approved by Wizards of the Coast LLC." | Free, 515.8MB (i.e., a real bundled offline database, comparable in spirit to Benchside's approach), category "Reference." Low ratings volume but live. |
| **French Vanilla Magic Rules** (id6758114292) | Andrew Benson | Full CR index + terms glossary, "auto-updater" for rules text without app updates | No explicit disclaimer text found in the fetched listing (may appear only in-app) | New app (initial release "Feb 18," v1.4.0 by "Jul 12" — 2026 timeframe), narrowly scoped: rules only, no card data. Closest analog to Benchside's scope. |
| **MagicJudge** (id6738770397) | Ambicon ApS | AI-generated rules explanations "trained on the official MTG ruleset," rule search, card tagging | No explicit Fan Content Policy citation found in listing | Different approach (AI-generated answers vs. verbatim text) — riskier IP posture, not directly comparable. |
| **MTG Judge – Judge Orbit** (Google Play; com.judgeorbit.app) | — | CR, IPG, MTR, JAR (Judge Academy Rules?) documents, updated "over the air," banned/restricted lists per format, draft timer, decklist counter, judge-training flashcards | Not confirmed in snippet | Android-only per search; "documents... update over the air" — same content-refresh pattern Benchside's pipeline uses. |
| **MTG Judge Core** | — | Referenced/discussed on **apps.magicjudges.org** (the official-adjacent Magic Judges community forum) — a thread exists asking for an iOS port of the Android app | — | Notable: this app is *discussed favorably on the judge community's own forum infrastructure*, suggesting community/tacit acceptance, though the forum itself states organizations like "Judge Foundry" and "International Judges Program" are explicitly "not endorsed by WOTC" — i.e., WotC does distinguish official-program endorsement from community tool tolerance. No evidence WotC has taken down MTG Judge Core. |

**Does WotC's Fan Content Policy actually cover these apps?** This is the key nuance: **not cleanly.** Full policy text (company.wizards.com/en/legal/fancontentpolicy):

- Fan Content must be free (no selling/licensing for compensation), though ad revenue/donations are allowed.
- Required disclaimer format: *"[Title] is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC."*
- **Critical exclusion**: *"Fan Content does not include the verbatim copying and reposting of Wizards' IP (e.g., freely distributing D&D® rules content or books)."* — i.e., the Policy's own text says verbatim rules reproduction is explicitly **outside** what it permits.
- None of the surveyed apps (MTG Guide, Bugko, French Vanilla Magic Rules) use WotC's mandated Fan Content disclaimer wording — they use generic "not affiliated/endorsed" language instead. This suggests the app developers are **not relying on the Fan Content Policy as their legal basis** for shipping CR/MTR/IPG verbatim; they're relying on the fact that WotC (a) publishes the CR/MTR/IPG itself for free on its own site, and (b) has shown no enforcement appetite against reference tools that redistribute already-free, non-monetized-as-a-product rules text. Some of these apps (MTG Guide) *do* charge a subscription, and still appear undisturbed — suggesting WotC's tolerance line is about "are you selling MTG the game / competing with WotC's own product," not "did you charge $1/month for a nicer rules browser."
- **No takedown of any of these MTG rules apps was found in this research.** That is a meaningful negative result given years of operation (MTG Guide has existed long enough to go through multiple major iOS redesign cycles) and real monetization.

**Yu-Gi-Oh**: Only deck-builder precedent found (Yugipedia Deck Builder, standard "not affiliated with... Konami" disclaimer). No dedicated Yu-Gi-Oh rules-reference app was located in this pass; Konami does run an official "Rules Resource for Yu-Gi-Oh!" style content and a Judge Program, but third-party app precedent here is thin — treat as no-data, not as a negative signal.

---

## 3. TPCi / Nintendo enforcement history — pattern analysis

Enforcement actions found, categorized:

**A. Character-IP / gameplay-IP enforcement (frequent, aggressive):**
- **Pokemon GO location trackers** (2016): PokeVision, PokeAlert, Pokemap, Poke Hound — all hit with cease-and-desist letters from Niantic/Nintendo/TPCi and shut down within weeks of the game's launch. Stated rationale: unauthorized scraping of game server data + facilitating "cheating," not primarily a copyright/trademark claim about character art.
- **Fan games / ROM hacks** (ongoing, escalating): Pokemon Uranium (2016, DMCA'd off official hosts, still findable via mirrors), Pokemon Prism, Pokemon Fusion Generation — all removed via DMCA for reproducing full game assets/engine. **Relic Castle** (Mar 2024) — a 10-year-old, 20,000-member forum that only *linked to* third-party fan-game downloads (didn't host them, wasn't monetized) — was still DMCA'd and shut down. This is the most aggressive recent action and shows TPCi/Nintendo will pursue even non-hosting community hubs when the content is a **playable derivative game**.
- Nintendo's broader 2018-2020 ROM-site campaign (Emuparadise, LoveROMs, LoveRoms, etc.) targeted classic-game ROM piracy generally, not TCG content.

**B. Rules-text / rules-reference enforcement: NONE FOUND.**
- No case of TPCi, Nintendo, or Pokemon USA/PUI taking action against a rules-text reference, rulings compendium, or judge-tool site or app was found anywhere in this research.
- compendium.pokegym.net (22+ years, reproduces official ruling interpretations) — untouched, informally blessed.
- The official TCG rulebook and Play! Pokémon Tournament Rules Handbook are themselves **freely published PDFs on pokemon.com** — TPCi's own copyright page states content "may not be used except as stated in the Pokémon Terms of Use or with... written permission," but the rulebook's *purpose* is public dissemination of tournament rules to the entire player base; TPCi has no evident interest in restricting who reads or references that text, only in unauthorized commercial/competing use of characters, art, and playable game content.

**Distinguishing principle observed across both Pokemon and MTG evidence**: enforcement targets (1) unauthorized use of copyrighted **character art/game assets**, (2) **playable derivative games** that substitute for the official product, and (3) unauthorized **data scraping** of live game infrastructure. Enforcement has not touched **text-only rules/rulings reference tools**, even ones that are long-lived, verbatim, and monetized (MTG Guide). This is consistent with, though not proof of, the "rules facts are not protected the way character IP is" framing already in Benchside's CLAUDE.md.

---

## 4. Apple App Review Guideline 5.2 (Intellectual Property) — verbatim-relevant text

From developer.apple.com/app-store/review/guidelines/#intellectual-property:

**5.2.1 Generally**: *"Don't use protected third-party material such as trademarks, copyrighted works, or patented ideas in your app without permission, and don't include misleading, false, or copycat representations, names, or metadata in your app bundle or developer name. Apps should be submitted by the person or legal entity that owns or has licensed the intellectual property and other relevant rights."*

**5.2.2 Third-Party Sites/Services**: *"If your app uses, accesses, monetizes access to, or displays content from a third-party service, ensure that you are specifically permitted to do so under the service's terms of use. Authorization must be provided upon request."*

**5.2.5 Apple Products**: covers Apple-specific IP (Finder look-alikes, Apple emoji, Activity rings, WeatherKit attribution) — not relevant to Benchside directly, but confirms Apple applies the same "don't imply you're the official thing" logic to its own IP, i.e., the review team's mental model generalizes.

**Practically, how live unofficial companion apps satisfy 5.2.1** (observed pattern across every app surveyed above, Pokemon and MTG alike):
1. **Naming**: never use the trademarked character/franchise name as if it were the app's own brand in a way that implies officialness (e.g., avoid "Pokemon Rules" as a bare title; pattern is "[Generic/Original Name]" or "[Descriptive] for [Franchise]" — e.g., "TCG Card Scanner for Pokémon," "MTG Guide," "Bugko"). None of the surveyed apps used a name indistinguishable from an official Pokemon/WotC product.
2. **Icon/screenshots**: none of the fetched listings showed use of official character artwork as the app icon (not independently screenshot-verified in this pass, but scanner apps show generic card-frame UI, not reproduced character art).
3. **Disclaimer boilerplate**, present on every surveyed listing in some form: *"[App] is not affiliated with, endorsed, sponsored, or specifically approved by [Rights Holder(s)]."* This exact template (with rights-holder list swapped) appears near-verbatim across TrainerBOX, Bugko, Yugipedia Deck Builder, and multiple card-scanner apps — it's clearly the industry-standard disclaimer text developers converge on, likely satisfying 5.2.1's "misleading... representations" clause by explicit disclaiming.
4. **Category**: several list under "Reference" or "Utilities," not "Games," reinforcing the "tool about the game, not a version of the game" framing.

No specific rejection/appeal case study for a Pokemon or MTG rules app was found (i.e., no public record of Apple rejecting one of these specific apps and a subsequent appeal). General Apple Developer Forum threads about 5.2.1 rejections show the common failure modes are (a) using the trademark owner's exact name/logo as the app's own identity, (b) no proof of authorization when Apple explicitly asks for it, (c) company/seller name mismatches. None of the surveyed apps display those failure patterns, consistent with why they're live.

---

## 5. Bottom line

**Yes — an unofficial, disclaimer-carrying, character-art-free Pokemon TCG rules reference realistically survives both App Review and stands a good chance of avoiding takedown, based on observed precedent** — with two important caveats:

1. **The precedent is strong but not identical.** The closest exact-match precedent (Pokemon TCG rules content specifically) is a *website* (compendium.pokegym.net, 22+ years, no takedown, informal PUI tolerance) rather than an app, and it ships *rulings interpretations* rather than a bundled verbatim rulebook database. The closest *app-form* precedent (MTG Guide, Bugko — verbatim CR/MTR/IPG, offline, monetized, years-long, no takedown) is a different rights-holder (WotC/Hasbro) under a different (if imperfectly-matching) Fan Content Policy. Benchside sits at the intersection: Pokemon IP + app form + verbatim text — no single precedent covers all three simultaneously, but each dimension individually has a clean, long-running, unmolested analog.

2. **TPCi's enforcement pattern is genuinely different in kind from character/game-asset enforcement**, and every data point found supports treating rules-text reference as low-risk relative to fan games, ROM hacks, or live-data scraping tools — which is exactly what gets hit.

**Posture choices that most reduce risk, derived directly from what live apps already do:**
- **Naming**: Do not use "Pokemon" as if it's part of the app's own brand identity. Use a pattern like "[Original Name] — Rules for Pokémon TCG" or similar descriptive/reference framing, never a name that could be mistaken for an official product. (Matches Benchside's existing "no character names user-facing" rule, but note: "Pokemon TCG" as a *game-name reference*, distinct from *character names*, is what every surveyed disclaimer implicitly treats as fair descriptive use — worth confirming this distinction is intentional in Benchside's naming, since the surveyed apps all say "for Pokémon" in metadata even while avoiding character names.)
- **Disclaimer**: Adopt the converged industry boilerplate verbatim-style: *"[App] is an unofficial, fan-made reference. Not affiliated with, endorsed, sponsored, or specifically approved by The Pokémon Company, Nintendo, or Creatures Inc."* — surface it in both the App Store description and in-app (About screen), matching what every surveyed app does.
- **Screenshots/icon**: No character artwork, no official card images, no logo lookalikes — text/UI only, consistent with Benchside's existing "no character art" rule and reinforcing 5.2.1 compliance.
- **Category**: List under Reference/Utilities, not Games.
- **Zero network calls** (already a Benchside non-negotiable) removes the entire "unauthorized scraping of live game data" enforcement vector that produced TPCi's most aggressive historical actions (Pokevision et al.) — this is arguably Benchside's single strongest risk-reduction feature relative to precedent, since it structurally can't be the kind of app TPCi has actually gone after.
- **Content posture**: The project's own Research Gate (verbatim rules text gated pending research) is the right caution given that even the closest precedent (WotC's own Fan Content Policy) explicitly disclaims covering verbatim rules reproduction — the safety here comes from TPCi's *revealed behavior* (tolerating compendium.pokegym.net, publishing its own free rulebook PDFs) rather than from any written permission. Treat "no one has been taken down for this" as directionally reassuring, not as a substitute for the legal research the gate is designed to produce.

### Sources
- https://compendium.pokegym.net/ (search-snippet corroborated; direct fetch 403)
- https://pojo.com/Features/2004/032504.html (Compendium history, "PUI thinks you're a great resource" quote — via search snippet)
- https://pokegym.net/community/index.php?threads/pokemon-tcg-compendium-announcement.5344/
- https://apps.apple.com/mx/app/trainerbox/id6752110435
- https://apps.apple.com/us/app/pokedata-scan-and-track-tcg/id6504906730
- https://apps.apple.com/us/app/tcg-card-scanner-for-pok%C3%A9mon/id6743366115
- https://apps.apple.com/jp/app/tcg-live-for-pokemon-tcgp/id6670340801
- https://apps.apple.com/mx/app/id6752235140 (Kardex)
- https://apps.apple.com/mx/app/yugipedia-deck-builder/id1026470546
- https://apps.apple.com/us/app/mtg-guide/id378754271
- https://apps.apple.com/af/app/bugko/id1325400403
- https://apps.apple.com/us/app/-/id6758114292 (French Vanilla Magic Rules)
- https://apps.apple.com/us/app/magicjudge/id6738770397
- https://play.google.com/store/apps/details?id=com.judgeorbit.app
- https://apps.magicjudges.org/forum/topic/26086/ ("Judge core app" thread)
- https://company.wizards.com/en/legal/fancontentpolicy
- https://developer.apple.com/app-store/review/guidelines/#intellectual-property
- https://www.pokemon.com/us/legal/copyright
- https://www.pokemon.com/us/pokemon-tcg/rules
- https://www.gamesradar.com/after-almost-10-years-unofficial-pokemon-website-known-for-sharing-fan-made-games-shuts-down-after-reportedly-receiving-a-dmca-takedown-notice/ (Relic Castle, Mar 2024)
- https://www.nintendolife.com/news/2024/03/pokemon-fan-game-site-relic-castle-shut-down-following-dmca-takedown-notice
- https://kotaku.com/pokevision-and-other-pokemon-go-trackers-seem-to-have-b-1784602025
- https://www.mic.com/articles/166809/pokemon-go-update-pokealert-and-pokemap-forced-to-shut-down-by-the-pokemon-company

### Gaps / not independently verified
- compendium.pokegym.net and its /history/ page returned HTTP 403 to the fetch tool; history details rely on search-engine snippets of that page and a secondary pojo.com article, not a direct primary-source read.
- No direct evidence found of Apple *rejecting* a Pokemon or MTG rules/reference app specifically — absence of evidence, not evidence of a guaranteed pass.
- Konami/Yu-Gi-Oh rules-app precedent is thin (no dedicated rules app found); treat that TCG as no-data rather than as either a positive or negative signal.
- Could not independently confirm compendium.pokegym.net's current (2026) maintenance cadence beyond it appearing live in current search results.
