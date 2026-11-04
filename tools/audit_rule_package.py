#!/usr/bin/env python3
"""Audit a rule package for history leftovers: capability clusters, missing evidence, orphans.

This does NOT change anything. It answers three questions a maintainer needs before touching a
package that grew over many sessions:

1. Which capabilities are covered by several rules at once? (Usually intentional - one bridge per
   member - but a cluster of one-off rules around a single capability is where duplication hides.)
2. Which rules carry no `evidence` text? A rule without evidence cannot be re-judged later; it can
   only be trusted or deleted.
3. Which rules are never mentioned in any `runs/` README or result? An orphan is not necessarily
   wrong - it may have been added ahead of its evidence - but it should be known.

    python tools/audit_rule_package.py --rules-dir rules/fabric-1.21.1
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "runs" / "p270-rule-package-audit"
LIST_KEYS = ("methodRedirects", "fieldRedirects", "callSiteAdaptations", "constructorRedirects",
             "signatureAdaptations", "bodyRedirects", "methodRenames", "superclassReplacements",
             "mixinCallbackAdaptations", "mixinClassReplacements", "mixinConfigAdditions",
             "mixinStrips", "registrationKeys", "insertBeforeCalls")


def collect(rules_dir: Path):
    rules = []
    for f in sorted(rules_dir.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for kind in LIST_KEYS:
            for e in data.get(kind) or []:
                # Different rule kinds carry their justification in different fields:
                # evidence/risk for redirect-style rules, reason for mixin strips, value/why for
                # config additions. Judging only `evidence` produced six false alarms.
                texts = [str(e.get(k) or "").strip() for k in
                         ("evidence", "risk", "reason", "why", "value")]
                rules.append({"file": f.name, "kind": kind, "id": e.get("id"),
                              "capability": e.get("capability"), "risk": e.get("risk"),
                              "justification": max(texts, key=len) if texts else ""})
    return rules


def evidence_corpus() -> str:
    """Every run README and result, concatenated - used to tell whether a rule is mentioned."""
    blob = []
    for p in ROOT.joinpath("runs").rglob("*"):
        if p.is_file() and p.suffix in (".md", ".json", ".txt"):
            try:
                blob.append(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    return "\n".join(blob)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rules-dir", default="rules/fabric-1.21.1")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    rules_dir = Path(args.rules_dir)
    if not rules_dir.is_absolute():
        rules_dir = ROOT / rules_dir
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(rules_dir.glob("*.json"))
    if not files:
        print(f"no rule files under {rules_dir}", file=sys.stderr)
        return 2

    rules = collect(rules_dir)
    corpus = evidence_corpus()

    by_capability = collections.Counter(r["capability"] or "<none>" for r in rules)
    clustered = {cap: count for cap, count in by_capability.items() if count > 1}
    no_evidence = [r for r in rules if len(r["justification"]) < 20]
    def mentioned(rule) -> bool:
        rule_id = rule["id"]
        if rule_id and rule_id in corpus:
            return True
        # Batch rules are often evidenced by their FILE rather than by each id.
        stem = rule["file"][:-5] if rule["file"].endswith(".json") else rule["file"]
        return stem in corpus

    orphans = [rule for rule in rules if not mentioned(rule)]
    no_id = [r for r in rules if not r["id"]]
    by_kind = collections.Counter(r["kind"] for r in rules)

    print(f"{rules_dir.name}: {len(rules)} rules in {len(files)} files")
    print("  kinds:", dict(by_kind))
    print(f"  capabilities: {len(by_capability)} distinct, {len(clustered)} used by >1 rule")
    for cap, count in sorted(clustered.items(), key=lambda kv: -kv[1])[:8]:
        print(f"    {count:3}  {cap}")
    print(f"  rules without >=20 chars of justification: {len(no_evidence)}")
    for r in no_evidence[:8]:
        print(f"    {r['id'] or '<no id>':44} {r['file']}")
    print(f"  rules never mentioned in runs/: {len(orphans)}")
    for r in orphans[:12]:
        print(f"    {r['id']:44} {r['file']} [{r['kind']}]")
    print(f"  rules without an id: {len(no_id)}")

    checks = [
        {"id": "every-rule-has-an-id", "expect": 0, "got": len(no_id)},
        {"id": "every-rule-has-justification", "expect": 0, "got": len(no_evidence)},
        {"id": "no-orphan-rules", "expect": 0, "got": len(orphans)},
    ]
    for c in checks:
        c["passed"] = c["got"] == c["expect"]

    result = {
        "workstream": "audit of the 1.21.1 rule package for history leftovers",
        "rulesDir": rules_dir.relative_to(ROOT).as_posix(),
        "ruleFiles": len(files),
        "ruleCount": len(rules),
        "kinds": dict(by_kind),
        "capabilityClusters": clustered,
        "noJustification": [{"id": r["id"], "file": r["file"]} for r in no_evidence],
        "orphans": [{"id": r["id"], "file": r["file"], "kind": r["kind"]} for r in orphans],
        "noId": [r["file"] for r in no_id],
        "checks": checks,
        "note": "an orphan rule is not necessarily wrong: it may have been added ahead of its"
                " evidence, or its evidence may cite a mod name instead of the rule id. This"
                " report is an inventory, not a delete list.",
        "scope": "read-only: no rule was changed or removed",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\naudit -> {out / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
