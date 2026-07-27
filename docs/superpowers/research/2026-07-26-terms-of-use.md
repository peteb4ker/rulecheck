# Research notes: pokemon.com / TPCi Terms of Use as applied to Benchside's source PDFs

**Disclaimer:** These are research notes prepared by an AI research assistant, not legal advice. Confirm anything load-bearing with a licensed attorney before shipping.

**Scope:** Benchside's `sources/sources.yaml` currently ingests three PDFs, all hosted at `www.pokemon.com/static-assets/...`:
1. *Pokémon Trading Card Game Rules* ("Web Rulebook, Last Updated: July 2026") — `pbl_rulebook_en.pdf`
2. *Play! Pokémon Tournament Rules Handbook* (Last Revision: May 21, 2026) — `play-pokemon-tournament-rules-handbook-en.pdf`
3. *Play! Pokémon Penalty Guidelines* (Last Revision: May 21, 2026) — `play-pokemon-penalty-guidelines-en.pdf`

All three PDFs already exist locally in `sources/` (downloaded by the pipeline previously; git-ignored per repo convention), so this research read the PDFs directly rather than re-downloading them.

---

## 1. pokemon.com Terms of Use — verbatim clauses (https://www.pokemon.com/us/legal/terms-of-use)

Live fetches of this page intermittently hit a bot-detection interstitial; the extracts below come from the fetch attempts that succeeded (Claude's web-fetch tool renders the page and returns cleaned text, so "verbatim" here means as extracted by that tool, not a byte-for-byte HTML dump — treat wording as high-confidence but re-verify anything that will be quoted in a legal filing).

### Document structure (16 numbered sections)

1. What Services Do These Terms Cover?
2. This is an Agreement Between You and The Pokémon Company International, Inc.
3. **Intellectual Property, Service Content, and User Submissions**
4. Copyright Infringement Claims
5. **User Rights and Restrictions**
6. Conduct and Community Standards
7. Player Trainer Central Accounts
8. Contests; Sweepstakes
9. Play! Pokémon Program
10. Third-Party Products and Services
11. Virtual Content
12. Purchasing Virtual Content
13. Updates and Changes to the Service
14. Disclaimer
15. Indemnification
16. General Provisions

### (a) Acceptance-of-terms mechanism (Section 2)

> "By accessing, downloading, or using the Service, you acknowledge that you have read, understood and agreed to these Terms and any code of conduct that we may put forth from time to time."

This is pure **browsewrap**: no checkbox, no "I Agree" click-through, no account creation gate for the general site or for downloading a PDF linked from a public page. Contrast with pokemon.com's own e-commerce properties — Pokémon Center's ToU uses clickwrap language ("By clicking 'I Agree'... or by accessing or using the Services, you acknowledge...") which at least offers an explicit-assent path even if not always required. The main pokemon.com/legal ToU offers no such path for a person who just downloads a PDF from a public URL and never visits `/legal/terms-of-use` at all.

### (b) Section 3 — Intellectual Property, Service Content, and User Submissions

> "Unless otherwise noted, all content on the Service, including articles, artwork, screen shots, graphics, logos, downloads and other files, is the property of Pokémon and is protected by United States and international copyrights, trademarks and other intellectual property laws."

Users are told they have "no property or other rights in any content on the Service."

### (c) Section 5 — User Rights and Restrictions (the operative permission + prohibition clause)

Grant of permission:

> "...in your individual capacity, to use the content of Service made available to you for personal, noncommercial home use only."

Prohibited uses (numbered list, paraphrased numbering preserved from source, wording verbatim per the successful extraction):

- (i) "Change or remove any copyright and other proprietary notices from content on the Service"
- (ii) "Modify, or create derivative works based on, the content"
- (iii) "Use, or facilitate the use of, any unauthorized third-party software (e.g. bots, mods, hacks, and scripts) to modify or automate operation within the Service whether for yourself or for a third party" — **this is the automated-access / scraping clause; there is no separate "robots/spiders/crawlers" section.** It is framed around modifying/automating *operation of the Service* (i.e., game clients, account systems), not generically about fetching public pages with a script — a distinction that matters if the pipeline is characterized as "automated access."
- (iv) Using content in any manner that: suggests association with other products/brands, causes customer confusion, disparages Pokémon, is commercially exploitative, or infringes IP rights
- (v) "Download quantities of content to a database for any reason" — **this is the most directly on-point clause for Benchside's pipeline**, which parses PDFs into `content/*.json` and then a SQLite database (`build/benchside.db`). Read literally, downloading rulebook content into a database is exactly what this bullet prohibits, regardless of commercial intent.
- (vi) "Decompose, disassemble, or reverse engineer any part of any Service"
- (vii) Developing "functionally similar" products or services
- (viii) Using the Service for third-party benefit or transferring access
- (ix) Use "for commercial purposes, including...selling access to all or part of the Service" or placing advertising
- (x) Avoiding/circumventing/disabling security or DRM protocols
- (xi) Infiltrating systems operating the Service
- (xii) Exploiting known or latent bugs/malfunctions
- (xiii) Circumventing age, geography, or other access restrictions

Termination (also Section 5):

> "Notwithstanding anything to the contrary included in these Terms, we may at any time, with or without notice, suspend or terminate your access to some or all of the Service and refuse any and all current or future use of the Service at any time."

### (d) Section 16 — General Provisions (governing law / dispute mechanics)

> "These Terms are governed by and construed in accordance with the laws of the State of Washington, excluding its conflict of laws provisions, as applied to agreements executed by Washington residents and performed solely within the State of Washington, and you submit to personal jurisdiction in Washington."

> "THE PARTIES HEREBY WAIVE TRIAL BY JURY."

(A one-year claims-limitation period was also flagged in the section summary but not captured verbatim; re-fetch before citing exact wording.)

---

## 2. Copyright page (https://www.pokemon.com/us/legal/copyright)

> "You should assume that everything you see or read on http://www.pokemon.com is copyrighted -- unless otherwise noted"

> Materials "may not be used except as stated in the Pokémon Terms of Use or with the written permission of The Pokémon Company International."

DMCA takedown mechanics: complaints go to TPCi's General Counsel (10400 NE 4th Street, Suite 2800, Bellevue, WA) or legalnotices@pokemon.com, with the standard §512(c)(3) elements (signature, ID of copyrighted work, ID/location of infringing material, contact info, good-faith statement, perjury statement).

> Pokémon "neither warrants nor represents that your use of materials displayed on the Service will not infringe rights of third parties."

This page adds no independent obligations beyond pointing back to the ToU; it functions as a copyright notice + DMCA contact page, not a separate license.

---

## 3. Play! Pokémon Terms of Use (separate document, distinct from the general site ToU)

URL: `https://www.pokemon.com/us/legal/play-pokemon-terms-of-use`. Live fetch was blocked by the same bot-detection interstitial on every attempt; only search-snippet content was recoverable:

- The Play! Pokémon program is offered by The Pokémon Company International Inc.
- Before participating, "you (or your parent or legal guardian if you're under the age of majority) must review and agree to" this Agreement.
- "The Agreement applies to all who participate in the Program, including players, competitors, and Professors."

This document governs *participation in tournaments* (conduct, eligibility, prize rules) — it is the agreement a player/Professor accepts to play in an event, not a license covering redistribution of the Tournament Rules Handbook or Penalty Guidelines PDFs. I could not get the full text; if this matters for the app's fine print, it should be re-fetched directly (try a real browser session — the automated fetcher was consistently walled off) rather than relied on via search snippets. **Flag: incomplete — recommend a follow-up pass with a headed browser if this document's exact wording becomes load-bearing.**

The Tournament Rules Handbook itself (page 4, §1.1 "Supporting Materials") cross-references this document:

> [Verbatim quotation removed before this repository was made public. The passage is the opening "read in conjunction with" clause of the Tournament Rules Handbook §1.1, listing the Standards of Conduct, Terms of Use, Inclusion Policy and Accessibility Policy as companion documents.]

— again framing it as a program-participation agreement, not a content license.

---

## 4. Press / media asset terms (https://press.pokemon.com/en/Assets-Use-Terms)

Fetch returned **HTTP 401 Unauthorized** — this is TPCi's press site, gated behind a login for accredited media, and not accessible to a general researcher/downloader. Unable to confirm terms. Given the 401, it's reasonable to infer this license (whatever it says) is scoped to press/media assets (logos, screenshots, character art) for journalists, not to rules documents, and likely requires a registered press account — i.e., it doesn't create an alternate public license path for the rulebook PDFs. Not verified directly; flagging as unresolved rather than asserting.

---

## 5. Copyright/usage notices INSIDE the three source PDFs

Extracted directly from the local PDF files with `pypdf` (full-text scan of every page for "copyright", "all rights reserved", "©", "trademark", "terms of use", "permission").

### `tcg-rules.pdf` (Pokémon TCG Rules, Web Rulebook)
Page 44 (last page), in the glossary/credits footer:

> "©2026 Pokémon. ©1995–2026 Nintendo / Creatures Inc. / GAME FREAK inc. TM, ®, and character names are trademarks of Nintendo."

This is the **only** copyright/trademark notice found in this document. It's a standard character/trademark notice (protecting Pokémon names/characters, consistent with CLAUDE.md's note that "Character names are TPCi trademarks; rules facts are not"), not a document-specific reproduction license or restriction clause. No "all rights reserved," no explicit prohibition on copying text, no reference back to the site ToU.

