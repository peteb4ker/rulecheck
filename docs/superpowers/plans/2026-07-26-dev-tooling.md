# Dev Tooling & Source Download (Plan 1.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested `download` command (manifest-driven, sha256 drift detection) and put the repo's dev-command framework in place: a root justfile running Python through uv.

**Architecture:** `download` joins the existing `parse|build|verify|all` CLI as pipeline stage zero, reusing the manifest as single source of truth (new optional `sha256` per document). The justfile is a thin recipe layer over `uv run`; uv fully replaces pip/venv (committed `uv.lock`, `uv sync`, no activation). README, CLAUDE.md, and CI switch in the same PR.

**Tech Stack:** Python 3.12+ (stdlib `urllib.request`, `hashlib` — zero new runtime deps), uv, just (installed via `uv tool install rust-just`), GitHub Actions `astral-sh/setup-uv`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-26-dev-tooling-design.md`
- Only `download` touches the network; `all` stays offline-deterministic and does NOT grow a download step.
- Tests never touch the live network — fixture files via `file://` URIs.
- PDFs stay git-ignored; only `sources.yaml` hash lines (and regenerated `content/*.json`) are committed.
- Commits: Conventional Commits, body says why, trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Run Python commands from `pipeline/`; after Task 4 the canonical invocations are `just …` from the repo root (recipes `cd pipeline` internally).
- Existing suite (31 tests) stays green throughout.

---

### Task 1: `sha256` manifest field + unknown-key warning

**Files:**
- Modify: `pipeline/src/benchside_pipeline/model.py` (SourceDoc, line ~19)
- Modify: `pipeline/src/benchside_pipeline/manifest.py`
- Test: `pipeline/tests/test_manifest.py`

**Interfaces:**
- Consumes: existing `SourceDoc` (has `strip_lines: list[str]` defaulted field) and `load_manifest` with `REQUIRED`/`OPTIONAL` tuples.
- Produces: `SourceDoc.sha256: str | None = None`; `OPTIONAL = ("strip_lines", "sha256")`; unknown manifest keys emit a stderr warning naming the document and keys (not fatal).

- [ ] **Step 1: Write the failing tests**

Append to `pipeline/tests/test_manifest.py` (it already defines `VALID` and `write`):

```python
def test_sha256_optional_field(tmp_path):
    with_hash = VALID.replace(
        '    file: "fixture.pdf"\n',
        '    file: "fixture.pdf"\n    sha256: "abc123"\n',
    )
    assert load_manifest(write(tmp_path, with_hash))[0].sha256 == "abc123"
    assert load_manifest(write(tmp_path, VALID))[0].sha256 is None


def test_unknown_key_warns(tmp_path, capsys):
    typoed = VALID.replace(
        '    file: "fixture.pdf"\n',
        '    file: "fixture.pdf"\n    sha265: "typo"\n',
    )
    docs = load_manifest(write(tmp_path, typoed))
    assert docs[0].sha256 is None
    err = capsys.readouterr().err
    assert "sha265" in err and "fixture-doc" in err
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `pipeline/`, venv active): `pytest tests/test_manifest.py -v`
Expected: `test_sha256_optional_field` FAILS (`SourceDoc` has no `sha256`); `test_unknown_key_warns` FAILS (no warning emitted).

- [ ] **Step 3: Implement**

In `pipeline/src/benchside_pipeline/model.py`, add to `SourceDoc` after `strip_lines`:

```python
    sha256: str | None = None
