"""Tests for the CI simulator resolver.

It lives in .github/scripts rather than the pipeline package, because the
workflow runs it directly, but it carries real selection logic and picking the
wrong device wastes an eight minute macOS run to discover.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "resolve_simulator.py"

spec = importlib.util.spec_from_file_location("resolve_simulator", SCRIPT)
resolve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolve)


def devices(*entries):
    out = {}
    for runtime, name, udid in entries:
        out.setdefault(runtime, []).append(
            {"name": name, "udid": udid, "isAvailable": True})
    return json.dumps({"devices": out})


def run(payload, preferred="iPhone 16"):
    proc = subprocess.run([sys.executable, str(SCRIPT)], input=payload, text=True,
                          capture_output=True, env={"SIMULATOR_DEVICE": preferred,
                                                    "PATH": "/usr/bin:/bin"})
    return proc.returncode, proc.stdout.strip(), proc.stderr


IOS26 = "com.apple.CoreSimulator.SimRuntime.iOS-26-5"
IOS18 = "com.apple.CoreSimulator.SimRuntime.iOS-18-2"


def test_prefers_the_named_device_when_present():
    code, udid, err = run(devices((IOS26, "iPhone 16", "AAA"), (IOS26, "iPhone 17", "BBB")))
    assert code == 0 and udid == "AAA"
    assert "exact" in err


def test_falls_back_rather_than_failing_when_the_name_is_gone():
    """The whole point: the image dropping iPhone 16 must not turn every pull
    request red."""
    code, udid, err = run(devices((IOS26, "iPhone 17", "BBB"), (IOS26, "iPhone Air", "CCC")))
    assert code == 0, "a missing preferred device must not fail the job"
    assert udid == "BBB", "should choose the numbered model, not the alphabetical winner"
    assert "fallback" in err


def test_fallback_prefers_the_newest_runtime():
    code, udid, _ = run(devices((IOS18, "iPhone 17", "OLD"), (IOS26, "iPhone 15", "NEW")))
    assert (code, udid) == (0, "NEW")


def test_no_ios_simulator_at_all_is_a_clean_failure():
    payload = json.dumps({"devices": {
        "com.apple.CoreSimulator.SimRuntime.watchOS-11-0":
            [{"name": "Apple Watch Series 10", "udid": "W", "isAvailable": True}]}})
    code, udid, _ = run(payload)
    assert code == 1 and udid == ""


def test_unavailable_devices_are_ignored():
    payload = json.dumps({"devices": {IOS26: [
        {"name": "iPhone 16", "udid": "GONE", "isAvailable": False},
        {"name": "iPhone 15", "udid": "OK", "isAvailable": True}]}})
    code, udid, _ = run(payload)
    assert (code, udid) == (0, "OK"), "an unavailable device cannot be booted"


def test_model_number_ranks_numbered_models_above_unnumbered_ones():
    assert resolve.model_number("iPhone 17 Pro") == 17
    assert resolve.model_number("iPhone Air") == -1
    assert resolve.model_number("iPhone 17") > resolve.model_number("iPhone 16")


def test_runtime_version_orders_numerically_not_alphabetically():
    assert resolve.runtime_version(IOS26) > resolve.runtime_version(IOS18)
