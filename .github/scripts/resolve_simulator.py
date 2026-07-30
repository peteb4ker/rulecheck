"""Pick a simulator to test on.

The preferred device is a preference, not a requirement. Pinning a name with
no fallback means the day the runner image drops that device every pull
request goes red at once, and a runner that comes up with no simulator
runtimes at all produces a confusing "device not found" rather than saying so.

Reads `xcrun simctl list devices available --json` on stdin. Prints the chosen
udid, or nothing when the runner has no iPhone simulator at all.
"""

import json
import os
import re
import sys


def runtime_version(runtime: str) -> tuple[int, ...]:
    """Sort key from a runtime identifier such as ...SimRuntime.iOS-26-5."""
    digits = re.findall(r"\d+", runtime.rsplit(".", 1)[-1])
    return tuple(int(d) for d in digits)


def model_number(name: str) -> int:
    """Highest number in the device name, so iPhone 17 beats iPhone 16.

    Names without a number, such as "iPhone Air", sort below every numbered
    model rather than winning on an alphabetical accident.
    """
    digits = re.findall(r"\d+", name)
    return max((int(d) for d in digits), default=-1)


def main() -> int:
    preferred = os.environ.get("SIMULATOR_DEVICE", "")
    devices = json.load(sys.stdin)["devices"]

    candidates = []
    for runtime, entries in devices.items():
        if "iOS" not in runtime:
            continue
        for device in entries:
            if device.get("isAvailable") is False:
                continue
            if not device["name"].startswith("iPhone"):
                continue
            candidates.append((runtime_version(runtime), model_number(device["name"]),
                               device["name"], device["udid"]))

    if not candidates:
        return 1

    exact = [c for c in candidates if c[2] == preferred]
    # Newest runtime first, so a fallback lands on the most current iPhone
    # rather than whatever happens to sort first alphabetically.
    chosen = max(exact or candidates)
    print(chosen[3])
    print(f"{chosen[2]} (runtime {'.'.join(str(n) for n in chosen[0])})", file=sys.stderr)
    print("exact" if exact else "fallback", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