### `tournament-rules.pdf` (Play! Pokémon Tournament Rules Handbook)
**No copyright notice, ©, "all rights reserved," or license text anywhere in the document** — confirmed by full-text scan of all 49 pages and by PDF metadata (Producer/Creator fields only, no rights fields). The only "permission" hits in the document are unrelated to content reproduction:
- §1.1 cross-reference to the separate Play! Pokémon Terms of Use (see §3 above)
- §2.2/2.3 (page 10): a photo/video release clause covering attendees at events (name, image and likeness), quotation removed before publication — this is about event photography of *attendees*, not document text
- A staff-permission clause on page 12 (procedural, about tournament floor rulings) and a tournament-format clause on page 32 (about using non-standard formats "only with express written permission") — both unrelated to redistributing the document itself

### `penalty-guidelines.pdf` (Play! Pokémon Penalty Guidelines)
**No copyright notice, ©, "all rights reserved," license text, or "permission" language anywhere in the document** — confirmed by full-text scan of all 37 pages and metadata check.

**Bottom line for §5:** Only one of the three source documents carries any in-document rights notice, and it's a trademark notice on character names/branding, not a text-reproduction restriction. Neither the Tournament Rules Handbook nor the Penalty Guidelines PDF says anything about copying, reproducing, or redistributing itself. Whatever restrictions apply to these two documents come entirely from the *website* ToU governing the page they were downloaded from — not from the documents themselves.

