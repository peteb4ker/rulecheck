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

# Rewrites-layer coverage / archetype / review report
content-status:
    cd pipeline && uv run python -m benchside_pipeline content-status --root ..

# --- decomposition skill validators (buddy scripts) ---

# After authoring: schema, coverage, quotes, overlap, see-also, personas
check-decomposition: build
    cd pipeline && uv run python -m benchside_pipeline verify --root ..
    cd pipeline && uv run python -m benchside_pipeline content-status --root ..
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
    cp build/benchside.db app/Benchside/Resources/benchside.db

# Regenerate the Xcode project from app/project.yml
app-gen:
    cd app && xcodegen generate

_first-sim := `xcrun simctl list devices available | grep -m1 -o 'iPhone [^(]*' | sed 's/ *$//' || true`

app-build: app-db
    cd app && xcodebuild build -project Benchside.xcodeproj -scheme Benchside \
      -destination 'platform=iOS Simulator,name={{_first-sim}}' -quiet

# Full pre-PR gate: unit + UI tests (slow — cold builds and sim flows)
app-test: app-db
    cd app && time xcodebuild test -project Benchside.xcodeproj -scheme Benchside \
      -destination 'platform=iOS Simulator,name={{_first-sim}}' -quiet

# Fast inner loop: unit tests only, incl. the persona gates (~5s warm)
app-test-unit: app-db
    cd app && time xcodebuild test -project Benchside.xcodeproj -scheme Benchside \
      -destination 'platform=iOS Simulator,name={{_first-sim}}' \
      -only-testing:BenchsideTests -quiet
