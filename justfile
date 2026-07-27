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

app-test: app-db
    cd app && xcodebuild test -project Benchside.xcodeproj -scheme Benchside \
      -destination 'platform=iOS Simulator,name={{_first-sim}}' -quiet
