"""Quantify how much of the p195 corruption was byte-reversible.

For every repaired document this reads the damaged blob at HEAD, tries the inverse
of the corruption (re-encode as GBK, decode as UTF-8) per line and per non-ASCII
run, and reports how much of the shipped text is a true restoration versus a
reconstruction. Nothing is guessed: a segment counts as reversible only when the
round trip yields valid UTF-8.

Usage:
  python runs/p198-text-encoding/restore_report.py [--rev REV]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FILES = [
    "README.md",
    "docs/FINAL-STATUS.md",
    "runs/p125-final-acceptance/README.md",
]


def head_blob(rel: str, rev: str) -> str:
    proc = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=ROOT, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(f"git show {rev}:{rel} failed: {proc.stderr.decode('utf-8', 'replace')}")
    return proc.stdout.decode("utf-8", errors="replace")


def reversible(text: str) -> bool:
    try:
        text.encode("gbk").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False
    return True


def runs_of(text: str):
    """Maximal non-ASCII runs, the unit the corruptor damaged byte by byte."""
    i = 0
    while i < len(text):
        if ord(text[i]) <= 0x7F:
            i += 1
            continue
        j = i
        while j < len(text) and ord(text[j]) > 0x7F:
            j += 1
        yield text[i:j]
        i = j


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default="HEAD")
    args = ap.parse_args(argv)

    grand = {"lines": 0, "identical": 0, "restored": 0, "rewritten": 0,
             "runs": 0, "runs_reversible": 0, "chars": 0, "chars_reversible": 0}
    per_file = {}
    for rel in FILES:
        old = head_blob(rel, args.rev)
        new = (ROOT / rel).read_text(encoding="utf-8")
        old_lines, new_lines = old.split("\n"), new.split("\n")
        stats = {"lines": len(old_lines), "new_lines": len(new_lines), "identical": 0,
                 "restored": 0, "rewritten": 0, "line_count_match": len(old_lines) == len(new_lines),
                 "runs": 0, "runs_reversible": 0, "chars": 0, "chars_reversible": 0}
        if stats["line_count_match"]:
            for a, b in zip(old_lines, new_lines):
                if a == b:
                    stats["identical"] += 1
                elif reversible(a):
                    stats["restored"] += 1
                else:
                    stats["rewritten"] += 1
        for line in old_lines:
            for run in runs_of(line):
                stats["runs"] += 1
                stats["chars"] += len(run)
                if reversible(run):
                    stats["runs_reversible"] += 1
                    stats["chars_reversible"] += len(run)
        per_file[rel] = stats
        for key in grand:
            if key in stats:
                grand[key] += stats[key]

    print(f"restore report against {args.rev}")
    print("")
    print("| file | lines | identical | line-restored | rewritten | runs | runs reversible | chars | chars reversible |")
    print("|---|---|---|---|---|---|---|---|---|")
    for rel, s in per_file.items():
        print(f"| `{rel}` | {s['lines']} | {s['identical']} | {s['restored']} | {s['rewritten']} "
              f"| {s['runs']} | {s['runs_reversible']} | {s['chars']} | {s['chars_reversible']} |")
    print("")
    runs_pct = 100.0 * grand["runs_reversible"] / max(grand["runs"], 1)
    chars_pct = 100.0 * grand["chars_reversible"] / max(grand["chars"], 1)
    print(f"line count preserved for every file: "
          f"{all(s['line_count_match'] for s in per_file.values())}")
    print(f"lines: {grand['identical']} untouched, {grand['restored']} restored by round trip, "
          f"{grand['rewritten']} reconstructed")
    print(f"damaged runs: {grand['runs_reversible']}/{grand['runs']} reversible ({runs_pct:.1f}%)")
    print(f"damaged chars: {grand['chars_reversible']}/{grand['chars']} reversible ({chars_pct:.1f}%)")
    print(f"reconstructed share: {100.0 - chars_pct:.1f}% of damaged characters had lost bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
