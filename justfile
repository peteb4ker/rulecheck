# RuleCheck dev commands.
# Bootstrap: brew install uv && uv tool install rust-just && just setup

default:
    @just --list

# One-time / after dependency changes: sync pipeline env (uv manages .venv)
setup:
    cd pipeline && uv sync --all-extras

# Fetch official source PDFs (network!); exits 1 if TPCi revised a document
download:
    cd pipeline && uv run python -m rulecheck_pipeline download --root ..

# Authenticate the PDFs already in sources/ against sources.yaml (no network).
# Use after downloading them by hand when the upstream WAF blocks `just download`.
check-sources:
    cd pipeline && uv run python -m rulecheck_pipeline check-sources --root ..

parse:
    cd pipeline && uv run python -m rulecheck_pipeline parse --root ..

build:
    cd pipeline && uv run python -m rulecheck_pipeline build --root ..

verify:
    cd pipeline && uv run python -m rulecheck_pipeline verify --root ..

# parse → build → verify (offline; must end "verify OK")
all:
    cd pipeline && uv run python -m rulecheck_pipeline all --root ..

test:
    cd pipeline && uv run pytest

# Candidate vocabulary from the authored corpus (deterministic, re-runnable)
lexicon-candidates:
    cd pipeline && uv run python -m rulecheck_pipeline lexicon-candidates --root ..

# Concepts drawn from structure, not prose frequency (what rules turn on)
lexicon-structural:
    cd pipeline && uv run python -m rulecheck_pipeline lexicon-structural --root ..

# Independently check the lexicon against the corpus (the buddy script)
check-lexicon:
    python3 scripts/check_lexicon.py

# Rewrites-layer coverage / archetype / review report
content-status:
    cd pipeline && uv run python -m rulecheck_pipeline content-status --root ..

# Release build for a physical device. Debug builds are unoptimized and
# launch far slower on real hardware than in the simulator — use this for
# anything you actually carry to a tournament.
app-device: app-db
    cd app && xcodebuild build -project RuleCheck.xcodeproj -scheme RuleCheck \
      -configuration Release -destination 'generic/platform=iOS' -quiet
    @echo "Built Release. In Xcode: Product > Scheme > Edit Scheme > Run > Build Configuration = Release, then Run to your phone."

# --- decomposition skill validators (buddy scripts) ---

# After authoring: schema, coverage, quotes, overlap, see-also, personas
check-decomposition: build
    cd pipeline && uv run python -m rulecheck_pipeline verify --root ..
    cd pipeline && uv run python -m rulecheck_pipeline content-status --root ..
    cd pipeline && uv run pytest tests/test_personas.py -q

# After review: every shipped entry has a fresh, well-formed verdict
check-fidelity-review *ARGS:
    python3 scripts/check_fidelity_review.py --root . {{ARGS}}

# Committed content still reproduces from the source PDFs + manifest
# (runs inside the pipeline env — it imports the parser it validates)
check-ingest *ARGS:
    cd pipeline && uv run python ../scripts/check_ingest.py --root .. {{ARGS}}

# --- iOS app (Plan 2) ---

# Copy the built rules DB into the app bundle resources (runs pipeline build first)
app-db: build
    cp build/rulecheck.db app/RuleCheck/Resources/rulecheck.db

# Regenerate the Xcode project from app/project.yml
app-gen:
    cd app && xcodegen generate

_first-sim := `xcrun simctl list devices available | grep -m1 -o 'iPhone [^(]*' | sed 's/ *$//' || true`

app-build: app-db
    cd app && xcodebuild build -project RuleCheck.xcodeproj -scheme RuleCheck \
      -destination 'platform=iOS Simulator,name={{_first-sim}}' -quiet

# Full pre-PR gate: unit + UI tests (slow — cold builds and sim flows)
app-test: app-db
    cd app && time xcodebuild test -project RuleCheck.xcodeproj -scheme RuleCheck \
      -destination 'platform=iOS Simulator,name={{_first-sim}}' -quiet

# Fast inner loop: unit tests only, incl. the persona gates (~5s warm)
app-test-unit: app-db
    cd app && time xcodebuild test -project RuleCheck.xcodeproj -scheme RuleCheck \
      -destination 'platform=iOS Simulator,name={{_first-sim}}' \
      -only-testing:RuleCheckTests -quiet
