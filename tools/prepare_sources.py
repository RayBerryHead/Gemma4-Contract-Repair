"""Fetch pinned public upstream archives on the remote execution host."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import tarfile
import time
from pathlib import Path
import requests

def prepare(repo_root: Path, artifact_root: Path, ids: list[str] | None = None) -> dict:
    cases = json.loads((repo_root / "docs/plans/20261023_research_ready/case_index.json").read_text())["cases"]
    cases += [
        {"id":"TD1","repo":"pallets-eco/croniter","buggy_sha":"9810279c20030954e2f1ed2cf5f1d34b98c6b07f","fixed_sha":"f329964223eeb29e7788b1a9d615b525148fec96"},
        {"id":"TD2","repo":"agronholm/apscheduler","buggy_sha":"307896e9f47627b4b752d5745407ee4a989ae24e","fixed_sha":"c5a0346d303f64a044ef744aa75d5d6a18593d34"},
    ]
    previous=artifact_root/"receipts/source_manifest.json"
    existing=json.loads(previous.read_text())["cases"] if previous.exists() else []
    result = {"cases": existing if ids else [], "created_at": time.time(), "host": os.uname().nodename}
    source_root = artifact_root / "sources"
    source_root.mkdir(parents=True, exist_ok=True)
    for case in cases:
        if ids and case["id"] not in ids:
            continue
        item = {"id": case["id"], "repo": case["repo"], "revisions": {}}
        for role, field in (("buggy", "buggy_sha"), ("fixed", "fixed_sha")):
            sha = case[field]
            destination = source_root / (case["repo"].replace("/", "--") + "-" + sha)
            marker = destination / ".paper-source.json"
            url = f"https://codeload.github.com/{case['repo']}/tar.gz/{sha}"
            try:
                if not marker.exists():
                    archive = source_root / (sha + ".tar.gz")
                    if not archive.exists():
                        with requests.get(url, stream=True, timeout=(20, 180)) as response:
                            response.raise_for_status()
                            with archive.open("wb") as output:
                                for chunk in response.iter_content(1024 * 1024):
                                    output.write(chunk)
                    digest = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
                    temporary = source_root / (sha + ".extract")
                    temporary.mkdir(exist_ok=True)
                    with tarfile.open(archive) as bundle:
                        bundle.extractall(temporary, filter="data")
                    children = list(temporary.iterdir())
                    if len(children) != 1 or not children[0].is_dir():
                        raise RuntimeError("Unexpected archive layout")
                    children[0].rename(destination)
                    temporary.rmdir()
                    marker.write_text(json.dumps({"repo": case["repo"], "sha": sha, "url": url, "archive_sha256": digest}, indent=2) + "\n")
                metadata = json.loads(marker.read_text())
                item["revisions"][role] = {**metadata, "path": str(destination), "status": "SOURCE_READY"}
            except Exception as error:
                item["revisions"][role] = {"sha": sha, "status": "SOURCE_FAILED", "error": str(error), "url": url}
            print(case["id"], role, item["revisions"][role]["status"], flush=True)
        result["cases"]=[old for old in result["cases"] if old["id"]!=item["id"]]+[item]
        (artifact_root / "receipts").mkdir(exist_ok=True)
        (artifact_root / "receipts/source_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--ids", nargs="*")
    options = parser.parse_args()
    prepare(Path(__file__).resolve().parents[1], options.artifact_root, options.ids)
