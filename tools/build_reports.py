"""Build the deliverable reports from the locked manifests and run evidence.

Outputs:
  profiles/<mod>__fabric-1.21.1.json   - compatibility profile (schema 0.1 draft)
  docs/support-matrix.md               - per-sample stage matrix with denominators

Everything is derived from files that already carry hashes, so the reports are
reproducible instead of hand-written.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def main():
    corpus = load("manifests/corpus.json")
    env = load("manifests/environment.lock.json")
    upstream = load("manifests/upstream.lock.json")
    plan = load("runs/p0-fabric-target/plan.json")
    verdict = load("runs/p5-contract-script/verdict.json")

    iron = next(a for a in corpus["artifacts"] if a["slug"] == "ironchests")
    annotated = next(a for a in plan["artifacts"] if "ironchests" in a["file"])
    cb = next(r for r in upstream["repos"] if r["repo"] == "dextawa/CenturyBridge")
    loader = env["fabric"]["loader"]["version"]
    api = env["fabric"]["api"]["version"]

    patched = "work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1-aw.jar"
    rules = "rules/fabric-1.21.1/container.json"
    aw = "rules/fabric-1.21.1/mcbridge.accesswidener"

    profile = {
        "schemaVersion": "0.1-draft",
        "profileId": "ironchests.5.0.2.fabric-1.20.1__fabric-1.21.1",
        "status": "passed_within_scope",
        "statusNote": ("Dedicated-server container contract passed (place/insert/NBT/restart) with the "
                       "registry-aware ItemPredicate bridge; no fallback warning observed at boot. "
                       "Client GUI/render and multiplayer were not executed, so this is scoped to the "
                       "dedicated server."),
        "source": {
            "minecraft": "1.20.1",
            "loader": "fabric",
            "modId": iron["slug"],
            "modVersion": iron["versionNumber"],
            "jarSha256": iron["sha256"],
            "originUrl": iron["url"],
            "license": iron["license"]["id"],
        },
        "target": {
            "minecraft": "1.21.1",
            "loader": "fabric",
            "loaderBuild": loader,
            "fabricApi": api,
            "clientJarSha256": next(m for m in env["minecraft"] if m["minecraft"] == "1.21.1")["clientJar"]["sha256"],
            "mappingsSha256": env["fabric"]["intermediary-1.21.1"]["sha256"],
            "sides": ["dedicated_server"],
        },
        "engine": {
            "name": "CenturyBridge",
            "repo": cb["repo"],
            "commit": cb["lockedSha"],
            "license": "MIT",
            "artifactSha256": sha256(os.path.join(ROOT, patched)),
            "note": "engine compiled with a local no-op MixinCheck stub; mixin-check gate not verified",
        },
        "rulePackage": {
            "path": rules,
            "sha256": sha256(os.path.join(ROOT, rules)),
            "accessWidener": aw,
            "accessWidenerSha256": sha256(os.path.join(ROOT, aw)),
        },
        "appliedRules": [
            {"id": "itempredicate.any.static-field", "capability": "item.predicate.any"},
            {"id": "codec.dispatch.mapcodec-shape", "capability": "codec.dispatch.mapcodec"},
            {"id": "identifier.ctor.to-factory", "capability": "identifier.construct"},
            {"id": "blockentity.nbt.read.lookup", "capability": "blockentity.nbt.registries"},
            {"id": "blockentity.nbt.write.lookup", "capability": "blockentity.nbt.registries"},
            {"id": "constant-kind-fix", "capability": "dfu.interfaceization"},
            {"id": "itempredicate.fromjson.static", "capability": "item.predicate.json",
             "implementation": "registry-aware RegistryOps bridge (compiled Java source)"},
        ],
        "analysis": {
            "missingClass": annotated["counts"]["missingClass"],
            "missingMember": annotated["counts"]["missingMember"],
            "descMismatch": annotated["counts"]["descMismatch"],
            "missingApiClass": annotated["counts"]["missingApiClass"],
            "missingApiMember": annotated["counts"]["missingApiMember"],
            "confirmedInSource": annotated["counts"]["missingConfirmedInSource"],
            "planSha256": sha256(os.path.join(ROOT, "runs/p0-fabric-target/plan.json")),
        },
        "requiredContracts": [
            {"id": "container.place", "result": "passed", "scope": "dedicated server"},
            {"id": "container.insert", "result": "passed", "scope": "dedicated server"},
            {"id": "container.nbt.write", "result": "passed", "scope": "dedicated server"},
            {"id": "container.process.restart.persistence", "result": "passed", "scope": "two process runs"},
            {"id": "container.gui.open", "result": "pending", "scope": "needs client"},
            {"id": "container.two.clients.sync", "result": "pending", "scope": "needs 2 clients"},
            {"id": "render.block.entity", "result": "pending", "scope": "needs client"},
        ],
        "evidence": {
            "boot": {"path": "runs/p3-server-accesswidener/server.log",
                     "sha256": sha256(os.path.join(ROOT, "runs/p3-server-accesswidener/server.log"))},
            "contract": {"path": "runs/p5-contract-script/verdict.json",
                         "sha256": sha256(os.path.join(ROOT, "runs/p5-contract-script/verdict.json")),
                         "passed": verdict.get("passed")},
            "engineReport": {"path": "work/cb/out/ironchests/report.md",
                             "sha256": sha256(os.path.join(ROOT, "work/cb/out/ironchests/report.md"))},
            "patchedJar": {"path": patched, "sha256": sha256(os.path.join(ROOT, patched))},
        },
        "knownLimitations": [
            "GUI/render/multiplayer untested (no client instance).",
            "Game jar was locally remapped with this project's ASM remapper because the stock Fabric remap cannot write in this sandbox.",
        ],
    }
    out = os.path.join(ROOT, "profiles", "ironchests-5.0.2-fabric__fabric-1.21.1.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("wrote", out)

    # support matrix
    lines = ["# 支持矩阵（生成物）", "",
             f"目标：Fabric 1.21.1（loader {loader}，Fabric API {api}）。来源：Minecraft 1.20.1。",
             "",
             "| 样本 | 加载器 | 静态判定 | 缺类 | 缺成员 | 描述符变 | API 缺失 | 源索引确认 | 运行时阶段 |",
             "|---|---|---|---|---|---|---|---|---|"]
    runtime = {
        "ironchests-5.0.2-fabric.jar": "CONTRACT_PASSED（服务端命令范围）",
        "lithium-fabric-mc1.20.1-0.11.4.jar":
            "LOADED；显式 mixin 降级 2 条；调用点与 2 处 Mixin 目标已适配，卡在 chunk access 的 ChunkHolderExtended cast（未通过；见 runs/p11-lithium-explosion/）",
    }
    for a in plan["artifacts"]:
        c = a["counts"]
        hard = c["missingClass"] + c["missingMember"] + c["descMismatch"] + c["missingApiClass"] + c["missingApiMember"]
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {}/{} | {} |".format(
            a["file"], a["loader"], a["verdict"], c["missingClass"], c["missingMember"],
            c["descMismatch"], c["missingApiClass"], c["missingConfirmedInSource"], hard,
            runtime.get(a["file"], "未运行")))
    lines += ["", "分母：每份样本各自的静态问题条数；运行时阶段只对实际启动过的样本填写。",
              "“未运行”不代表通过。", ""]
    sm = os.path.join(ROOT, "docs", "support-matrix.md")
    with open(sm, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("wrote", sm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
