#!/usr/bin/env python3
"""Measure the 1.21.4 registration-key gap on real inputs, without converting anything.

Minecraft 1.21.2 made block/item settings pre-compute registry keys: an `Item.Settings` that was
never given one fails at registry time with `NullPointerException: Item id not set`. That is a
*missing call*, which is exactly the class of breakage a call-site rule cannot express - there is
no wrong reference to rewrite, only an absent one.

This tool measures the shape of the problem instead of guessing at it:

* counts the classes in a 1.20.1 jar that call `Registry.register` (class_2378.method_10230),
* counts the classes that build an `Item.Settings` (class_1792$class_1793),
* reports the overlap - the classes where a converter would have to inject the key,
* checks that the 1.21.4 target actually offers the setter it would inject
  (class_1792$class_1793.method_63686 takes a RegistryKey<Item>),
* checks the 1.20.1 source does NOT already call any such setter.

    python tools/scan_registration_sites.py
    python tools/scan_registration_sites.py --jar work/corpus/.../x.jar --jar ...

Exit codes: 0 measured, 2 a required input is missing.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "runs" / "p248-registry-key-gap"

# 1.20.1 intermediary names this measurement is written against.
REGISTER = (b"net/minecraft/class_2378", b"method_10230")
REGISTRIES_ITEM = (b"class_7923", b"field_41178")
SETTINGS = b"net/minecraft/class_1792$class_1793"
ITEM = b"net/minecraft/class_1792"
BLOCK_SETTINGS = b"net/minecraft/class_4970$class_4971"
ENTITY_BUILDER = (b"class_1299$class_1300",)

# The 1.21.4 side: the setter that has to be injected. Verified by reading the target stub.
TARGET_SETTINGS_CLASS = "net/minecraft/class_1792$class_1793.class"
TARGET_SETTER = b"method_63686"          # Settings.registryKey(RegistryKey<Item>)
TARGET_SETTER_SIG = b"(Lnet/minecraft/class_5321;)Lnet/minecraft/class_1792$class_1793;"
SOURCE_SETTERS = [b"method_63686", b"method_60745"]  # neither may appear in a 1.20.1 source


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_classes(zf: zipfile.ZipFile, prefix: str = ""):
    """Every .class entry of this zip; nested jars are reported separately, not inlined."""
    for name in zf.namelist():
        if name.endswith(".class"):
            yield prefix + name, zf.read(name)


def nested_jars(zf: zipfile.ZipFile):
    for name in zf.namelist():
        if name.startswith("META-INF/jars/") and name.endswith(".jar"):
            yield name, zf.read(name)


def count_patterns(data: bytes) -> dict:
    """What a class does about registration, judged from its constant pool."""
    direct = any(
        data.count(cls) and data.count(mth)
        for cls, mth in ((b"net/minecraft/class_2378", b"method_10230"),
                         (b"net/minecraft/class_2378", b"method_10226"),
                         (b"net/minecraft/class_2378", b"method_39197"))
    )
    wrapper = data.count(b"ResourcefulRegistries") > 0 or (
        data.count(b"common/registry") and data.count(b"create"))
    return {
        "directRegister": bool(direct),
        "registryWrapper": bool(wrapper),
        "buildsItemSettings": SETTINGS in data,
        "buildsBlockSettings": BLOCK_SETTINGS in data,
        "buildsEntityType": all(tok in data for tok in ENTITY_BUILDER),
        "touchesRegistriesItem": REGISTRIES_ITEM[0] in data and REGISTRIES_ITEM[1] in data,
        "callsTargetSetter": any(tok in data for tok in SOURCE_SETTERS),
    }


def scan_zip(zf: zipfile.ZipFile, label: str, out: dict) -> None:
    for name, data in iter_classes(zf, label):
        out["classes"] += 1
        f = count_patterns(data)
        if f["directRegister"]:
            out["directRegister"].append(name)
        if f["registryWrapper"]:
            out["registryWrapper"].append(name)
        if f["buildsItemSettings"]:
            out["itemSettings"].append(name)
        if f["buildsBlockSettings"]:
            out["blockSettings"].append(name)
        if f["buildsEntityType"]:
            out["entityType"].append(name)
        if f["touchesRegistriesItem"]:
            out["registriesItem"].append(name)
        if f["callsTargetSetter"]:
            out["alreadySetter"].append(name)


def blank() -> dict:
    return {k: [] for k in ("directRegister", "registryWrapper", "itemSettings", "blockSettings",
                            "entityType", "registriesItem", "alreadySetter")} | {"classes": 0}


def scan_jar(jar: Path) -> dict:
    out = blank()
    nested = []
    with zipfile.ZipFile(jar) as z:
        scan_zip(z, "", out)
        for name, data in nested_jars(z):
            inner = blank()
            with zipfile.ZipFile(io.BytesIO(data)) as iz:
                scan_zip(iz, name + "!/", inner)
            nested.append({"entry": name, "sha256": hashlib.sha256(data).hexdigest(),
                           **{k: len(v) for k, v in inner.items() if k != "classes"},
                           "classes": inner["classes"],
                           "directRegisterClasses": inner["directRegister"][:10],
                           "itemSettingsClasses": inner["itemSettings"][:10]})
            for k, v in inner.items():
                if k == "classes":
                    out["classes"] += v
                else:
                    out[k].extend(v)
    gap = sorted(set(out["directRegister"]) | set(out["registryWrapper"]))
    gap = sorted(set(gap) & (set(out["itemSettings"]) | set(out["blockSettings"])))
    return {
        "jar": jar.relative_to(ROOT).as_posix() if jar.is_relative_to(ROOT) else str(jar),
        "sha256": sha256(jar),
        "classes": out["classes"],
        "callsRegister": len(out["directRegister"]),
        "usesRegistryWrapper": len(out["registryWrapper"]),
        "buildsItemSettings": len(out["itemSettings"]),
        "touchesRegistriesItem": len(out["registriesItem"]),
        "buildsBlockSettings": len(out["blockSettings"]),
        "buildsEntityType": len(out["entityType"]),
        "alreadyCallsTargetSetter": len(out["alreadySetter"]),
        "gapClasses": gap,
        "nestedJars": nested,
        "_register": out["directRegister"],
        "_wrapper": out["registryWrapper"],
        "_settings": out["itemSettings"],
        "_blockSettings": out["blockSettings"],
        "_entity": out["entityType"],
        "_existingSetter": out["alreadySetter"],
    }


def target_api(stub: Path) -> dict:
    """Read the 1.21.4 settings class and report whether the setter we would inject exists."""
    with zipfile.ZipFile(stub) as z:
        if TARGET_SETTINGS_CLASS not in z.namelist():
            return {"present": False, "reason": f"{TARGET_SETTINGS_CLASS} not in the stub"}
        data = z.read(TARGET_SETTINGS_CLASS)
    return {
        "present": True,
        "class": TARGET_SETTINGS_CLASS,
        "hasRegistryKeySetter": TARGET_SETTER in data,
        "setterName": TARGET_SETTER.decode(),
        "setterDescriptor": TARGET_SETTER_SIG.decode() if TARGET_SETTER_SIG in data else None,
        "descriptorVisibleInConstantPool": TARGET_SETTER_SIG in data,
    }


RULE_DRAFT = {
    "status": "draft_only_not_implemented",
    "why_not_a_callSiteAdaptation": "There is no wrong call to rewrite: 1.20.1 code never calls a"
                                    " registry-key setter, so a call-site rule has nothing to match."
                                    " The key has to be injected between 'new Settings()' and"
                                    " 'new Item(settings)', using an id that is usually a separate"
                                    " static field read at the register call.",
    "why_not_a_constructorRedirect": "constructorRedirects replace one constructor call with a"
                                     " factory that receives the same arguments. The registry key is"
                                     " not among those arguments; it has to be recovered from the"
                                     " registry id passed to a later call in the same method.",
    "proposed_shape": {
        "kind": "registrationSiteRewrite",
        "match": {
            "registerCall": "class_2378.method_10230(registry, id, value)",
            "valueConstruction": "value is a fresh instance whose constructor took a Settings"
                                 " built in the same method",
        },
        "rewrite": "emit bridge call RegistrationKeyBridge.register(registry, id, supplier) where the"
                   " supplier builds the value with settings.method_63686(RegistryKey.of(RegistryKeys.ITEM, id))",
        "requires": [
            "a bridge that accepts a factory instead of an instance",
            "identity of the registry (item/block/entity) to pick RegistryKeys.*",
            "a decision for values that are not constructed inline (field holders)",
        ],
        "prerequisite": "A bytecode data-flow pass that ties the register call to the construction"
                        " it registers; the current rule engine matches single call sites.",
    },
    "verification_plan": "Patch the fixture, then assert: the patched class calls method_63686 before"
                         " class_1792.<init>; a 1.21.4 boot does not raise 'Item id not set'. Only the"
                         " first half is possible without a game instance.",
}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jar", action="append", default=[],
                    help="1.20.1 jar to scan (repeatable); defaults to the fixture and ironchests")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    jars = [Path(p) for p in args.jar] if args.jar else [
        ROOT / "fixtures/source-fabric-1.20.1/out/mcbfixture-1.0.0.jar",
        ROOT / "work/corpus/ironchests/ironchests-5.0.2-fabric.jar",
    ]
    stub = ROOT / "work/target/client-1.21.4-intermediary.jar"
    for j in jars:
        if not j.is_file():
            print(f"missing input jar: {j}", file=sys.stderr)
            return 2
    if not stub.is_file():
        print(f"missing 1.21.4 stub: {stub}", file=sys.stderr)
        return 2

    scans = []
    for j in jars:
        s = scan_jar(j)
        scans.append(s)
        print(f"{s['jar']}: classes={s['classes']} directRegister={s['callsRegister']}"
              f" wrapper={s['usesRegistryWrapper']}"
              f" itemSettings={s['buildsItemSettings']} blockSettings={s['buildsBlockSettings']}"
              f" entityType={s['buildsEntityType']} gap={len(s['gapClasses'])}"
              f" alreadySetter={s['alreadyCallsTargetSetter']}")

    api = target_api(stub)
    print(f"1.21.4 target settings: present={api.get('present')}"
          f" setter={api.get('hasRegistryKeySetter')} desc={api.get('setterDescriptor')}")

    checks = [
        {"id": "target-has-registry-key-setter", "expect": True,
         "got": api.get("hasRegistryKeySetter"),
         "why": "the setter the converter would inject must exist in the target"},
        {"id": "target-setter-takes-registry-key", "expect": True,
         "got": api.get("descriptorVisibleInConstantPool"),
         "why": "the descriptor must be the RegistryKey overload, not an unrelated method"},
        {"id": "source-never-calls-it", "expect": 0,
         "got": sum(s["alreadyCallsTargetSetter"] for s in scans),
         "why": "a 1.20.1 source calling a 1.21.4-only setter would mean the sample is not 1.20.1"},
        {"id": "gap-exists-in-at-least-one-input", "expect": ">=1",
         "got": sum(len(s["gapClasses"]) for s in scans),
         "why": "if no class both registers and builds settings, the fixture does not exercise it"},
    ]
    passed = all(c["got"] == c["expect"] if c["expect"] != ">=1" else c["got"] >= 1 for c in checks)

    public = [{k: v for k, v in s.items() if not k.startswith("_")} for s in scans]
    result = {
        "workstream": "B03 pre-work: measure the 1.21.4 registration-key gap",
        "target": {"profile": "targets/fabric-1.21.4.json",
                   "stub": "work/target/client-1.21.4-intermediary.jar",
                   "api": api},
        "inputs": public,
        "gapDetail": {s["jar"]: {"directRegister": s["_register"],
                                 "registryWrapper": s["_wrapper"],
                                 "itemSettings": s["_settings"],
                                 "blockSettings": s["_blockSettings"],
                                 "entityType": s["_entity"],
                                 "overlap": s["gapClasses"]} for s in scans},
        "checks": checks,
        "ruleDraft": RULE_DRAFT,
        "passed": passed,
        "scope": "measurement only. Nothing was converted, no rule was written, no game was"
                 " launched: this locates the shape of the gap, it does not close it.",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    for c in checks:
        print(f"{'PASS' if (c['got'] == c['expect'] if c['expect'] != '>=1' else c['got'] >= 1) else 'FAIL'} {c['id']}")
    print(f"\nregistration-key gap: {'PASS' if passed else 'FAIL'} -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
