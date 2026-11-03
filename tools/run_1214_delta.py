#!/usr/bin/env python3
"""B01: freeze-correct 1.21.4 delta classification against the 1.21.1 baseline.

What this produces, and what it deliberately does not:

* It diffs the *same* 1.20.1 inputs (the pinned fixture and a real sample) against the 1.21.1 and
  the 1.21.4 indexes, then classifies every difference into "newly broken in 1.21.4", "already
  broken in 1.21.1" and "resolved". That classification is measured, not read from a blog.
* It carries the official 1.21.2/1.21.3 and 1.21.4 modder-facing change lists as data, each item
  marked with whether bytecode-level analysis can see it. Those flags are judgement, and the
  report says so.
* It does NOT claim any of it converts. There is no 1.21.4 rule package and no game was launched.

    python tools/run_1214_delta.py
    python tools/run_1214_delta.py --out runs/p247-fabric-1.21.4-delta
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "source-fabric-1.20.1" / "out" / "mcbfixture-1.0.0.jar"
SAMPLE = ROOT / "work" / "corpus" / "ironchests" / "ironchests-5.0.2-fabric.jar"
DEFAULT_OUT = ROOT / "runs" / "p247-fabric-1.21.4-delta"
PROFILE_1214 = ROOT / "targets" / "fabric-1.21.4.json"

# (label, client jar, mappings, api jar, java major)
ENVS = {
    "1.21.1": ("work/target/client-1.21.1.jar", "work/target/intermediary-1.21.1-v2.jar",
               "work/target/fabric-loader-0.19.5.jar", 21),
    "1.21.4": ("work/target/client-1.21.4.jar", "work/target/intermediary-1.21.4-v2.jar",
               "work/target/fabric-loader-0.16.14.jar", 21),
}

# The official modder-facing changes, as data. `staticDetectable` is this run's judgement:
# "yes" = a bytecode/member diff can see the break, "partial" = only some shapes are visible,
# "no" = it is a runtime/protocol/asset behaviour that references cannot show.
OFFICIAL = [
    # 1.21.2 / 1.21.3
    {"id": "1212.registry-key-settings", "version": "1.21.2", "area": "registration",
     "summary": "Block/Item settings must carry a RegistryKey; missing it fails with"
                " 'NullPointerException: Item id not set' at registry time.",
     "staticDetectable": "partial",
     "why": "The call to Settings#registryKey is a member reference and is visible, but its"
            " absence is a call that was never emitted: nothing in the bytecode says it is required."},
    {"id": "1212.serverworld-params", "version": "1.21.2", "area": "api-shape",
     "summary": "Server-only methods now take ServerWorld explicitly; callers must pass it instead"
                " of casting.",
     "staticDetectable": "yes",
     "why": "The descriptor of the called method changes, so an exact-match site either misses or"
            " needs a call-site adaptation."},
    {"id": "1212.action-result-merge", "version": "1.21.2", "area": "api-shape",
     "summary": "ActionResult / ItemActionResult / TypedActionResult merged into ActionResult.",
     "staticDetectable": "yes",
     "why": "Return types and static factory owners change: member lookups fail or need bridges."},
    {"id": "1212.entity-render-state", "version": "1.21.2", "area": "rendering",
     "summary": "EntityRenderer gains a render-state type parameter; createRenderState /"
                " updateRenderState split rendering data from the entity instance.",
     "staticDetectable": "yes",
     "why": "The renderer's method set and descriptors change. Whether the ported renderer still"
            " looks right is NOT visible here."},
    {"id": "1212.registry-rename", "version": "1.21.2", "area": "api-shape",
     "summary": "Registry implements RegistryEntryLookup: getEntry->getOptional, entryOf->getOrThrow,"
                " getOrThrow->getValueOrThrow, and siblings.",
     "staticDetectable": "yes",
     "why": "Method names change; exact-match lookups miss."},
    {"id": "1212.recipes-rework", "version": "1.21.2", "area": "data",
     "summary": "Recipes keyed by RegistryKey; Recipe/ID server-side only; clients get"
                " RecipeDisplayEntry with NetworkRecipeId.",
     "staticDetectable": "partial",
     "why": "Method signatures move, but the client/server split is a protocol change: a signature"
            " that still resolves can still be wrong at runtime."},
    {"id": "1212.ingredient-list", "version": "1.21.2", "area": "data",
     "summary": "Ingredient is internally a list of items, not item stacks.",
     "staticDetectable": "partial",
     "why": "Type stays Ingredient, so only calls that read stacks reveal it."},
    {"id": "1212.profiler", "version": "1.21.2", "area": "api-shape",
     "summary": "Shared profiler is accessed through Profilers#get instead of world.getProfiler().",
     "staticDetectable": "yes", "why": "Call owner/descriptor change."},
    {"id": "1212.attribute-prefix", "version": "1.21.2", "area": "api-shape",
     "summary": "EntityAttributes constants drop the GENERIC prefix and their identifiers change.",
     "staticDetectable": "yes", "why": "Static field names change; references miss."},
    {"id": "1212.loot-tables-empty", "version": "1.21.2", "area": "data",
     "summary": "LootTables#EMPTY removed; absence is Optional now.",
     "staticDetectable": "yes", "why": "Field reference disappears."},
    {"id": "1212.fuel-event", "version": "1.21.2", "area": "registration",
     "summary": "Furnace fuels register through FuelRegistryEvents.BUILD with a context."
                " FuelRegistry.INSTANCE.add is gone.",
     "staticDetectable": "yes", "why": "Owner/API type change."},
    {"id": "1212.entity-type-key", "version": "1.21.2", "area": "registration",
     "summary": "EntityType.Builder#build now requires a RegistryKey; the no-arg build injected by"
                " FabricEntityTypeBuilder was removed.",
     "staticDetectable": "yes", "why": "Descriptor change on build()."},
    {"id": "1212.spawn-reason", "version": "1.21.2", "area": "api-shape",
     "summary": "Creating an entity requires a SpawnReason.",
     "staticDetectable": "yes", "why": "Descriptor change on create()."},
    {"id": "1212.datagen-recipe-generator", "version": "1.21.2", "area": "datagen",
     "summary": "Recipe providers override getRecipeGenerator instead of generate.",
     "staticDetectable": "yes", "why": "Override signature changes; the override silently stops"
                                        " being called if it is not migrated."},
    # 1.21.4
    {"id": "1214.item-model-definitions", "version": "1.21.4", "area": "resources",
     "summary": "Items use assets/<ns>/items/*.json model definitions; ItemColors and related"
                " tinting APIs were removed.",
     "staticDetectable": "partial",
     "why": "Removed Java APIs are visible; a missing JSON asset is only visible to a resource"
            " scan, and a model that loads but looks wrong is not visible to either."},
    {"id": "1214.block-model-render-type", "version": "1.21.4", "area": "rendering",
     "summary": "BlockEntity#getRenderType is gone: every block entity renders its block model.",
     "staticDetectable": "yes", "why": "The override target disappears from the target index."},
    {"id": "1214.model-loading-split", "version": "1.21.4", "area": "rendering",
     "summary": "Model Loading API split into static vs block models; BeforeBake/AfterBake removed;"
                " GroupableModel no longer extends UnbakedModel.",
     "staticDetectable": "yes", "why": "Types and callback interfaces change."},
    {"id": "1214.pick-block-server-side", "version": "1.21.4", "area": "network",
     "summary": "Pick Block moved from client to logical server; client callbacks replaced by"
                " PlayerPickItemEvents.",
     "staticDetectable": "partial",
     "why": "The client callback API is visible when it is removed; whether a mod's pick logic is"
            " now on the right side is a runtime question."},
    {"id": "1214.custom-ingredient-stream", "version": "1.21.4", "area": "api-shape",
     "summary": "CustomIngredient#getMatchingStacks returns a stream, not a list.",
     "staticDetectable": "yes", "why": "Return type change on an override."},
    {"id": "1214.equipment-path", "version": "1.21.4", "area": "resources",
     "summary": "Equipment assets moved from models/equipment to assets/<ns>/equipment; several"
                " tags removed; slot outline textures moved.",
     "staticDetectable": "no",
     "why": "Pure asset layout: no bytecode reference points at a resource path that can be"
            " checked without a resource scan and a visual comparison."},
    {"id": "1214.rendering-v0-removed", "version": "1.21.4", "area": "api-shape",
     "summary": "fabric-rendering-v0 and FabricModelPredicateProviderRegistry removed;"
                " BuiltinItemRenderer replaced by SpecialModelTypes.ID_MAPPER access widener.",
     "staticDetectable": "yes", "why": "Removed API classes are visible in the API index."},
]


def ensure_java_home() -> str | None:
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / "java.exe").exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "java.exe").exists():
            os.environ["JAVA_HOME"] = str(cand)
            return str(cand)
    return None


def cli_path() -> Path | None:
    base = ROOT / "java" / "build" / "install" / "mcbridge1201" / "bin"
    p = base / ("mcbridge1201.bat" if os.name == "nt" else "mcbridge1201")
    return p if p.exists() else None


def run(cmd: list, timeout=1800) -> tuple[int, str]:
    p = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def class_majors(jar: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            if not name.endswith(".class"):
                continue
            head = z.read(name)[:8]
            if len(head) >= 8:
                major = (head[6] << 8) | head[7]
                counts[major] = counts.get(major, 0) + 1
    return counts


def key_of(item: dict) -> str:
    return "|".join(str(item.get(k) or "") for k in ("kind", "owner", "name", "desc"))


def analyze(cli: Path, mods: Path, env: str, out_json: Path) -> tuple[int, dict]:
    client, mappings, api, _java = ENVS[env]
    rc, text = run([cli, "analyze", "--mods", mods,
                    "--client-jar", client, "--mappings", mappings,
                    "--api", api, "--target", env, "--out", out_json])
    data = json.loads(out_json.read_text(encoding="utf-8")) if out_json.is_file() else {}
    return rc, {"rc": rc, "plan": data, "tail": text.strip().splitlines()[-2:]}


def flatten(plan: dict) -> dict:
    """Collect every missing/mismatch item of one artifact under one key set."""
    out = {}
    for art in plan.get("artifacts") or []:
        for field in ("missingClass", "missingMember", "descMismatch", "missingApiClass"):
            for item in art.get(field) or []:
                k = key_of(item)
                out[k] = {"field": field, "owner": item.get("owner"), "name": item.get("name"),
                          "desc": item.get("desc"), "kind": item.get("kind")}
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    java_home = ensure_java_home()
    cli = cli_path()
    if java_home is None or cli is None:
        write_json(out / "result.json", {"passed": False, "skipped": True,
                                         "reason": "need a JDK and the built CLI (gradle installDist)"})
        print("SKIP: need JDK + CLI", file=sys.stderr)
        return 2

    cases = []

    def add(case_id, goal, expect, got, extra=None):
        c = {"id": case_id, "goal": goal, "expect": expect, "got": got}
        c.update(extra or {})
        cases.append(c)
        print(f"  {case_id}: {json.dumps(got, ensure_ascii=False)[:120]}")

    # ---------------------------------------------------------------- environment
    stub = ROOT / "work/target/client-1.21.4-intermediary.jar"
    majors = class_majors(stub) if stub.is_file() else {}
    add("b01.1214-stub-java21", "the 1.21.4 compile stub is readable at the target Java level",
        {"onlyMajor": 65}, {"majors": {str(k): v for k, v in majors.items()},
                            "classes": sum(majors.values())})

    json_1214 = out / "profile-check-1.21.4.json"
    rc, text = run([cli, "profile-check", "--profile", str(PROFILE_1214), "--root", ".",
                    "--json", str(json_1214)])
    codes = []
    if json_1214.is_file():
        rep = json.loads(json_1214.read_text(encoding="utf-8"))
        codes = [p["code"] for p in rep.get("problems", []) if p.get("severity") == "error"]
    add("b01.1214-no-rules-refused", "the 1.21.4 profile refuses to convert without a rule package",
        {"rc": 3, "code": "pipeline.rule-order-empty"}, {"rc": rc, "errorCodes": sorted(set(codes))})

    wrong = out / "profile-check-1.21.4-with-1211-rules.json"
    rc, text = run([cli, "profile-check", "--profile", str(PROFILE_1214), "--root", ".",
                    "--rules", "rules/fabric-1.21.1/container.json", "--json", str(wrong)])
    codes = []
    if wrong.is_file():
        rep = json.loads(wrong.read_text(encoding="utf-8"))
        codes = [p["code"] for p in rep.get("problems", []) if p.get("severity") == "error"]
    add("b01.1214-reuses-no-1211-rules", "the 1.21.1 rule package cannot be aimed at 1.21.4",
        {"rc": 3, "code": "rules.target-mismatch"}, {"rc": rc, "errorCodes": sorted(set(codes))})

    # ---------------------------------------------------------------- measured delta
    inputs = [("fixture", FIXTURE), ("ironchests-5.0.2", SAMPLE)]
    deltas = {}
    for label, jar in inputs:
        if not jar.is_file():
            deltas[label] = {"missingInput": str(jar)}
            continue
        # One directory per input: analyze scans the whole --mods directory, so sharing one would
        # merge both artifacts into every result and make the two deltas identical.
        mods_dir = out / "inputs" / label
        mods_dir.mkdir(parents=True, exist_ok=True)
        copy = mods_dir / jar.name
        if not copy.is_file():
            copy.write_bytes(jar.read_bytes())
        plans = {}
        for env_name in ("1.21.1", "1.21.4"):
            plan_path = out / f"static-{label}-{env_name}.json"
            rc, info = analyze(cli, copy.parent, env_name, plan_path)
            plans[env_name] = info
        a = flatten(plans["1.21.1"]["plan"])
        b = flatten(plans["1.21.4"]["plan"])
        new_broken = sorted(set(b) - set(a))
        resolved = sorted(set(a) - set(b))
        both = sorted(set(a) & set(b))
        deltas[label] = {
            "counts": {
                "1.21.1": len(a), "1.21.4": len(b),
                "newIn1214": len(new_broken), "resolvedIn1214": len(resolved),
                "inBoth": len(both),
            },
            "newIn1214": [b[k] for k in new_broken[:25]],
            "resolvedIn1214": [a[k] for k in resolved[:25]],
            "inBoth": [a[k] for k in both[:25]],
            "analyzeRc": {"1.21.1": plans["1.21.1"]["rc"], "1.21.4": plans["1.21.4"]["rc"]},
        }
        print(f"  delta {label}: 1.21.1={len(a)} 1.21.4={len(b)} new={len(new_broken)}"
              f" resolved={len(resolved)} both={len(both)}")

    feasible = [k for k, v in deltas.items() if "counts" in v]
    add("b01.measured-delta", "the same 1.20.1 input is diffed against both target indexes",
        {"inputsAnalysed": 2},
        {"inputsAnalysed": len(feasible), "deltas": {k: v.get("counts") for k, v in deltas.items()}})

    # ---------------------------------------------------------------- official list
    by_area = {}
    for item in OFFICIAL:
        by_area.setdefault(item["area"], []).append(item["id"])
    detectable = {"yes": 0, "partial": 0, "no": 0}
    for item in OFFICIAL:
        detectable[item["staticDetectable"]] = detectable.get(item["staticDetectable"], 0) + 1

    result = {
        "workstream": "B01 freeze the 1.21.4 environment and classify the delta",
        "environment": {
            "lock": "manifests/target-fabric-1.21.4.lock.json",
            "profile": "targets/fabric-1.21.4.json",
            "stub": "work/target/client-1.21.4-intermediary.jar",
            "javaMajor": 21,
            "classMajorMax": 65,
        },
        "baseline": {"env": "1.21.1", "indexes": ENVS["1.21.1"][:3]},
        "delta": deltas,
        "officialChanges": {
            "source": [
                "https://fabricmc.net/2024/10/14/1212.html",
                "https://fabricmc.net/2024/12/02/1214.html",
            ],
            "count": len(OFFICIAL),
            "byArea": by_area,
            "staticDetectable": detectable,
            "items": OFFICIAL,
            "caveat": "staticDetectable is this run's judgement about what a bytecode/member diff"
                      " can see. The counts in `delta` are the measurement; the flags are not.",
        },
        "cases": cases,
        "scope": "static only: two indexes were built and diffed, no jar was converted and no game"
                 " was launched. No 1.21.4 rule package exists.",
    }
    failed = []
    for c in cases:
        exp, got = c["expect"], c["got"]
        ok = True
        if "onlyMajor" in exp:
            ok = ok and list((got.get("majors") or {}).keys()) == [str(exp["onlyMajor"])]
        if "rc" in exp:
            ok = ok and got.get("rc") == exp["rc"]
        if "code" in exp:
            ok = ok and exp["code"] in (got.get("errorCodes") or [])
        if "inputsAnalysed" in exp:
            ok = ok and got.get("inputsAnalysed") == exp["inputsAnalysed"]
        c["passed"] = ok
        if not ok:
            failed.append(c["id"])

    for c in cases:
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']}")
    result["passed"] = not failed
    result["failed"] = failed
    write_json(out / "result.json", result)
    write_json(out / "official-changes.json", {"source": result["officialChanges"]["source"],
                                               "items": OFFICIAL})
    print(f"\nB01 delta: {'PASS' if not failed else 'FAIL'} ({len(cases) - len(failed)}/{len(cases)})"
          f" -> {out / 'result.json'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