---

## 6. Enforceability context: browsewrap vs. clickwrap against a non-account-holding downloader

*Not exhaustive case law research — high-level orientation only.*

- **Nguyen v. Barnes & Noble, Inc.**, 763 F.3d 1171 (9th Cir. 2014): B&N's website ToU was presented only via a hyperlink in the footer, with no prompt requiring the user to view or assent to it before completing a purchase. The Ninth Circuit held this **pure browsewrap agreement unenforceable** — a conspicuous hyperlink alone, without more (no click-to-accept, no forced notice), doesn't give rise to constructive assent, especially against a party who never actually visited the terms page.
- **Specht v. Netscape Communications Corp.**, 306 F.3d 17 (2d Cir. 2002): download page invited users to get free software with license terms visible only if the user scrolled down past the download button; court held users who didn't see the terms weren't bound — reasonable notice is the touchstone, not mere availability of a link.
- **Register.com v. Verio, Inc.**, 356 F.3d 393 (2d Cir. 2004): contrasting case where a sophisticated repeat commercial user (making automated queries against a WHOIS database with knowledge of posted terms) was held bound — enforceability tracks actual or constructive notice plus a pattern of use that puts the user on notice, which matters more for a company scraping repeatedly than an individual downloading a PDF once.
- General doctrinal throughline: courts scrutinize (1) how conspicuous the terms/link were, (2) whether any affirmative act (checkbox, click) manifested assent, and (3) the sophistication/repeat-use pattern of the accused party. Pure browsewrap terms reachable only via a small footer link, with no click-through and no forced interstitial, are the weakest form of contract and are frequently found unenforceable against a first-time, non-account-holding visitor — which is the posture of Benchside's pipeline (an anonymous one-time or periodic fetch of a public PDF URL, no account, no click-to-accept).
- Caveat: enforceability of the *contract* (breach-of-ToU claim) is analytically separate from **copyright infringement** exposure. Even if the ToU itself is not a binding contract against Benchside, the underlying documents are still copyrighted works, and using large verbatim excerpts inside a distributed app raises ordinary copyright (not contract) questions — fair use, amount/substantiality of the taking, effect on the market for TPCi's own materials, etc. The ToU's Section 3/5 language doesn't change the underlying copyright analysis; it's a separate, additional restriction TPCi is trying to layer on via contract, and it only binds if the contract itself is enforceable.

