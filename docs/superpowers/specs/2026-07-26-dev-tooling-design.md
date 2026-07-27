# Dev Tooling & Source Download (Plan 1.1) — Design Spec

**Date:** 2026-07-26
**Status:** Approved by Pete (brainstorming session)
**Scope:** Side quest between the content pipeline (merged, PR #10) and Plan 2
(iOS app): a source-download admin command plus the dev-script framework for
all local admin commands.

## What this is

Two things, one PR:

1. A `download` command that fetches the three official source PDFs from the
   URLs already recorded in `sources.yaml`, with sha256 bookkeeping that
   detects when TPCi silently revises a document.
2. The repo's command surface for local admin/dev work: a root `justfile`
   running Python through uv — the pattern Swift commands join in Plan 2.

## Decisions locked in

| Decision | Choice |
|---|---|
| Task runner | `just` (installed via `uv tool install rust-just` — uv is the single bootstrap tool, no brew formula needed) |
| Python env | Full uv adoption: `uv sync`, committed `uv.lock`, no manual venv activation anywhere; pip/venv instructions deleted |
| Download logic | Pipeline CLI subcommand (`python -m benchside_pipeline download`), NOT a standalone script or shell recipe — tested like everything else, manifest stays the single source of truth |
| Upstream revisions | `sha256` recorded per document in `sources.yaml`; download compares and warns loudly on drift |
| Network policy | Only `download` touches the network; `all` stays offline-deterministic and does not grow a download step; tests use `file://` URLs, never live network |

## Design

### `download` command

- `sources.yaml` document entries gain one optional field: `sha256` (hex
  digest of the PDF as ingested). `manifest.py` loads it, and gains a
  validation pass that warns on unknown keys (so a typoed `sha256:` cannot
  be silently dropped — the slice of issue #9 this work touches).
- New module `pipeline/src/benchside_pipeline/download.py`:
  `download_doc(source: SourceDoc, dest_dir: Path) -> DownloadResult`.
  Fetches `source.url` via stdlib `urllib.request` (no new runtime deps)
  with a plain descriptive User-Agent, writes atomically (temp file in
  `dest_dir` + `os.replace`), computes sha256 while writing.
- `DownloadResult` carries `status` ∈ `ok | changed | new` plus the digest:
  - `ok` — digest matches recorded `sha256`; quiet one-line confirmation.
  - `changed` — digest differs from recorded: loud stderr warning naming the
    document ("TPCi revised this document — re-ingest and cut an app
    release"); CLI exits 1.
  - `new` — no recorded `sha256`: file kept, digest printed as a ready-to-
    paste manifest line; exits 0.
- CLI: `download` joins `parse|build|verify|all` in `__main__.py`, using the
  same `--root` convention. `all` is unchanged.
- PDFs land in `sources/` and remain git-ignored; only `sources.yaml` hash
  lines are committed.

### justfile + uv framework

- Root `justfile`, recipes: `setup` (runs `uv sync` in `pipeline/`; prints
  the one-time `uv tool install rust-just` bootstrap hint), `download`,
  `parse`, `build`, `verify`, `all`, `test` — each a thin
  `uv run --project pipeline python -m benchside_pipeline <cmd> --root .`
  (or equivalent) wrapper. uv auto-syncs on `uv run`, so there is no
  activation step and no stale-env failure mode.
- A commented block reserves Plan 2's surface (`app-build`, `app-test`) so
  the Swift work lands in the same place.
- `pipeline/pyproject.toml` unchanged in spirit; `uv.lock` committed;
  `.venv/` stays git-ignored.

### Sync (same PR, per CLAUDE.md)

- README "Running the pipeline" rewritten around the new bootstrap:
  `brew install uv && uv tool install rust-just && just setup && just all`
  → ends `verify OK`.
- CLAUDE.md dev-loop wording updated (no more "venv active"; commands go
  through `just`).
- CI `pipeline` job switches to `astral-sh/setup-uv` + `uv sync --locked`
  (locked = CI fails on lockfile drift). CI does not run `download`; wiring
  the weekly drift cron to it is future work, deliberately out of scope.

## Error handling

- Network failure / non-200 / truncated download: the temp-file write means
  no partial file ever lands at the real path; error names the document and
  URL; CLI exits nonzero having attempted all documents (report every
  failure, not just the first).
- Unknown manifest keys: warning to stderr (not fatal — forward compatible).
- `just` recipes inherit exit codes; no swallowing.

## Testing

- `download_doc` unit tests against `file://` fixture URLs: ok / changed /
  new paths, atomic-write behavior (no file left on simulated failure),
  digest correctness against a known fixture.
- Manifest tests extended for `sha256` round-trip and unknown-key warning.
- CLI test for `download` exit codes (changed → 1) using `file://` sources.
- Existing 31 tests stay green; `uv run pytest` is the invocation.
- Manual gate: `just download` against the live URLs once, paste the three
  real hashes into `sources.yaml`, confirm second run says `ok` ×3.

## Out of scope

- Wiring CI's weekly drift cron to `download` (follow-up).
- Any Swift/app recipes beyond the reserved comment block (Plan 2).
- Auto-updating `sources.yaml` hashes in place (paste-the-line is enough;
  revisions are rare and deserve human eyes).
- The rest of issue #9's hygiene items.
