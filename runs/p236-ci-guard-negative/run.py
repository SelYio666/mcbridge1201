"""p236: negative test for the CI guards.

1. clone this repo into work/tmp/p236-neg (throwaway, no push)
2. edit a hashed doc WITHOUT refreshing runs/SHA256SUMS.txt, commit it
3. check_hashes must fail (this is what the new CI step catches)
4. check_manifest_coverage must still pass (it checks a different property)
5. refresh the manifest with hash_evidence, then check_hashes must pass
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
CLONE = ROOT / "work" / "tmp" / "p236-neg"


def sh(args, cwd=CLONE, check=False):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode:
        raise RuntimeError(f"{args[0]} failed: {r.stderr[:400]}")
    return r


def main() -> int:
    if CLONE.exists():
        shutil.rmtree(CLONE)
    sh(["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(CLONE)], cwd=ROOT, check=True)

    doc = CLONE / "docs" / "remaining-work.md"
    doc.write_text(doc.read_text(encoding="utf-8") + "\nNEGATIVE-TEST-LINE\n", encoding="utf-8")
    sh(["git", "add", "docs/remaining-work.md"], check=True)
    sh(["git", "-c", "user.name=p236", "-c", "user.email=p236@local", "commit", "-q",
        "-m", "test: stale manifest (should fail the hash guard)"], check=True)

    stale_hash = sh([sys.executable, "tools/check_hashes.py"])
    stale_cov = sh([sys.executable, "tools/check_manifest_coverage.py"])
    sh([sys.executable, "tools/hash_evidence.py"], check=True)
    fresh_hash = sh([sys.executable, "tools/check_hashes.py"])

    def tail(r, n=2):
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        return lines[-n:]

    payload = {
        "stale_manifest": {
            "check_hashes_rc": stale_hash.returncode,
            "check_hashes_tail": tail(stale_hash),
            "coverage_rc": stale_cov.returncode,
            "coverage_tail": tail(stale_cov, 1),
        },
        "after_refresh": {
            "check_hashes_rc": fresh_hash.returncode,
            "check_hashes_tail": tail(fresh_hash),
        },
        "checks": {
            "stale_detected": stale_hash.returncode != 0 and "mismatch=0" not in stale_hash.stdout,
            "coverage_unaffected": stale_cov.returncode == 0,
            "refresh_fixes_it": fresh_hash.returncode == 0 and "mismatch=0" in fresh_hash.stdout,
        },
    }
    payload["passed"] = all(payload["checks"].values())
    payload["total"] = len(payload["checks"])
    (RUN / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