---

## 7. Bottom line

### (a) Downloading the PDFs for local processing (pipeline ingest)

- The ToU's Section 5(v) — "Download quantities of content to a database for any reason" — is written broadly enough to literally cover exactly what the pipeline does (fetch PDF → parse → load into `content/*.json` and `benchside.db`). Taken at face value, this clause prohibits it outright, independent of any downstream redistribution.
- However, as a pure browsewrap term (Section 2's acceptance language: "by accessing, downloading, or using the Service, you acknowledge...") reached only via a footer link on a page the pipeline never visits, its contractual enforceability against an anonymous automated fetch is weak under *Nguyen*-line reasoning — there's a real argument no contract was ever formed with the downloader. That's a defense to a *breach-of-contract* theory, not to copyright.
- Practical weight: **legally uncertain/contestable, not "clearly permitted."** The clause is squarely on point and TPCi could plausibly assert it; the main counter is browsewrap-formation weakness, which is a real but not bulletproof defense (TPCi could also point to *actual* notice via repeated pipeline runs, similar to *Register.com*'s "sophisticated repeat user" reasoning if the fetch is automated and recurring rather than one-off).

### (b) Redistributing the text inside a free app

- Section 5's grant is expressly "personal, noncommercial home use only" — redistributing parsed rules text inside a shipped app, even a free one, falls outside that grant on its face (it's not "your individual" use; it's republishing to other users).
- Section 5(ii) ("Modify, or create derivative works based on, the content") and 5(ix) ("commercial purposes... selling access") are secondary hooks — (ix) likely doesn't bite since Benchside is free/non-commercial per CLAUDE.md, but (ii) plausibly does if the pipeline's parsing/restructuring (splitting into headings, JSON records, DB rows) counts as a "derivative work" of the rulebook text — an open interpretive question, not resolved by the ToU's plain text.
- None of the three PDFs carry their own copyright/reproduction notice (see §5) — the TCG rulebook's only in-document notice is a trademark line about character names, and the other two documents have no rights language at all. So the restriction, if it exists, comes entirely from the website ToU's browsewrap terms, not from anything printed on the documents themselves.
- Practical weight: **the ToU's plain language weighs against redistribution**, but its legal force again depends on browsewrap enforceability against a party with no account and no click-through. Separately and more importantly, **copyright itself doesn't require a ToU to be infringed** — TPCi owns copyright in the documents' expression regardless of contract enforceability, so redistribution of verbatim (or substantially similar) text is a copyright question first, a ToU-breach question second. CLAUDE.md's existing "Research Gate" on verbatim rules text appears to already track this correctly — the ToU analysis here reinforces rather than substitutes for that gate; it's an additional (contractual) risk layered on top of the (more fundamental) copyright risk, not a lesser or greater one.

### Overall

Nothing found here should be read as "TPCi has clearly authorized this." The ToU explicitly withholds the exact rights the app wants (bulk download into a database; redistribution beyond personal use), and none of the three PDFs contain a friendlier, document-specific license that would override the site-wide ToU. The main mitigating factor is browsewrap enforceability weakness (Nguyen), which blunts but doesn't eliminate the ToU's force, and does nothing for the separate, more fundamental copyright question. This supports keeping verbatim text gated behind the Research Gate as CLAUDE.md already specifies, and treating this ToU review as one more data point for that gate rather than a green light.

---

## Gaps / follow-ups if this becomes load-bearing

1. Play! Pokémon Terms of Use (`/us/legal/play-pokemon-terms-of-use`) full text was never successfully fetched (bot-detection interstitial on every attempt) — only search-snippet fragments recovered. Re-attempt with a real browser session.
2. Press/media Assets Use Terms (`press.pokemon.com/en/Assets-Use-Terms`) returned HTTP 401 — inaccessible without a press-site login; scope/relevance unconfirmed.
3. The general ToU's exact wording for Section 3(iv)'s sub-list and the one-year limitations clause in Section 16 came through a rendering/extraction tool rather than a raw HTML diff — treat as high-confidence paraphrase-adjacent, not a certified verbatim copy; re-pull before quoting in anything formal.
4. No search was done for TPCi's separate Fan Content Policy (if one exists distinct from Play! Pokémon materials) — worth a dedicated pass given CLAUDE.md's "no Pokemon character/species names user-facing" constraint already anticipates trademark sensitivity.
