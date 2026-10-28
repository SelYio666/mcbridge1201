"""Detect encoding damage in tracked Markdown documents.

Catches the failure mode that mangled README.md, docs/FINAL-STATUS.md and
runs/p125-final-acceptance/README.md around p195: UTF-8 bytes read as cp936
and re-saved (锛 鈥 銆-style double encoding, GBK user-area U+E000..F8FF
artifacts, and the corruptor's '?' where a lost byte could not pair).

Rules per file (every hit is a finding, exit 1):
  bad-utf8     the file is not valid UTF-8
  fffd         contains U+FFFD replacement characters
  pua          contains GBK user-area private-use characters U+E000..F8FF
  signature    contains characters that only arise from UTF-8-as-cp936 decoding
               (锛 鈥 銆 鍦 乣 夛 坄 嶅 ...); none of the tracked docs uses them
  question     an ASCII '?' directly adjacent to CJK/fullwidth text, or a run
               of two or more '?'  (the corruptor wrote one '?' per lost byte)
  double-enc   a run of >= 6 CJK chars whose GBK re-encoding is itself valid
               UTF-8 — the general form of the damage, catches new content

Exemptions: a document that has to quote the damaged bytes on purpose (the p198
report) would trip the four content rules by design. Those files are listed in
EXEMPT with a reason; they still must be valid UTF-8 with no U+FFFD, and the
guard always prints how many findings were suppressed so an exemption can never
hide damage silently.

Usage:
  python tools/check_text_encoding.py            # scan git-tracked *.md
  python tools/check_text_encoding.py PATH...    # scan explicit files

Exit codes: 0 clean; 1 findings; 2 usage error.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SIGNATURE_CHARS = "锛鈥銆鍦乣夛坄嶅鈻鈹煈锟嘺"
QUESTION = "?"

MIN_DOUBLE_ENC_RUN = 6

# rule ids that an exempt (quote-the-damage) document may legitimately trip
CONTENT_RULES = {"pua", "signature", "question-run", "question-near-cjk", "double-enc"}

# rel path (posix) -> reason. Keep this list short and reviewed: adding a file here
# means "this document quotes the corruption on purpose", not "this file is broken".
EXEMPT = {
    "runs/p198-text-encoding/README.md":
        "p198 report quotes the damaged bytes to show what was repaired",
}


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (
        0x2E80 <= o <= 0x9FFF          # CJK radicals .. unified
        or 0xF900 <= o <= 0xFAFF       # compatibility ideographs
        or 0xFF00 <= o <= 0xFFEF       # fullwidth forms
        or 0x3000 <= o <= 0x303F       # CJK punctuation
    )


def _double_encoded_runs(text: str) -> list[tuple[int, str]]:
    """Runs of CJK that re-encode to valid UTF-8 through GBK: the text was
    produced by decoding UTF-8 bytes as cp936."""
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.split("\n"), 1):
        i = 0
        while i < len(line):
            if not _is_cjk(line[i]):
                i += 1
                continue
            j = i
            while j < len(line) and _is_cjk(line[j]):
                j += 1
            run = line[i:j]
            if len(run) >= MIN_DOUBLE_ENC_RUN:
                try:
                    run.encode("gbk").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
                else:
                    hits.append((lineno, run))
            i = j
    return hits


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def findings_for(path: Path) -> list[tuple[str, str]]:
    """(rule, message) pairs. Structural rules keep the raw path for bad-utf8."""
    raw = path.read_bytes()
    rel = _rel(path)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [("bad-utf8", f"{path}: bad-utf8: {exc}")]
    findings: list[tuple[str, str]] = []
    for lineno, line in enumerate(text.split("\n"), 1):
        where = f"{rel}:{lineno}"
        snippet = line.strip()
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        if "\ufffd" in line:
            findings.append(("fffd", f"{where}: fffd: {snippet}"))
        for ch in line:
            if 0xE000 <= ord(ch) <= 0xF8FF:
                findings.append(("pua", f"{where}: pua U+{ord(ch):04X}: {snippet}"))
                break
        for ch in SIGNATURE_CHARS:
            if ch in line:
                findings.append(("signature", f"{where}: signature {ch}: {snippet}"))
                break
        for m in re.finditer(r"\?{2,}", line):
            findings.append(("question-run",
                             f"{where}: question-run {m.group(0)[:8]}: {snippet}"))
            break
        for m in re.finditer(r"\?", line):
            a, b = m.start() - 1, m.end()
            prev_cjk = a >= 0 and _is_cjk(line[a])
            next_cjk = b < len(line) and _is_cjk(line[b])
            if prev_cjk or next_cjk:
                near = line[max(0, m.start() - 10):m.end() + 10]
                findings.append(("question-near-cjk", f"{where}: question-near-cjk ...{near}..."))
                break
    for lineno, run in _double_encoded_runs(text):
        findings.append(("double-enc", f"{rel}:{lineno}: double-enc {run[:24]}..."))
    return findings


def tracked_markdown() -> list[Path]:
    proc = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        print(f"git ls-files failed: {proc.stderr}", file=sys.stderr)
        raise SystemExit(2)
    return [ROOT / line for line in proc.stdout.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(a) for a in argv]
    else:
        paths = tracked_markdown()
    dirty = 0
    total = 0
    exempted = 0
    suppressed = 0
    for path in paths:
        if not path.exists():
            print(f"missing file: {path}", file=sys.stderr)
            return 2
        found = findings_for(path)
        reason = EXEMPT.get(_rel(path))
        if reason:
            kept = [f for f in found if f[0] not in CONTENT_RULES]
            dropped = len(found) - len(kept)
            exempted += 1
            suppressed += dropped
            print(f"exempt: {_rel(path)} — {reason}; "
                  f"{dropped} content finding(s) suppressed, {len(kept)} structural kept")
            found = kept
        if found:
            dirty += 1
            total += len(found)
            for _, message in found:
                print(message)
    if exempted:
        print(f"exempt files: {exempted}, suppressed content findings: {suppressed}")
    print(f"checked {len(paths)} markdown file(s): "
          f"{len(paths) - dirty} clean, {total} finding(s)")
    return 1 if dirty else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
