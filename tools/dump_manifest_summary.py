"""Print hashes/licenses for the docs (no third-party jars are copied into docs)."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

corpus = json.load(open(os.path.join(ROOT, "manifests", "corpus.json"), encoding="utf-8"))
for a in corpus["artifacts"]:
    print(f"{a['id']} | {a['sha256']} | {a['license']['id']} | {a['role']} | {a['size']}")

print("--- upstream ---")
u = json.load(open(os.path.join(ROOT, "manifests", "upstream.lock.json"), encoding="utf-8"))
for r in u["repos"]:
    print(r["repo"], r["lockedSha"], r["snapshot"]["sha256"],
          [(l["sha256"][:12], l["entry"]) for l in r["licenses"]])

print("--- environment ---")
e = json.load(open(os.path.join(ROOT, "manifests", "environment.lock.json"), encoding="utf-8"))
for m in e["minecraft"]:
    print(m["minecraft"], m["clientJar"]["sha256"], m["javaVersion"])
for k, v in e["fabric"].items():
    print(k, v.get("version"), v["sha256"])
