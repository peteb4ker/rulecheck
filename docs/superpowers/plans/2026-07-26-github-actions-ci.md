# GitHub Actions CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the GitHub Actions CI designed in `docs/superpowers/specs/2026-07-26-github-actions-ci-design.md` — green on today's docs-only repo, activating automatically as `pipeline/` and `app/` land.

**Architecture:** One `ci.yml` with a cheap `detect` job whose outputs gate `pipeline` (ubuntu, pytest + content build/verify) and `app` (macOS, xcodebuild) jobs, plus an unconditional `guards` job enforcing repo non-negotiables. A separate `pr-title.yml` enforces Conventional Commits PR titles (repo squash-merges, so titles become `main` commit subjects).

**Tech Stack:** GitHub Actions, bash, actionlint v1.7.7 (pinned download, not a third-party action), `actions/checkout@v4`, `actions/setup-python@v5`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-26-github-actions-ci-design.md` — it wins on any disagreement.
- Only first-party `actions/*` actions, pinned to major versions. No third-party actions.
- Workflow-level `permissions: contents: read` (or `permissions: {}` where nothing is read).
- Every job has `timeout-minutes`.
- The app job must NOT run on PRs that touch neither `app/**`, `content/**`, `pipeline/src/benchside_pipeline/build.py`, nor `.github/workflows/**` (macOS minutes bill at 10× on this private repo).
- Conventional Commits types allowed in PR titles are exactly CLAUDE.md's branch prefixes: `feat fix chore docs ci refactor test`.
- YAML "tests" are actionlint runs plus locally executing each embedded shell snippet; the PR's own CI run is the integration test.
- Never push to `main`; all work lands via PR with a Conventional Commits title and `Closes #2`.

---

### Task 1: `ci.yml` skeleton — triggers, detect, guards

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: workflow `CI` with job `detect` exposing outputs `has-pipeline`, `has-app`, `has-content`, `app-relevant` (strings `'true'`/`'false'`), consumed by Task 2's jobs via `needs.detect.outputs.*`. Job `guards` has no outputs.

- [ ] **Step 1: Install actionlint locally (the test harness for this plan)**

```bash
ACTIONLINT_DIR=$(mktemp -d)
bash <(curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/v1.7.7/scripts/download-actionlint.bash) 1.7.7 "$ACTIONLINT_DIR"
"$ACTIONLINT_DIR/actionlint" --version
```

Expected: prints `1.7.7`. Keep `$ACTIONLINT_DIR` for later steps.

- [ ] **Step 2: Write the workflow**

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: '17 6 * * 1' # weekly drift check (Mon 06:17 UTC)
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  detect:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    outputs:
      has-pipeline: ${{ steps.scan.outputs.has-pipeline }}
      has-app: ${{ steps.scan.outputs.has-app }}
      has-content: ${{ steps.scan.outputs.has-content }}
      app-relevant: ${{ steps.scan.outputs.app-relevant }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 # merge-base against the PR base branch
      - name: Scan repo state and changed paths
        id: scan
        env:
          EVENT_NAME: ${{ github.event_name }}
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
        run: |
          has_pipeline=false
          [ -f pipeline/pyproject.toml ] && has_pipeline=true
          has_app=false
          compgen -G 'app/*.xcodeproj' > /dev/null && has_app=true
          has_content=false
          compgen -G 'content/*.json' > /dev/null && has_content=true

          # push / schedule / dispatch always count as app-relevant so a
          # path-filter gap is caught at merge and weekly, never lingering.
          app_relevant=true
          if [ "$EVENT_NAME" = "pull_request" ]; then
            merge_base=$(git merge-base "$BASE_SHA" HEAD)
            changed=$(git diff --name-only "$merge_base" HEAD)
            printf 'changed files:\n%s\n' "$changed"
            app_relevant=false
            if printf '%s\n' "$changed" | grep -qE '^(app/|content/|pipeline/src/benchside_pipeline/build\.py|\.github/workflows/)'; then
              app_relevant=true
            fi
          fi

          {
            echo "has-pipeline=$has_pipeline"
            echo "has-app=$has_app"
            echo "has-content=$has_content"
            echo "app-relevant=$app_relevant"
          } >> "$GITHUB_OUTPUT"

  guards:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - name: No tracked PDFs
        run: |
          tracked=$(git ls-files -- '*.pdf')
          if [ -n "$tracked" ]; then
            echo '::error::Source PDFs must never be committed (CLAUDE.md non-negotiable). Tracked:'
            printf '%s\n' "$tracked"
            exit 1
          fi
      - name: No tracked build products
        run: |
          tracked=$(git ls-files -- 'build/*' '*.db')
          if [ -n "$tracked" ]; then
            echo '::error::build/ output and .db files are build products, not source. Tracked:'
            printf '%s\n' "$tracked"
            exit 1
          fi
      - name: sources.yaml parses
        run: |
          if [ -f sources/sources.yaml ]; then
            pip install --quiet pyyaml
            python3 -c 'import yaml; yaml.safe_load(open("sources/sources.yaml"))'
            echo 'sources.yaml OK'
          else
            echo 'sources/sources.yaml not present yet; skipping'
          fi
      - name: content JSON parses
        run: |
          shopt -s nullglob
          fail=0
          for f in content/*.json; do
            if ! python3 -m json.tool "$f" > /dev/null; then
              echo "::error file=$f::invalid JSON"
              fail=1
            fi
          done
          [ "$fail" -eq 0 ] && echo 'content JSON OK (or none present)'
          exit "$fail"
      - name: actionlint
        run: |
          bash <(curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/v1.7.7/scripts/download-actionlint.bash) 1.7.7 "$RUNNER_TEMP"
          "$RUNNER_TEMP/actionlint" -color
```

- [ ] **Step 3: Lint the workflow**

```bash
"$ACTIONLINT_DIR/actionlint" -color
```

Expected: no output, exit 0. (actionlint auto-discovers `.github/workflows/`; run from the repo root.)

- [ ] **Step 4: Exercise the detect and guard logic locally**

The detect scan, against the current repo state (expect all three `false` — repo is docs-only):

```bash
has_pipeline=false; [ -f pipeline/pyproject.toml ] && has_pipeline=true
has_app=false; compgen -G 'app/*.xcodeproj' > /dev/null && has_app=true
has_content=false; compgen -G 'content/*.json' > /dev/null && has_content=true
echo "pipeline=$has_pipeline app=$has_app content=$has_content"
```

Expected: `pipeline=false app=false content=false`.

The PDF/build guards (expect empty — nothing tracked):

```bash
git ls-files -- '*.pdf'; git ls-files -- 'build/*' '*.db'; echo "guards clean"
```

Expected: only `guards clean` printed.

Negative test for the changed-path regex (must match app/content/schema/workflow paths, must not match docs):

```bash
regex='^(app/|content/|pipeline/src/benchside_pipeline/build\.py|\.github/workflows/)'
for p in app/Benchside.xcodeproj/x content/tcg-rules.json pipeline/src/benchside_pipeline/build.py .github/workflows/ci.yml; do
  echo "$p" | grep -qE "$regex" || echo "FAIL should match: $p"
done
for p in README.md docs/superpowers/specs/x.md pipeline/src/benchside_pipeline/parse.py sources/sources.yaml; do
  echo "$p" | grep -qE "$regex" && echo "FAIL should NOT match: $p"
done
echo "regex OK"
```

Expected: only `regex OK`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CI workflow with repo-state detection and guard checks"
```

---

### Task 2: `ci.yml` pipeline and app jobs

**Files:**
- Modify: `.github/workflows/ci.yml` (append two jobs)

**Interfaces:**
- Consumes: `detect` job outputs from Task 1 (`has-pipeline`, `has-app`, `has-content`, `app-relevant`).
- Produces: jobs `pipeline` and `app`. Commands match the content-pipeline plan exactly: install `pip install -e '.[dev]'`, test `pytest -v`, content check `python -m benchside_pipeline build|verify --root ..` from `pipeline/`.

- [ ] **Step 1: Append the jobs**

Add to the `jobs:` map in `.github/workflows/ci.yml`, after `guards`:

```yaml
  pipeline:
    needs: detect
    if: needs.detect.outputs.has-pipeline == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: pipeline
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: pipeline/pyproject.toml
      - name: Install
        run: pip install -e '.[dev]'
      - name: Unit tests (fixture-based, no real PDFs)
        run: pytest -v
      - name: Build and verify committed content
        if: needs.detect.outputs.has-content == 'true'
        run: |
          python -m benchside_pipeline build --root ..
          python -m benchside_pipeline verify --root ..

  app:
    needs: detect
    if: needs.detect.outputs.has-app == 'true' && needs.detect.outputs.app-relevant == 'true'
    runs-on: macos-15
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - name: Discover project and scheme
        id: xcode
        run: |
          shopt -s nullglob
          projects=(app/*.xcodeproj)
          if [ "${#projects[@]}" -ne 1 ]; then
            echo "::error::expected exactly one .xcodeproj under app/, found ${#projects[@]}"
            exit 1
          fi
          project="${projects[0]}"
          scheme=$(xcodebuild -list -project "$project" -json \
            | python3 -c 'import json,sys; s=json.load(sys.stdin)["project"]["schemes"]; print(s[0] if s else "")')
          if [ -z "$scheme" ]; then
            echo "::error::no shared schemes in $project — share the Benchside scheme in Xcode"
            exit 1
          fi
          echo "project=$project" >> "$GITHUB_OUTPUT"
          echo "scheme=$scheme" >> "$GITHUB_OUTPUT"
      - name: Unit and UI tests
        run: |
          xcodebuild test \
            -project '${{ steps.xcode.outputs.project }}' \
            -scheme '${{ steps.xcode.outputs.scheme }}' \
            -destination 'platform=iOS Simulator,name=iPhone 16' \
            CODE_SIGNING_ALLOWED=NO
```

- [ ] **Step 2: Lint**

```bash
"$ACTIONLINT_DIR/actionlint" -color
```

Expected: no output, exit 0.

- [ ] **Step 3: Sanity-check the scheme-discovery python one-liner**

```bash
echo '{"project":{"schemes":["Benchside","Other"]}}' \
  | python3 -c 'import json,sys; s=json.load(sys.stdin)["project"]["schemes"]; print(s[0] if s else "")'
echo '{"project":{"schemes":[]}}' \
  | python3 -c 'import json,sys; s=json.load(sys.stdin)["project"]["schemes"]; print(s[0] if s else "")'
```

Expected: first prints `Benchside`, second prints an empty line.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add pipeline (pytest + content verify) and app (xcodebuild) jobs"
```

---

### Task 3: PR title check

**Files:**
- Create: `.github/workflows/pr-title.yml`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: workflow `PR Title` with job `conventional-title`.

- [ ] **Step 1: Test the regex locally first**

```bash
pattern='^(feat|fix|chore|docs|ci|refactor|test)(\([a-z0-9-]+\))?!?: .+'
good=('feat: add search' 'fix(pipeline): handle empty body' 'ci: add workflows' 'refactor!: drop v1 schema' 'docs(app-notes): reader screen')
bad=('Add search' 'feat add search' 'feat(): x' 'style: reorder imports' 'feat:missing space' 'ci: ')
for t in "${good[@]}"; do printf '%s' "$t" | grep -qE "$pattern" || echo "FAIL should pass: $t"; done
for t in "${bad[@]}"; do printf '%s' "$t" | grep -qE "$pattern" && echo "FAIL should reject: $t"; done
echo "title regex OK"
```

Expected: only `title regex OK`.

- [ ] **Step 2: Write the workflow**

`.github/workflows/pr-title.yml`:

```yaml
name: PR Title

on:
  pull_request:
    types: [opened, edited, reopened, synchronize]

permissions: {}

jobs:
  conventional-title:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Conventional Commits title
        env:
          TITLE: ${{ github.event.pull_request.title }}
        run: |
          pattern='^(feat|fix|chore|docs|ci|refactor|test)(\([a-z0-9-]+\))?!?: .+'
          if printf '%s' "$TITLE" | grep -qE "$pattern"; then
            echo "PR title OK: $TITLE"
          else
            echo "::error::PR title must be Conventional Commits — type(scope)?: summary, type in {feat,fix,chore,docs,ci,refactor,test}. Squash-merge makes this the main commit subject. Got: $TITLE"
            exit 1
          fi
```

- [ ] **Step 3: Lint**

```bash
"$ACTIONLINT_DIR/actionlint" -color
```

Expected: no output, exit 0.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/pr-title.yml
git commit -m "ci: enforce Conventional Commits PR titles"
```

---

### Task 4: Docs sync

**Files:**
- Modify: `README.md` (badge + one CI sentence)
- Modify: `CLAUDE.md` (Quality gates section)

**Interfaces:**
- Consumes: workflow file `ci.yml` from Task 1 (badge URL references it by filename).

- [ ] **Step 1: Add the badge and CI sentence to README.md**

Read `README.md` first; insert the badge directly under the top-level `# Benchside` heading line:

```markdown
[![CI](https://github.com/peteb4ker/benchside/actions/workflows/ci.yml/badge.svg)](https://github.com/peteb4ker/benchside/actions/workflows/ci.yml)
```

and append a short section at the end:

```markdown
## CI

Every PR runs [CI](.github/workflows/ci.yml): repo guards (no committed
PDFs or build products, manifest/content validity, workflow lint),
pipeline `pytest` plus a build+verify of committed content, and the app's
`xcodebuild test` when app-relevant paths change. PR titles must be
Conventional Commits (squash merge uses them as commit subjects).
```

- [ ] **Step 2: Update CLAUDE.md Quality gates**

Append one bullet to the `## Quality gates` list in `CLAUDE.md`:

```markdown
- **CI enforces the gates.** `.github/workflows/ci.yml` runs the guard
  checks (no PDFs/DBs in git, manifest + content validity), pipeline
  tests, content build+verify, and app tests on app-relevant changes.
  Checks are advisory (no branch protection on the current GitHub plan) —
  a red check still means stop and fix.
```

- [ ] **Step 3: Verify docs render sanely**

```bash
grep -n 'actions/workflows/ci.yml/badge.svg' README.md && grep -n 'CI enforces the gates' CLAUDE.md
```

Expected: one hit in each file.

- [ ] **Step 4: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document CI coverage in README and CLAUDE.md"
```

---

### Task 5: Push, open PR, watch CI go green

**Files:** none (integration).

**Interfaces:**
- Consumes: everything above; issue #2.

- [ ] **Step 1: Push the branch**

```bash
git push -u origin HEAD
```

- [ ] **Step 2: Open the PR**

Title: `ci: add GitHub Actions CI (guards, pipeline, app, PR title)`.
Body: summary of the four workflows/jobs, test plan (actionlint + local snippet runs + this PR's own checks), `Closes #2`, and the
`🤖 Generated with [Claude Code](https://claude.com/claude-code)` trailer.

```bash
gh pr create --title "ci: add GitHub Actions CI (guards, pipeline, app, PR title)" --body-file <(...)
```

- [ ] **Step 3: Watch the checks**

```bash
gh pr checks --watch
```

Expected: `detect`, `guards`, `conventional-title` pass; `pipeline` and `app` are skipped (repo has no `pipeline/` or `app/` yet). Any failure: read the run log with `gh run view --log-failed`, fix, push, re-watch. Do not merge — leave the PR for Pete's review (squash merge per CLAUDE.md).
