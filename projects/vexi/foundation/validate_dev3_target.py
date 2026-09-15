"""Fail-closed target validation for the combined dev2+dev3 development patch."""
from __future__ import annotations
from pathlib import Path
import hashlib
import sys

EXPECTED_DEV1_GIT_BLOBS = {
    "core/vexi_foundation/contracts.py": "7ecf568a66ab6863f2b966d76c168668780742d4",
    "core/vexi_foundation/integrity.py": "c63fbe158a3b34d0de8380eacb2aabd7e548a4d0",
    "core/vexi_foundation/workspace.py": "617e0cfca8310fae17fc65b227b67eb8abeb5e79",
}
EXPECTED_DEV2_SHA256 = "9234cefb5e95fc912752ac8923258e7933012162289773239544c4860f3b7c4f"


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    failures = []
    for relative, expected in EXPECTED_DEV1_GIT_BLOBS.items():
        path = root / relative
        if not path.is_file():
            failures.append(f"MISSING {relative}")
            continue
        observed = git_blob_sha1(path.read_bytes())
        if observed != expected:
            failures.append(f"BASELINE_MISMATCH {relative} expected={expected} observed={observed}")
    dev2 = root / "core/vexi_foundation/document_lifecycle.py"
    if dev2.exists():
        observed = sha256(dev2.read_bytes())
        if observed != EXPECTED_DEV2_SHA256:
            failures.append(f"DEV2_MISMATCH core/vexi_foundation/document_lifecycle.py expected={EXPECTED_DEV2_SHA256} observed={observed}")
    if failures:
        print("DEV3 TARGET REJECTED")
        for item in failures: print(item)
        return 2
    print("DEV3 TARGET OK: exact dev1 interfaces detected; existing dev2 is compatible or absent")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
