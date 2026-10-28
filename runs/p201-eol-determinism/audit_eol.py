"""p201 — is every hashed file reproducible from a fresh clone?

`runs/SHA256SUMS.txt` hashes raw bytes (tools/check_hashes.py). With
core.autocrlf=true and no .gitattributes, git rewrites text files to CRLF on
checkout, so the bytes a clean clone gets are not the bytes this machine hashed.
The manifest then "passes" here and mismatches everywhere else.

This compares, for every path in tools/hash_evidence.py:FILES, the sha256 of the
working-tree file against the sha256 of the bytes git would actually check out
(the blob in the index). Equal means reproducible; different means the entry is
only valid on a machine that never checked the file out.

  python runs/p201-eol-determinism/audit_eol.py            # report only
  python runs/p201-eol-determinism/audit_eol.py --json     # machine-readable
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_files() -> list[str]:
    spec = importlib.util.spec_from_file_location(
        "hash_evidence", ROOT / "tools" / "hash_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.FILES)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def index_blob(rel: str) -> bytes | None:
    """The bytes `git checkout` would write for this path (filter applied)."""
    proc = subprocess.run(["git", "cat-file", "blob", f":{rel}"], cwd=ROOT,
                          capture_output=True)
    if proc.returncode != 0:
        return None
    return proc.stdout


def cat_file_eol(rel: str) -> tuple[str, str]:
    """(index eol, worktree eol) as git reports them: lf / crlf / mixed / -text."""
    proc = subprocess.run(["git", "ls-files", "--eol", "--", rel], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8")
    fields = proc.stdout.split()
    if len(fields) < 2:
        return ("?", "?")
    return (fields[0].split("/", 1)[1] if "/" in fields[0] else "?",
            fields[1].split("/", 1)[1] if "/" in fields[1] else "?")


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    files = load_files()
    reproducible, drifted, missing = [], [], []
    rows = []
    for rel in files:
        path = ROOT / rel
        if not path.exists():
            missing.append(rel)
            continue
        work = sha256_bytes(path.read_bytes())
        blob = index_blob(rel)
        if blob is None:
            missing.append(rel)
            continue
        want = sha256_bytes(blob)
        row = {"path": rel, "worktree": work, "index": want,
               "eol": cat_file_eol(rel), "same": work == want}
        rows.append(row)
        (reproducible if row["same"] else drifted).append(rel)

    if as_json:
        print(json.dumps({
            "total": len(files),
            "reproducible_from_clone": len(reproducible),
            "drifted": drifted,
            "missing_or_untracked": missing,
            "rows": rows,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"hashed paths: {len(files)}")
        print(f"reproducible from a fresh clone: {len(reproducible)}")
        print(f"worktree bytes != checkout bytes: {len(drifted)}")
        for rel in drifted[:12]:
            i_eol, w_eol = cat_file_eol(rel)
            print(f"  {rel}  index={i_eol} worktree={w_eol}")
        if len(drifted) > 12:
            print(f"  ... {len(drifted) - 12} more")
        if missing:
            print(f"missing / untracked: {len(missing)}")
            for rel in missing[:12]:
                print(f"  {rel}")
    return 0 if not drifted and not missing else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
