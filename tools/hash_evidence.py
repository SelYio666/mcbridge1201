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
    "runs/p6-lithium/server.log",
    "runs/p6-contract-recheck/verdict.json",
    "runs/p7-degradation-probe/server.log",
    "runs/p7-contract-recheck/verdict.json",
    "runs/p10-lithium-signature/README.md",
    "runs/p10-lithium-signature/verdict.json",
    "runs/p10-lithium-signature/patch-lithium.log",
    "runs/p10-lithium-signature/build-bridges.log",
    "runs/p10-lithium-signature/inject-bridges.log",
    "runs/p10-lithium-signature/server-callsite.log",
    "runs/p10-lithium-signature/server-callsite.result.txt",
    "runs/p10-lithium-signature/gradle-test.log",
    "runs/p10-lithium-signature/build-reports.log",
    "runs/p10-lithium-signature/remap-client-1.20.1.log",
    "runs/p10-lithium-signature/remap-client-1.21.1.log",
    "runs/p10-lithium-signature/bridge-javap.txt",
    "runs/p10-lithium-signature/ironchests-patch-recheck.log",
    "runs/p10-lithium-signature/lithium-patch-recheck.log",
    "runs/p10-lithium-signature/no-nsm-check.txt",
    "runs/p10-lithium-signature/class_14-1.20.1-body.txt",
    "runs/p10-lithium-signature/class_14-1.21.1-body.txt",
    "runs/p11-lithium-explosion/README.md",
    "runs/p11-lithium-explosion/verdict.json",
    "runs/p11-lithium-explosion/patch-lithium.log",
    "runs/p11-lithium-explosion/patch-lithium2.log",
    "runs/p11-lithium-explosion/patch-lithium3.log",
    "runs/p11-lithium-explosion/patch-lithium-recheck.log",
    "runs/p11-lithium-explosion/server-explosion.log",
    "runs/p11-lithium-explosion/server-explosion2.log",
    "runs/p11-lithium-explosion/server-explosion3.log",
    "runs/p11-lithium-explosion/server-readd.log",
    "runs/p11-lithium-explosion/server-chunkholder-local.log",
    "runs/p11-lithium-explosion/server-chunkholder-local2.log",
    "runs/p11-lithium-explosion/ironchests-patch-recheck.log",
    "runs/p11-lithium-explosion/gradle-test.log",
    "runs/p11-lithium-explosion/gradle-install.log",
    "work/cb/out/lithium/lithium-patched-explosion3.jar",
    "runs/p12-chunk-access/README.md",
    "runs/p13-chunk-port/README.md",
    "runs/p13-chunk-port/verdict.json",
    "runs/p13-chunk-port/patch-lithium-chunkport.log",
    "runs/p13-chunk-port/patch-lithium-chunkport-recheck.log",
    "runs/p13-chunk-port/build-bridges.log",
    "runs/p13-chunk-port/build-mixins.log",
    "runs/p13-chunk-port/gradle-test.log",
    "runs/p13-chunk-port/gradle-install.log",
    "runs/p13-chunk-port/server-chunkport-rule.log",
    "runs/p13-chunk-port/server-chunkport-commands.log",
    "runs/p13-chunk-port/server-chunk-port.log",
    "runs/p13-chunk-port/server-chunk-port2.log",
    "runs/p13-chunk-port/ironchests-patch-recheck.log",
    "runs/p13-chunk-port/build-reports.log",
    "work/cb/out/lithium/lithium-patched-chunkport.jar",
    "runs/p15-trashslot/README.md",
    "runs/p15-trashslot/convert.log",
    "runs/p15-trashslot/convert-balm.log",
    "runs/p15-trashslot/inject-aw-balm.log",
    "runs/p15-trashslot/patch.log",
    "runs/p15-trashslot/build-bridges.log",
    "runs/p15-trashslot/server-trashslot.log",
    "runs/p15-trashslot/server-trashslot2.log",
    "runs/p15-trashslot/server-trashslot3.log",
    "runs/p15-trashslot/gradle-test.log",
    "work/cb/out/trashslot/trashslot-patched.jar",
    "rules/fabric-1.21.1/trashslot.json",
    "runs/p16-balm/README.md",
    "runs/p16-balm/patch.log",
    "runs/p16-balm/build-bridges.log",
    "runs/p16-balm/inject-aw-trashslot.log",
    "runs/p16-balm/server-balm.log",
    "runs/p16-balm/server-balm2.log",
    "work/cb/out/trashslot/trashslot-patched-balm.jar",
    "work/cb/out/trashslot/trashslot-patched-balm-aw.jar",
    "runs/p17-balm-net/README.md",
    "runs/p17-balm-net/verdict.json",
    "runs/p17-balm-net/patch2.log",
    "runs/p17-balm-net/inject-aw2.log",
    "runs/p17-balm-net/build-bridges.log",
    "runs/p17-balm-net/server-net.log",
    "runs/p17-balm-net/server-net2.log",
    "work/cb/out/trashslot/trashslot-patched-net2-aw.jar",
    "runs/p18-nested-bridges/README.md",
    "runs/p18-nested-bridges/gradle-test.log",
    "runs/p18-nested-bridges/install-dist.log",
    "runs/p18-nested-bridges/ironchests-repatch3.log",
    "runs/p18-nested-bridges/inject-aw.log",
    "runs/p18-nested-bridges/server-nested.log",
    "runs/p18-nested-bridges/contract.log",
    "runs/p18-nested-bridges/contract/verdict.json",
    "work/tmp/p18/ironchests-repatch3.jar",
    "work/tmp/p18/ironchests-repatch3-aw.jar",
    "runs/p14-lithium-ironchests/README.md",
    "runs/p14-lithium-ironchests/verdict.json",
    "runs/p14-lithium-ironchests/step1-place-insert.log",
    "runs/p14-lithium-ironchests/step2-restart-read.log",
    "runs/p14-lithium-ironchests/run.txt",
    "runs/p14-lithium-ironchests/build-reports.log",
    "runs/p14-lithium-ironchests/hash-evidence.log",
    "work/cb/out/lithium/lithium-patched-final.jar",
    "rules/fabric-1.21.1/lithium.json",
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
    "profiles/ironchests-5.0.2-fabric__fabric-1.21.1.json",
    "docs/support-matrix.md",
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
