"""Print a compact summary of a mcbridge1201 plan.json (P0 inspection helper)."""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "runs/p0-fabric-target/plan.json"
detail = sys.argv[2] if len(sys.argv) > 2 else None

plan = json.load(open(path, encoding="utf-8"))
print(f"target {plan['target']['minecraft']} / {plan['target']['loader']}  classes={plan['target']['indexClasses']} members={plan['target']['indexMembers']}")
for a in plan["artifacts"]:
    c = a["counts"]
    hard = c["missingClass"] + c["missingMember"] + c["descMismatch"] + c["missingApiClass"] + c["missingApiMember"]
    print(f"{a['file'][:44]:46} {a['verdict']:26} confirmed {c['missingConfirmedInSource']:3}/{hard:3} "
          f"unmapped={c['unmappedNamespaceRefs']:5} wrongLoader={c['wrongLoaderNamespace']:4} "
          f"mixinMiss={c['mixinTargetsUnresolved']:3} ext={c['externalPackages']}")

if detail:
    for a in plan["artifacts"]:
        if detail not in a["file"]:
            continue
        print(f"\n===== {a['file']} ({a['verdict']}) classes={a['classes']} signed={a['signed']} mixins={a['mixins']}")
        for k in ("missingClass", "missingMember", "descMismatch", "missingApiClass", "missingApiMember", "wrongLoaderNamespace"):
            items = a.get(k) or []
            print(f"-- {k}: {len(items)}")
            for it in items[:8]:
                print(f"   {it['owner']} {it.get('name','')} {(it.get('desc') or '')[:60]} refs={it['refs']} "
                      f"src={it.get('presentInSource')} {it.get('note','')}")