```

In `pipeline/src/benchside_pipeline/manifest.py`: add `import sys` to the imports, then:

```python
OPTIONAL = ("strip_lines", "sha256")
KNOWN = set(REQUIRED) | set(OPTIONAL)
```

and inside the entry loop, after the `missing` check:

```python
        unknown = sorted(set(entry) - KNOWN)
        if unknown:
            print(
                f"warning: {entry['id']}: unknown manifest keys ignored: {', '.join(unknown)}",
                file=sys.stderr,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_manifest.py -v` then `pytest -q`
Expected: manifest tests pass; full suite 33 passed (31 + 2).

- [ ] **Step 5: Commit**

```bash
git add src/benchside_pipeline/model.py src/benchside_pipeline/manifest.py tests/test_manifest.py
git commit -m "feat(pipeline): sha256 manifest field + unknown-key warning"
```

---

### Task 2: `download_doc`

**Files:**
- Create: `pipeline/src/benchside_pipeline/download.py`
- Test: `pipeline/tests/test_download.py`

**Interfaces:**
- Consumes: `SourceDoc` (with `sha256` from Task 1).
- Produces: `DownloadResult` dataclass `(doc_id: str, status: str, sha256: str, path: Path)` with `status` ∈ `"ok" | "changed" | "new"`; `download_doc(source: SourceDoc, dest_dir: Path) -> DownloadResult` — atomic write, raises `OSError` (incl. `urllib.error.URLError`) on fetch failure leaving no file behind.

- [ ] **Step 1: Write the failing tests**

`pipeline/tests/test_download.py`:

```python
import dataclasses
import hashlib

import pytest

from benchside_pipeline.download import download_doc
from benchside_pipeline.model import SourceDoc


def make_source(tmp_path, content: bytes, sha256=None):
    origin = tmp_path / "origin.pdf"
    origin.write_bytes(content)
    return SourceDoc(
        id="fixture-doc", prefix="fix", title="Fixture", version="1.0",
        published="2026-01-01", url=origin.as_uri(), file="fixture.pdf",
        heading_rules=[r"^(\d+)\.\s+(.+)$"], sha256=sha256,
    )


@pytest.fixture
def dest(tmp_path):
    d = tmp_path / "sources"
    d.mkdir()
    return d


def test_new_download(tmp_path, dest):
    result = download_doc(make_source(tmp_path, b"pdf bytes"), dest)
    assert result.status == "new"
    assert result.sha256 == hashlib.sha256(b"pdf bytes").hexdigest()
    assert result.path == dest / "fixture.pdf"
    assert result.path.read_bytes() == b"pdf bytes"


def test_ok_when_hash_matches(tmp_path, dest):
    digest = hashlib.sha256(b"pdf bytes").hexdigest()
    assert download_doc(make_source(tmp_path, b"pdf bytes", digest), dest).status == "ok"


def test_changed_when_hash_differs(tmp_path, dest):
    result = download_doc(make_source(tmp_path, b"pdf bytes", "0" * 64), dest)
    assert result.status == "changed"
    assert result.path.exists()  # file still saved for inspection


def test_failed_download_leaves_no_file(tmp_path, dest):
    source = make_source(tmp_path, b"x")
    source = dataclasses.replace(source, url=(tmp_path / "missing.pdf").as_uri())
    with pytest.raises(OSError):
        download_doc(source, dest)
    assert list(dest.iterdir()) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_download.py -v`
Expected: FAIL with `ModuleNotFoundError: benchside_pipeline.download`.

- [ ] **Step 3: Implement**

`pipeline/src/benchside_pipeline/download.py`:

```python
from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from benchside_pipeline.model import SourceDoc

USER_AGENT = "benchside-pipeline/0.1 (offline rules reference builder)"
CHUNK = 65536


@dataclass
class DownloadResult:
    doc_id: str
    status: str  # "ok" | "changed" | "new"
    sha256: str
    path: Path


def download_doc(source: SourceDoc, dest_dir: Path) -> DownloadResult:
    dest_dir = Path(dest_dir)
    dest = dest_dir / source.file
    request = urllib.request.Request(source.url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    fd, tmp_name = tempfile.mkstemp(dir=dest_dir, prefix=f".{source.file}.")
    try:
        with os.fdopen(fd, "wb") as tmp, urllib.request.urlopen(request) as resp:
            while chunk := resp.read(CHUNK):
                digest.update(chunk)
                tmp.write(chunk)
        os.replace(tmp_name, dest)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise
    hex_digest = digest.hexdigest()
    if source.sha256 is None:
        status = "new"
    elif hex_digest == source.sha256:
        status = "ok"
    else:
        status = "changed"
    return DownloadResult(doc_id=source.id, status=status, sha256=hex_digest, path=dest)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_download.py -v` then `pytest -q`
Expected: 4 passed; full suite 37 passed.

- [ ] **Step 5: Commit**

```bash
git add src/benchside_pipeline/download.py tests/test_download.py
git commit -m "feat(pipeline): atomic manifest-driven document download with sha256"
```

---

### Task 3: CLI `download` subcommand

**Files:**
- Modify: `pipeline/src/benchside_pipeline/__main__.py`
- Test: `pipeline/tests/test_cli.py`

**Interfaces:**
- Consumes: `download_doc`/`DownloadResult` (Task 2), `load_manifest`, existing `main(argv)` and `make_repo` test helper.
- Produces: `python -m benchside_pipeline download [--root PATH]` — exit 0 when every document is `ok`/`new`, exit 1 if any is `changed` or any fetch failed; attempts ALL documents before exiting (reports every failure, not just the first). `all` is unchanged.

- [ ] **Step 1: Write the failing test**

Append to `pipeline/tests/test_cli.py` (reuses its `make_repo`; adjust the two `.replace()` needles to the literal strings in `make_repo`'s manifest if they differ):

```python
def test_download_new_then_changed(tmp_path, fixture_pdf):
    root = make_repo(tmp_path, fixture_pdf)
    origin = tmp_path / "origin.pdf"
    origin.write_bytes(b"official pdf bytes")
    yaml_path = root / "sources" / "sources.yaml"
    yaml_path.write_text(yaml_path.read_text().replace(
        'url: "https://example.com/fixture.pdf"', f'url: "{origin.as_uri()}"'))

    assert main(["download", "--root", str(root)]) == 0  # no recorded hash -> "new"
    assert (root / "sources" / "fixture.pdf").read_bytes() == b"official pdf bytes"

    yaml_path.write_text(yaml_path.read_text().replace(
        'file: "fixture.pdf"', 'file: "fixture.pdf"\n    sha256: "' + "0" * 64 + '"'))
    assert main(["download", "--root", str(root)]) == 1  # hash mismatch -> "changed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: new test FAILS (argparse rejects `download`); existing 2 CLI tests still pass.

- [ ] **Step 3: Implement**

In `pipeline/src/benchside_pipeline/__main__.py`: add `from benchside_pipeline.download import download_doc` to imports; add `"download"` to the argparse `choices` list; dispatch `if args.command == "download": return cmd_download(root)` alongside the existing dispatches (`all` chain unchanged); add:

```python
def cmd_download(root: Path) -> int:
    dest = root / "sources"
    changed = failures = 0
    for source in load_manifest(root / "sources" / "sources.yaml"):
        try:
            result = download_doc(source, dest)
        except OSError as exc:
            print(f"ERROR: {source.id}: download failed from {source.url}: {exc}",
                  file=sys.stderr)
            failures += 1
            continue
        if result.status == "ok":
            print(f"{source.id}: ok ({result.sha256[:12]}…)")
        elif result.status == "new":
            print(f"{source.id}: downloaded; no recorded hash. Add to sources.yaml:")
            print(f'    sha256: "{result.sha256}"')
        else:
            changed += 1
            print(
                f"WARNING: {source.id}: upstream document changed "
                f"(recorded {source.sha256}, fetched {result.sha256}).\n"
                f"  TPCi revised this document — re-ingest and cut an app release.",
                file=sys.stderr,
            )
    return 1 if (changed or failures) else 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v` then `pytest -q`
Expected: 3 CLI tests pass; full suite 38 passed.

- [ ] **Step 5: Commit**

```bash
git add src/benchside_pipeline/__main__.py tests/test_cli.py
git commit -m "feat(pipeline): download CLI subcommand with drift exit code"
```

---

### Task 4: justfile + full uv adoption + doc/CI sync

**Files:**
- Create: `justfile` (repo root)
- Create: `pipeline/uv.lock` (generated by `uv sync`, committed)
- Modify: `README.md` ("Running the pipeline" section)
- Modify: `CLAUDE.md` (Layout block + Quality gates pipeline line)
- Modify: `.github/workflows/ci.yml` (pipeline job steps, lines ~120-134)

**Interfaces:**
- Consumes: the complete CLI (Tasks 1-3).
- Produces: recipes `setup`, `download`, `parse`, `build`, `verify`, `all`, `test`; bootstrap contract `brew install uv && uv tool install rust-just && just setup && just all` → ends `verify OK`.

- [ ] **Step 1: Create the justfile**

`justfile` (repo root):

```just
# Benchside dev commands.
# Bootstrap: brew install uv && uv tool install rust-just && just setup

default:
    @just --list

# One-time / after dependency changes: sync pipeline env (uv manages .venv)
setup:
    cd pipeline && uv sync --all-extras

# Fetch official source PDFs (network!); exits 1 if TPCi revised a document
download:
    cd pipeline && uv run python -m benchside_pipeline download --root ..

parse:
    cd pipeline && uv run python -m benchside_pipeline parse --root ..

build:
    cd pipeline && uv run python -m benchside_pipeline build --root ..

verify:
    cd pipeline && uv run python -m benchside_pipeline verify --root ..

# parse → build → verify (offline; must end "verify OK")
all:
    cd pipeline && uv run python -m benchside_pipeline all --root ..

test:
    cd pipeline && uv run pytest

# --- Plan 2 (iOS app) recipes land here: app-build, app-test ---
```

- [ ] **Step 2: Generate the lockfile and verify recipes work**

```bash
just setup      # creates pipeline/uv.lock + syncs pipeline/.venv
just test       # expected: 38 passed
just all        # expected: ends "verify OK"
```

(If `just` is not installed: `uv tool install rust-just` first.)

- [ ] **Step 3: Rewrite README's "Running the pipeline" section**

Replace the whole section (from `## Running the pipeline` up to `## Layout`) with:

```markdown
## Running the pipeline

One-time bootstrap:

```bash
brew install uv
uv tool install rust-just
just setup
```

Day to day:

```bash
just all        # parse → build → verify (offline; ends "verify OK")
just test       # pytest suite
just download   # fetch official PDFs (network; exits 1 if TPCi revised a doc)
```

`just` with no arguments lists every recipe. PDFs land in `sources/`
(never committed; `sources.yaml` records each document's origin URL and
sha256). Parsed JSON goes to `content/` (committed, reviewable); the app
database to `build/benchside.db` (git-ignored). Re-run `just all` after
any `sources.yaml` edit or document revision.
```

- [ ] **Step 4: Sync CLAUDE.md**

In the Layout block add a line for the justfile, and change the pipeline quality-gate line. The two edits:

```markdown
justfile           # dev commands: just setup / all / test / download …
```

(added at the top of the Layout code block), and in Quality gates replace

```markdown
- **Pipeline** (`pipeline/`, Python): `pytest` green, always. Logic changes
```

with

```markdown
- **Pipeline** (`pipeline/`, Python, via uv — `just test`): `pytest` green,
  always. Logic changes
```

- [ ] **Step 5: Switch CI's pipeline job to uv**

In `.github/workflows/ci.yml`, replace the pipeline job's setup-python + Install steps (keeping `working-directory: pipeline` defaults and the job structure):

```yaml
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          cache-dependency-glob: pipeline/uv.lock
      - name: Install (locked)
        run: uv sync --locked --all-extras
      - name: Unit tests (fixture-based, no real PDFs)
        run: uv run pytest -v
      - name: Build and verify committed content
        if: needs.detect.outputs.has-content == 'true'
        run: |
          uv run python -m benchside_pipeline build --root ..
          uv run python -m benchside_pipeline verify --root ..
```

- [ ] **Step 6: Verify locally, commit**

```bash
just test && just all
git add justfile pipeline/uv.lock README.md CLAUDE.md .github/workflows/ci.yml
git commit -m "feat(tooling): justfile + full uv adoption; CI and docs switch with it"
```

(CI itself is verified on the PR — the pipeline job must go green with the uv steps.)

---

### Task 5: Record the real document hashes

**Files:**
- Modify: `sources/sources.yaml` (three `sha256:` lines)
- Modify: `content/*.json` (regenerated — document blocks gain `"sha256"`)

**Interfaces:**
- Consumes: `just download`, `just all`.
- Produces: a manifest where all three documents have recorded hashes; committed content regenerated so `content/*.json` stays byte-identical with what the pipeline now produces.

- [ ] **Step 1: Live download, record hashes**

```bash
just download
```

Expected: three `downloaded; no recorded hash` blocks, each printing a ready-to-paste `sha256:` line; exit 0. Paste each line into the matching document entry in `sources/sources.yaml` (same indentation as its `file:` line).

If any document instead reports `WARNING: … upstream document changed` — TPCi revised it since the July ingest. STOP and surface to the controller: that means re-ingest (heading-rule retune possible) before hashes can be recorded, which exceeds this task.

- [ ] **Step 2: Confirm ok ×3 and regenerate content**

```bash
just download   # expected: three "ok (…)" lines, exit 0
just all        # expected: verify OK; content/*.json regenerated with sha256 in each document block
just test       # expected: 38 passed
git diff --stat # expected: sources.yaml + 3 content JSONs only
```

- [ ] **Step 3: Commit**

```bash
git add sources/sources.yaml content/
git commit -m "feat(content): record source document sha256 hashes"
```

---

> **Reality note (2026-07-26, Task 5):** pokemon.com's WAF (Incapsula)
> serves bot-challenge HTML to repeated automated fetches. During execution
> this clobbered the local PDFs (fetched HTML replaced them before any
> content check) — fixed by a `%PDF-` magic-byte guard in `download_doc`
> that raises before anything reaches the destination. The three sha256
> values were recorded from the verified July-ingest PDFs before the WAF
> engaged. Step 2's content regeneration (embedding `sha256` into
> `content/*.json`) is deferred until real PDFs are locally present again
> — via WAF cooldown or a manual browser download into `sources/`; the
> recorded hashes authenticate either path.

## Definition of Done

- Fresh clone: `brew install uv && uv tool install rust-just && just setup && just download && just all` ends `verify OK` with no manual venv step anywhere (PDFs are git-ignored, so `download` must precede the first `all`).
- `just download` twice in a row: first run may print paste-lines (if hashes missing), second run prints `ok` ×3, exit 0.
- Full suite 39 passed via `just test` (38 + the WAF magic-byte guard test); CI pipeline job green on uv.
- README/CLAUDE.md mention pip/venv nowhere; `uv.lock` committed.
