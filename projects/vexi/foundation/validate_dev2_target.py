"""Fail-closed compatibility check before staging dev2 into Vexi 0.1.5.dev1 source."""
from __future__ import annotations
from pathlib import Path
import hashlib
import sys

EXPECTED_GIT_BLOBS = {
    "core/vexi_foundation/contracts.py": "7ecf568a66ab6863f2b966d76c168668780742d4",
    "core/vexi_foundation/integrity.py": "c63fbe158a3b34d0de8380eacb2aabd7e548a4d0",
    "core/vexi_foundation/workspace.py": "617e0cfca8310fae17fc65b227b67eb8abeb5e79",
}


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    failures = []
    for relative, expected in EXPECTED_GIT_BLOBS.items():
        path = root / relative
        if not path.is_file():
            failures.append(f"MISSING {relative}")
            continue
        observed = git_blob_sha1(path.read_bytes())
        if observed != expected:
            failures.append(f"BASELINE_MISMATCH {relative} expected={expected} observed={observed}")
    if failures:
        print("DEV2 TARGET REJECTED")
        for item in failures:
            print(item)
        return 2
    print("DEV2 TARGET OK: exact 0.1.5.dev1 foundation interfaces detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
