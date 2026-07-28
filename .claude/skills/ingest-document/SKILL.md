---
name: ingest-document
description: Use when adding a new source PDF or re-ingesting a revised one - covers manifest registration, heading-rule tuning, and structure-stability verification
---

# Ingesting a Source Document

Get a source PDF into `content/` as a correctly-structured section tree.

**Announce at start:** "Using ingest-document for <document>."

This is an *exploratory* loop, not a scripted one: real PDFs have layouts
nobody predicted. The loop is **register → dump → tune → verify**, and it
runs entirely in the manifest. Code changes are a last resort.

## Step 1: Acquire the PDF

`just download` fetches everything registered in `sources/sources.yaml` and
compares sha256 against the recorded value:

- `ok` — matches; nothing changed upstream.
- `new` — no hash recorded; the digest is printed for pasting into the
  manifest.
- `changed` — **the publisher revised the document.** Re-ingest and treat
  every dependent rewrite entry as suspect.

If the publisher's site blocks automated fetches (bot protection), download
the PDF manually in a browser into `sources/`. Never work around bot
protection; the recorded hashes authenticate a manual download just as
well.

## Step 2: Register in the manifest

Every field is required except the tuning ones:

```yaml
- id: <doc-id>
  prefix: <short-prefix>        # section ids become <prefix>-<number>
  title: "<exact cover title>"
  version: "<version or revision date printed on the document>"
  published: "<YYYY-MM-DD>"
  url: "<origin url>"
  file: "<file>.pdf"
  sha256: "<digest>"            # from `just download`
  heading_rules:                # rule index i => heading level i+1
    - '^(\d+)\.\s+(.+)$'        # group 1 = number, group 2 = title
  strip_lines: []               # optional: regexes for page furniture
  layout: false                 # optional: layout-aware extraction
```

## Step 3: See what the extractor sees

Never tune blind. Dump the raw lines first:

```bash
cd pipeline && uv run python -c "
from rulecheck_pipeline.parse import extract_lines
for l in extract_lines('../sources/<file>.pdf')[:120]: print(repr(l))
"
```

Then tune, in this order of preference:

1. **`heading_rules`** — one regex per heading level. Watch for false
   positives: table-of-contents dot leaders (`(?!.*\.{2,})`), four-digit
   years matching a number rule (constrain the digit range), and table
   fragments (require a letter, forbid a lowercase start).
2. **`strip_lines`** — page headers/footers polluting bodies. Validate by
   counting matches against the page count; a footer regex should match
   about once per page.
3. **`layout: true`** — last resort for multi-column pages. It preserves
   column geometry, which can rescue interleaved prose, but it changes line
   shapes and can break heading rules. Only keep it if the structure gate
   below still passes.

## Step 4: Parse and inspect

```bash
just parse
```

Read the resulting `content/<doc-id>.json`: does the section count match
the document's own table of contents? Do titles match? Are bodies
non-empty? Fix by tuning the manifest and re-parsing — **never by editing
`content/` by hand.** That file is machine-generated; a hand edit is
silently destroyed by the next parse.

## Step 5: Structure gate

```bash
just check-ingest
```

Deterministic: re-parses from the PDF and diffs against committed content.
Section ids and count must be identical — that is what proves the parse is
reproducible and that no hand edit has crept in.

Then `just all` must end `verify OK`.

## Known traps

- **Duplicate heading numbers**: "Summary of Changes" tables repeat earlier
  section numbers. The parser treats the repeat as body text and warns for
  each one — read the warnings, confirm each is genuinely a changelog row
  and not a real section being swallowed.
- **Wrapped titles**: a title ending in a comma continues on the next line;
  the parser joins one continuation automatically.
- **Rotated diagram labels**: mirrored words (`SDRAC`, `EZIRP`) are art, not
  content. They survive into bodies and must be ignored downstream, never
  authored from.
- **Sections with no prose**: diagram-label-only sections should be
  skiplisted rather than authored — see the `decompose-section` skill.

## After ingest

Ingestion produces the verbatim reference layer only. Nothing from
`content/` ships. Every section with body text then needs a rewrite entry
or a skip — see `decompose-section`.
