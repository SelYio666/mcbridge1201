#!/usr/bin/env python3
"""Freeze the 1.21.1 baseline as one machine-readable lock, and re-check it later.

Why this exists: the repository already records a lot of state in prose (`docs/FINAL-STATUS.md`),
per-artifact evidence (`profiles/`), a byte manifest (`runs/SHA256SUMS.txt`) and an environment
lock (`manifests/environment.lock.json`). None of those answers the question a new target asks
first: *what exactly was the 1.21.1 conversion when it was declared the baseline, and what has
drifted since?* This script answers it with hashes instead of prose.

    python tools/freeze_baseline.py                     # write manifests/baseline.lock.json
    python tools/freeze_baseline.py --check             # compare the tree against the lock
    python tools/freeze_baseline.py --check --json out.json
    python tools/freeze_baseline.py --run-gates         # freeze + run the release gates

`--check` distinguishes "an input changed" (rules, bridge sources, target profiles, pinned
indices, evidence statuses) from "the git state changed" (dirty files, commit). Only the first
kind means the frozen contract moved; the second is recorded but not compared, because a
worktree is expected to be ahead of the commit it was frozen at.

Exit codes: 0 ok, 1 drift / gate failure, 2 usage or environment problem.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "manifests" / "baseline.lock.json"
SCHEMA = "baseline-lock-1"

RULES_DIR = "rules/fabric-1.21.1"
SOURCE_TREES = [
    "java/src/main",
    "java/src/bridge",
    "java/src/bridge-shim",
    "java/src/mixin",
    "java/src/test",
]
TOOL_FILES = [
    "tools/check_hashes.py",
    "tools/check_manifest_coverage.py",
    "tools/check_text_encoding.py",
    "tools/verify_evidence.py",
    "tools/hash_evidence.py",
    "tools/release_check.py",
    "tools/build_bridges.py",
    "tools/conversion_cache.py",
    "tools/build_source_fixture.py",
    "tools/fetch_target_1214.py",
    "tools/run_1214_delta.py",
    "tools/scan_registration_sites.py",
    "tools/run_target_gate.py",
    "tools/run_isolation_cache.py",
    "tools/run_source_fixture_probe.py",
    "tools/run_contract.py",
    "tools/run_server.py",
    "tools/build_reports.py",
    "tools/freeze_baseline.py",
]
# Documents that state the current contract, as opposed to the running history log.
CURRENT_DOCS = [
    "docs/FINAL-STATUS.md",
    "docs/remaining-work.md",
    "docs/STATUS.md",
    "docs/support-matrix.md",
    "docs/limitations.md",
    "docs/multi-target-baseline.md",
]
HISTORICAL_DOCS = [
    "docs/progress.md",
    "docs/baseline.md",
    "docs/handoff.md",
    "docs/handover-zcode.md",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def files_under(relpath: str, suffixes: tuple[str, ...]) -> list[Path]:
    base = ROOT / relpath
    if not base.exists():
        return []
    return sorted((p for p in base.rglob("*") if p.is_file() and p.suffix in suffixes),
                  key=lambda p: rel(p))


def hash_group(relpath: str, suffixes: tuple[str, ...]) -> dict:
    files = files_under(relpath, suffixes)
    entries = [{"path": rel(p), "sha256": sha256(p), "size": p.stat().st_size} for p in files]
    package = hashlib.sha256()
    for e in entries:
        package.update(e["path"].encode("utf-8"))
        package.update(e["sha256"].encode("ascii"))
    return {"root": relpath, "count": len(entries), "packageSha256": package.hexdigest(),
            "files": entries}


def hash_list(paths: list[str]) -> dict:
    entries = []
    for p in paths:
        full = ROOT / p
        if full.is_file():
            entries.append({"path": p, "sha256": sha256(full), "size": full.stat().st_size})
        else:
            entries.append({"path": p, "sha256": None, "missing": True})
    package = hashlib.sha256()
    for e in entries:
        package.update(e["path"].encode("utf-8"))
        package.update(str(e["sha256"]).encode("ascii"))
    return {"count": len(entries), "present": sum(1 for e in entries if e.get("sha256")),
            "packageSha256": package.hexdigest(), "files": entries}


def git_state() -> dict:
    def run(*args: str) -> str | None:
        try:
            p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        except OSError:
            return None
        return p.stdout.strip() if p.returncode == 0 else None

    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    dirty_files, untracked = [], []
    for line in (status or "").splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if line.startswith("??"):
            untracked.append(path)
        else:
            dirty_files.append(path)
    return {
        "commit": commit,
        "branch": run("branch", "--show-current"),
        "dirty": bool(dirty_files or untracked),
        "modifiedFiles": sorted(dirty_files),
        "untrackedFiles": sorted(untracked),
        "note": "Recorded, not compared by --check: a worktree is expected to be ahead of the"
                " commit it was frozen at. Only inputs.* moving means the frozen contract moved.",
    }


def environment_state() -> dict:
    path = ROOT / "manifests" / "environment.lock.json"
    if not path.is_file():
        return {"path": "manifests/environment.lock.json", "missing": True}
    data = json.loads(path.read_text(encoding="utf-8"))
    targets = []
    for m in data.get("minecraft", []):
        targets.append({
            "minecraft": m.get("minecraft"),
            "javaMajor": (m.get("javaVersion") or {}).get("majorVersion"),
            "clientJarSha256": (m.get("clientJar") or {}).get("sha256"),
            "mappingsSha256": (m.get("clientMappings") or {}).get("sha256"),
        })
    fabric = {}
    for key in ("intermediary-1.20.1", "intermediary-1.21.1", "loader", "api", "api-1.20.1"):
        entry = (data.get("fabric") or {}).get(key)
        if entry:
            fabric[key] = {"version": entry.get("version"), "sha256": entry.get("sha256")}
    return {"path": rel(path), "sha256": sha256(path), "generatedAt": data.get("generatedAt"),
            "targets": targets, "fabric": fabric}


def target_profiles() -> dict:
    out = []
    base = ROOT / "targets"
    if not base.is_dir():
        return {"count": 0, "profiles": []}
    for p in sorted(base.glob("*.json"), key=lambda x: x.name):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            out.append({"path": rel(p), "sha256": sha256(p), "error": str(exc)})
            continue
        target = data.get("target") or {}
        pipeline = data.get("pipeline") or {}
        out.append({
            "path": rel(p),
            "sha256": sha256(p),
            "profileId": data.get("profileId"),
            "targetId": target.get("id"),
            "minecraft": target.get("minecraft"),
            "loader": target.get("loader"),
            "javaMajor": target.get("javaMajor"),
            "namespace": target.get("namespace"),
            "bridgeAbi": pipeline.get("bridgeAbi"),
            "ruleOrderEntries": len(pipeline.get("ruleOrder") or []),
        })
    return {"count": len(out), "profiles": out}


def evidence_state() -> dict:
    """Per-artifact evidence: status and contract outcome, hashed by file."""
    items = []
    contracts: dict[str, int] = {}
    base = ROOT / "profiles"
    if base.is_dir():
        for p in sorted(base.glob("*.json"), key=lambda x: x.name):
            data = json.loads(p.read_text(encoding="utf-8"))
            reqs = data.get("requiredContracts") or []
            passed = sum(1 for c in reqs if c.get("result") == "passed")
            pending = sum(1 for c in reqs if c.get("result") == "pending")
            failed = sum(1 for c in reqs if c.get("result") not in ("passed", "pending"))
            for c in reqs:
                contracts[c.get("id", "?")] = contracts.get(c.get("id", "?"), 0) + 1
            items.append({
                "path": rel(p),
                "sha256": sha256(p),
                "profileId": data.get("profileId"),
                "status": data.get("status"),
                "contractsPassed": passed,
                "contractsPending": pending,
                "contractsOther": failed,
                "knownLimitations": len(data.get("knownLimitations") or []),
            })
    return {
        "profiles": items,
        "profilesByStatus": {s: sum(1 for i in items if i["status"] == s)
                             for s in sorted({i["status"] for i in items})},
        "note": "Status vocabulary is passed_within_scope / booted_within_scope / pending. It is"
                " narrower than 'compatible' and states scope, not breadth.",
    }


def degradations() -> dict:
    """Explicit losses. A strip is legal only if it says what it removes and why."""
    strips = []
    base = ROOT / RULES_DIR
    for p in sorted(base.glob("*.json"), key=lambda x: x.name):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for s in data.get("mixinStrips") or []:
            strips.append({"path": rel(p), "id": s.get("id"), "config": s.get("config"),
                           "classes": s.get("classes") or [], "reason": s.get("reason")})
    return {"mixinStrips": strips,
            "note": "Removing a mixin is a recorded degradation, never silent success. These are"
                    " the only ones declared in the frozen rule package."}


def historical_state() -> dict:
    entries = []
    for p in HISTORICAL_DOCS:
        full = ROOT / p
        entries.append({"path": p, "sha256": sha256(full) if full.is_file() else None,
                        "missing": not full.is_file()})
    return {
        "documents": entries,
        "policy": "These files are append-only history. Their older conclusions are NOT"
                  " re-adjudicated by this baseline: a claim from an earlier round stays a claim"
                  " from that round. Current contract = CURRENT_DOCS + profiles/ + this lock.",
        "currentDocs": [{"path": p, "sha256": sha256(ROOT / p) if (ROOT / p).is_file() else None}
                        for p in CURRENT_DOCS],
    }


def gate_steps() -> list[tuple[str, list[str]]]:
    py = sys.executable
    return [
        ("hash manifest matches the tree", [py, "tools/check_hashes.py"]),
        ("every run README/result is hashed", [py, "tools/check_manifest_coverage.py"]),
        ("markdown encoding is clean", [py, "-B", "tools/check_text_encoding.py"]),
        ("evidence gate (contracts + unit tests + encoding)", [py, "tools/verify_evidence.py"]),
    ]


def run_gates(verbose: bool = False) -> dict:
    env = dict(os.environ)
    if "JAVA_HOME" not in env:
        jdk = ROOT.parent / ".toolchain" / "jdk"
        if jdk.is_dir():
            env["JAVA_HOME"] = str(jdk)
    results = []
    ok = True
    for name, cmd in gate_steps():
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=1800, env=env)
            rc, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
        except subprocess.TimeoutExpired:
            rc, out = 124, "timeout"
        tail = [ln for ln in out.splitlines() if ln.strip()][-3:]
        results.append({"name": name, "rc": rc, "tail": tail})
        if verbose:
            print(f"  gate: {name} -> rc {rc}", flush=True)
        if rc != 0:
            ok = False
    return {"ran": True, "passed": ok, "steps": results,
            "note": "Gates run by this script are read-only checks over the tree; the game-side"
                    " contracts they summarize were not re-executed here."}


def build(run_gate_flag: bool) -> dict:
    rules = hash_group(RULES_DIR, (".json",))
    sources = {tree: hash_group(tree, (".java",)) for tree in SOURCE_TREES}
    lock = {
        "schemaVersion": SCHEMA,
        "generatedAt": utc_now(),
        "tool": "tools/freeze_baseline.py",
        "what": "The 1.20.1 -> Fabric 1.21.1 conversion frozen as a contract: the rule package,"
                " the bridge and converter sources, the pinned target indices, the per-artifact"
                " evidence statuses and the declared degradations, each by SHA-256.",
        "not": "Not a support claim and not a test run. Nothing here was executed to produce it"
               " except the optional --run-gates read-only checks.",
        "git": git_state(),
        "environment": environment_state(),
        "inputs": {
            "rules": rules,
            "sources": sources,
            "tools": hash_list(TOOL_FILES),
            "manifests": hash_list(["manifests/environment.lock.json", "manifests/upstream.lock.json",
                                    "manifests/corpus.json"]),
        },
        "targetProfiles": target_profiles(),
        "evidence": evidence_state(),
        "degradations": degradations(),
        "historical": historical_state(),
        "gates": run_gates() if run_gate_flag else {"ran": False,
                                                  "note": "Pass --run-gates to execute them."},
    }
    return lock


def utc_now() -> str:
    import datetime
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


# Fields that legitimately differ between two runs and must not count as drift.
VOLATILE = {"generatedAt", "git", "gates", "not", "what", "schemaVersion", "tool"}


def comparable(lock: dict) -> dict:
    return {k: v for k, v in lock.items() if k not in VOLATILE}


def diff(old: dict, new: dict, path: str = "") -> list[str]:
    """Flatten to dotted paths and report added/removed/changed leaves."""
    out: list[str] = []

    def walk(a, b, prefix: str) -> None:
        if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
            out.append(f"{prefix}: type {type(a).__name__} -> {type(b).__name__}")
            return
        if isinstance(a, dict):
            for key in sorted(set(a) | set(b)):
                sub = f"{prefix}.{key}" if prefix else key
                if key not in a:
                    out.append(f"{sub}: added")
                elif key not in b:
                    out.append(f"{sub}: removed")
                else:
                    walk(a[key], b[key], sub)
        elif isinstance(a, list):
            if len(a) != len(b):
                out.append(f"{prefix}: length {len(a)} -> {len(b)}")
                return
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{prefix}[{i}]")
        elif a != b:
            out.append(f"{prefix}: {short(a)} -> {short(b)}")

    walk(old, new, path)
    return out


def short(value) -> str:
    text = str(value)
    return text if len(text) <= 40 else text[:37] + "..."


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="compare the working tree against the frozen lock instead of writing it")
    ap.add_argument("--run-gates", action="store_true", help="also run the read-only release gates")
    ap.add_argument("--json", default=None, help="write the lock (or the check result) here")
    args = ap.parse_args()

    if args.check:
        if not LOCK.is_file():
            print(f"no baseline lock at {LOCK}; run without --check first", file=sys.stderr)
            return 2
        old = json.loads(LOCK.read_text(encoding="utf-8"))
        new = build(args.run_gates)
        changes = diff(comparable(old), comparable(new))
        report = {"lock": rel(LOCK), "drift": bool(changes), "changes": changes,
                  "comparedFields": sorted(comparable(new)),
                  "gate": new["gates"]}
        for line in changes:
            print("DRIFT", line)
        print(f"baseline {'DRIFTED' if changes else 'unchanged'}"
              f" ({len(changes)} change(s)); gates {'pass' if new['gates'].get('passed') else 'not run/failed'}")
        if args.json:
            Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8", newline="\n")
        return 1 if changes else 0

    lock = build(args.run_gates)
    text = json.dumps(lock, ensure_ascii=False, indent=2) + "\n"
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(text, encoding="utf-8", newline="\n")
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8", newline="\n")
    rules = lock["inputs"]["rules"]
    src_count = sum(g["count"] for g in lock["inputs"]["sources"].values())
    print(f"wrote {rel(LOCK)}")
    print(f"  commit {lock['git']['commit']} dirty={lock['git']['dirty']}")
    print(f"  rules {rules['count']} files, package {rules['packageSha256'][:16]}")
    print(f"  sources {src_count} .java files across {len(lock['inputs']['sources'])} trees")
    print(f"  target profiles {lock['targetProfiles']['count']}, evidence profiles {len(lock['evidence']['profiles'])}")
    print(f"  degradations {len(lock['degradations']['mixinStrips'])} declared mixin strip(s)")
    if lock["gates"].get("ran"):
        print(f"  gates {'PASS' if lock['gates'].get('passed') else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
