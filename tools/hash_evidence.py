"""Record SHA-256 for the evidence artifacts produced by P0 (docs + manifests)."""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    "runs/p0-fabric-target/plan.json",
    "docs/generated/static-matrix-fabric-1.21.1.md",
    "work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1.jar",
    "work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1-patched.jar",
    "runs/p2-server-ironchests-rule1/server.log",
    "runs/p2-server-ironchests-rule2/server.log",
    "work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1-aw.jar",
    "runs/p3-server-accesswidener/server.log",
    "runs/p4-contract-place/server.log",
    "runs/p4-contract-restart/server.log",
    "runs/p4-contract-vanilla-control/server.log",
    "runs/p5-contract-nbt-fix/server.log",
    "runs/p5-contract-nbt-restart/server.log",
    "runs/p5-contract-script/verdict.json",
    "runs/p5-contract-script/step1-place-insert.log",
    "runs/p5-contract-script/step2-restart-read.log",
    "work/cb/out/ironchests/report.md",
    "work/cb/out/ironchests/full-audit.tsv",
    "work/remap/server-intermediary.jar",
    "runs/p1-server-baseline/server.log",
    "runs/p1-server-baseline/server-baseline.log",
    "runs/p1-server-baseline/server-rerun.log",
    "runs/p1-server-converted-ironchests/server.log",
    "runs/p0-server-baseline/server.log",
    "runs/p0-server-baseline/server-l016.log",
    "runs/p0-server-baseline/server-outside.log",
    "work/evidence/doctor.json",
    "manifests/corpus.json",
    "manifests/environment.lock.json",
    "manifests/upstream.lock.json",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    lines = []
    for rel in FILES:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if os.path.exists(p):
            lines.append(f"{sha256(p)}  {rel}")
        else:
            lines.append(f"{'MISSING':64}  {rel}")
    out = os.path.join(ROOT, "runs", "SHA256SUMS.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
