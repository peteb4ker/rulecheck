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
