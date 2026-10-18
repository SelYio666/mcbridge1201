"""Lock upstream candidate engines (Retromod, CenturyBridge) to exact commits.

GitHub's REST API is rate-limited for this host (HTTP 403) and `git` cannot do
TLS here (schannel SEC_E_NO_CREDENTIALS), so we use:
  - /commits/<branch>.atom   -> latest commit SHA + date (no API quota)
  - codeload.github.com zip  -> exact snapshot for that SHA
  - releases.atom            -> release/tag list (no API quota)

Output: manifests/upstream.lock.json + work/upstream/<repo>@<sha>/
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
import zipfile

from fetchlib import download, http_get, now_iso, sha256_file, write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "work", "upstream")
MANIFESTS = os.path.join(ROOT, "manifests")

ATOM = "{http://www.w3.org/2005/Atom}"


def latest_commit(repo: str, branch: str = "main") -> dict:
    url = f"https://github.com/{repo}/commits/{branch}.atom"
    root = ET.fromstring(http_get(url))
    entries = root.findall(f"{ATOM}entry")
    out = []
    for e in entries[:10]:
        cid = e.findtext(f"{ATOM}id") or ""
        m = re.search(r"Commit/([0-9a-f]{40})", cid)
        out.append({
            "sha": m.group(1) if m else None,
            "updated": e.findtext(f"{ATOM}updated"),
            "title": (e.findtext(f"{ATOM}title") or "").strip(),
        })
    return {"feed": url, "branch": branch, "commits": out}


def releases(repo: str) -> list[dict]:
    url = f"https://github.com/{repo}/releases.atom"
    try:
        root = ET.fromstring(http_get(url))
    except Exception as e:
        return [{"error": str(e)}]
    out = []
    for e in root.findall(f"{ATOM}entry")[:10]:
        out.append({
            "title": (e.findtext(f"{ATOM}title") or "").strip(),
            "updated": e.findtext(f"{ATOM}updated"),
            "link": e.findtext(f"{ATOM}link"),
        })
    return out


def zip_info(repo: str, sha: str) -> dict:
    dest = os.path.join(WORK, f"{repo.replace('/', '__')}@{sha}.zip")
    rec = download(f"https://codeload.github.com/{repo}/zip/{sha}", dest)
    names = []
    with zipfile.ZipFile(dest) as z:
        names = z.namelist()
    top = sorted({n.split("/")[0] for n in names})
    license_files = [n for n in names if re.search(r"(^|/)(LICENSE|LICENCE|COPYING|NOTICE)(\..*)?$", n, re.I)]
    build_files = [n for n in names if re.search(r"(^|/)(build\.gradle(\.kts)?|settings\.gradle(\.kts)?|pom\.xml|gradle\.properties|gradlew(\.bat)?)$", n)]
    return {
        **rec,
        "entryCount": len(names),
        "topLevel": top,
        "licenseFiles": license_files,
        "buildFiles": build_files,
        "zip": dest,
    }


def main() -> int:
    repos = [
        ("Bownlux/Retromod", "main"),
        ("dextawa/CenturyBridge", "main"),
    ]
    lock = {"generatedAt": now_iso(), "method": "atom feeds + codeload zip (GitHub REST API rate-limited on this host)", "repos": []}
    for repo, branch in repos:
        entry = {"repo": repo, "url": f"https://github.com/{repo}"}
        info = latest_commit(repo, branch)
        entry["branchFeed"] = info
        sha = next((c["sha"] for c in info["commits"] if c["sha"]), None)
        entry["lockedSha"] = sha
        entry["releases"] = releases(repo)
        if sha:
            z = zip_info(repo, sha)
            entry["snapshot"] = z
            # license text hash: keep the licence text itself under third-party/
            out_dir = os.path.join(ROOT, "third-party", "licenses")
            os.makedirs(out_dir, exist_ok=True)
            lic_records = []
            if z["licenseFiles"]:
                with zipfile.ZipFile(z["zip"]) as zf:
                    for lf in z["licenseFiles"][:3]:
                        text = zf.read(lf)
                        p = os.path.join(out_dir, f"{repo.replace('/', '__')}__{sha[:10]}__{os.path.basename(lf)}")
                        with open(p, "wb") as f:
                            f.write(text)
                        lic_records.append({"entry": lf, "savedAs": p, "sha256": sha256_file(p), "bytes": len(text)})
            entry["licenses"] = lic_records
        lock["repos"].append(entry)
        print(f"[lock] {repo} @ {sha}")
    write_json(os.path.join(MANIFESTS, "upstream.lock.json"), lock)
    print("wrote manifests/upstream.lock.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
