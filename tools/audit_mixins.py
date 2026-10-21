#!/usr/bin/env python3
"""Audit mixin configs inside a jar.

Two failure modes are checked:

1. a class listed in a mixin config is missing from the jar;
2. a class annotated with @Mixin lives in the mixin package but is not listed in any config - the
   signature of the conversion stripping dead mixin entries (FerriteCore fastmap/mrl, AppleSkin
   ItemStackMixin, Shulker ItemStackMixin).

Mixin configs may spell sub-package entries with dots (``client.fabric.ItemStackMixin``); both the
dotted and slashed forms are resolved. Non-mixin helpers and ``Config`` plugin classes are ignored.

Exit code is non-zero when either problem is found, unless --allow-inert is given.
"""
import argparse
import json
import sys
import zipfile

CONFIG_SUFFIXES = (".mixins.json", ".mixin.json")
MIXIN_ANNOTATION = b"Lorg/spongepowered/asm/mixin/Mixin;"


def load_configs(zf):
    """Return (configs, errors); a broken config is a failure, not a skip."""
    configs = []
    errors = []
    for name in zf.namelist():
        if name.endswith(CONFIG_SUFFIXES) and "/" not in name:
            try:
                data = json.loads(zf.read(name).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001 - collected and counted as a problem
                print(f"CONFIG_ERROR {name}: {exc}")
                errors.append(name)
                continue
            configs.append((name, data))
    return configs, errors


def resolve_class(zf, package, rel):
    for candidate in (rel, rel.replace(".", "/")):
        path = f"{package}/{candidate}.class" if package else f"{candidate}.class"
        if path in zf.namelist():
            return path
    return None


def audit(jar, allow_inert):
    zf = zipfile.ZipFile(jar)
    configs, config_errors = load_configs(zf)
    listed = {}
    packages = set()
    problems = len(config_errors)
    for name, data in configs:
        package = data.get("package", "").replace(".", "/")
        if package:
            packages.add(package)
        for section in ("mixins", "client", "server"):
            for rel in data.get(section, []):
                path = resolve_class(zf, package, rel)
                key = path or f"{package}/{rel}.class"
                listed[key] = (name, section)
                if path is None:
                    problems += 1
                    print(f"MISSING {package}/{rel}.class (listed in {name}:{section})")
    inert = []
    for path in zf.namelist():
        if not path.endswith(".class") or "$" in path:
            continue
        fqcn = path[:-6]
        if not any(fqcn.startswith(pkg + "/") for pkg in packages):
            continue
        if path in listed or fqcn.endswith("/Config"):
            continue
        if MIXIN_ANNOTATION in zf.read(path):
            inert.append(path)
    for path in sorted(inert):
        if not allow_inert:
            problems += 1
        print(f"INERT {path} (mixin in mixin package, not listed in any config)")
    print(f"jar={jar} configs={len(configs)} config_errors={len(config_errors)} "
          f"listed={len(listed)} inert={len(inert)} problems={problems}")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit mixin configs for missing or inert classes")
    ap.add_argument("--jar", action="append", required=True)
    ap.add_argument("--allow-inert", action="store_true")
    args = ap.parse_args(argv)
    problems = 0
    for jar in args.jar:
        problems += audit(jar, args.allow_inert)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
