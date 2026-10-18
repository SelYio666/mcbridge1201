"""Build the P0 corpus: 5 Fabric + 5 Forge Minecraft 1.20.1 artifacts.

Selection is engineering sampling, not a statistical claim. Every artifact is
fetched from Modrinth (project owner-published), verified against the sha512
published by Modrinth, and recorded with licence + dependency metadata.
Jars live under work/corpus (never committed); manifests/corpus.json is the
committed, reproducible record.
"""
from __future__ import annotations

import json
import os

from fetchlib import download, http_json, now_iso, sha256_file, write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "work", "corpus")
MANIFESTS = os.path.join(ROOT, "manifests")
API = "https://api.modrinth.com/v2"

# role is our sampling category (per 完整实施方案 §9.1)
SAMPLES = [
    # ---- Fabric 1.20.1 ----
    dict(loader="fabric", slug="ironchests", version_id="gioHN8Aw", file="ironchests-5.0.2-fabric.jar",
         role="container", why="CenturyBridge author-reported 1.20.1->1.21.1 sample; block entities + menu + persistence"),
    dict(loader="fabric", slug="lithium", version_id="iEcXOkz4", file="lithium-fabric-mc1.20.1-0.11.4.jar",
         role="high-risk-mixin", why="large, deep Mixin/optimizer surface; expected to be a stable block case"),
    dict(loader="fabric", slug="appleskin", version_id="N5XeV21r", file="appleskin-fabric-mc1.20.1-2.5.2.jar",
         role="client-ui", why="client-only HUD + event hooks; tests side separation"),
    dict(loader="fabric", slug="modmenu", version_id="lEkperf6", file="modmenu-7.2.2.jar",
         role="metadata-config", why="config screen + Fabric API dependency graph"),
    dict(loader="fabric", slug="trashslot", version_id="rvZNAUdl", file="trashslot-fabric-1.20.1-15.1.5.jar",
         role="container", why="container-like UI, client+server, cloth-config dependency"),
    # ---- Forge 1.20.1 ----
    dict(loader="forge", slug="jei", version_id="gwEKpCDU", file="jei-1.20.1-forge-15.71.0.224.jar",
         role="container-gui", why="very large Forge API surface, registry/plugin lifecycle, item subtypes"),
    dict(loader="forge", slug="journeymap", version_id="HWDC99DO", file="journeymap-forge-1.20.1-6.0.7.jar",
         role="client-render", why="client rendering + world data; expected render breakage"),
    dict(loader="forge", slug="curios", version_id="IPQlZkz1", file="curios-forge-5.14.1+1.20.1.jar",
         role="capability-api", why="capability storage + network + menu integrations"),
    dict(loader="forge", slug="patchouli", version_id="94dtOLgZ", file="Patchouli-1.20.1-85-FORGE.jar",
         role="data-library", why="data-driven book resources + client rendering + registry"),
    dict(loader="forge", slug="create", version_id="8amzvn9x", file="create-1.20.1-6.0.8.jar",
         role="high-risk-mixin", why="registrate, large mixin set, contraption state; stress sample"),
]


def main() -> int:
    projects: dict[str, dict] = {}
    entries = []
    for s in SAMPLES:
        proj = projects.get(s["slug"])
        if proj is None:
            proj = http_json(f"{API}/project/{s['slug']}")
            projects[s["slug"]] = proj
        ver = http_json(f"{API}/version/{s['version_id']}")
        files = {f["filename"]: f for f in ver["files"]}
        if s["file"] not in files:
            print(f"[skip] {s['slug']}: {s['file']} not in {list(files)}")
            continue
        f = files[s["file"]]
        dest = os.path.join(CORPUS, s["slug"], s["file"])
        rec = download(f["url"], dest, expected_sha256=f["hashes"].get("sha256"))
        # Modrinth publishes sha512; verify independently of sha256
        import hashlib
        h = hashlib.sha512()
        with open(dest, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        sha512_ok = h.hexdigest() == f["hashes"]["sha512"]
        entry = {
            "id": f"{s['slug']}@{ver['version_number']}",
            "slug": s["slug"],
            "title": proj["title"],
            "versionNumber": ver["version_number"],
            "versionId": ver["id"],
            "filename": s["file"],
            "loader": s["loader"],
            "sourceGame": "1.20.1",
            "gameVersions": ver["game_versions"],
            "loaders": ver["loaders"],
            "role": s["role"],
            "why": s["why"],
            "license": {
                "id": proj.get("license", {}).get("id"),
                "name": proj.get("license", {}).get("name"),
                "url": proj.get("license", {}).get("url"),
                "redistributableHint": "check project licence before distributing converted jars",
            },
            "url": f["url"],
            "size": rec["size"],
            "sha256": rec["sha256"],
            "modrinthSha512Verified": sha512_ok,
            "dependencies": [
                {"projectId": d.get("project_id"), "versionId": d.get("version_id"),
                 "dependencyType": d.get("dependency_type")}
                for d in ver.get("dependencies", [])
            ],
            "publishedAt": ver.get("date_published"),
            "downloads": proj.get("downloads"),
            "clientSide": proj.get("client_side"),
            "serverSide": proj.get("server_side"),
        }
        entries.append(entry)
        print(f"[corpus] {entry['id']:<45} {entry['sha256'][:16]} sha512ok={sha512_ok}")

    manifest = {
        "schemaVersion": 1,
        "generatedAt": now_iso(),
        "sourceGame": "1.20.1",
        "selectionNote": "engineering sample (5 Fabric + 5 Forge), not a statistical sample; see docs/baseline.md",
        "artifacts": entries,
    }
    write_json(os.path.join(MANIFESTS, "corpus.json"), manifest)
    print(f"wrote manifests/corpus.json ({len(entries)} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
