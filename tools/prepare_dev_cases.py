"""Prepare the already-tracked synthetic development sources, without natural-root inflation."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def prepare(artifact):
    file=artifact/"receipts/source_manifest.json"
    manifest=json.loads(file.read_text())
    for case,index in [("CD1","s01"),("CD2","s02")]:
        revisions={}
        for role in ["buggy","fixed"]:
            original=ROOT/"docs/plans/20261022_two_papers/lean/synth_dev"/f"{index}_{role}.mjs"
            data=original.read_bytes()
            digest=hashlib.sha256(data).hexdigest()
            destination=artifact/"sources"/f"synthetic-{index}-{role}-{digest[:12]}"
            destination.mkdir(exist_ok=True)
            (destination/"subject.mjs").write_bytes(data)
            revisions[role]={"path":str(destination),"sha256":digest,"status":"SOURCE_READY","source_kind":"synthetic_development"}
        manifest["cases"]=[item for item in manifest["cases"] if item["id"]!=case]+[{"id":case,"repo":"local-synthetic-dev","revisions":revisions}]
    file.write_text(json.dumps(manifest,indent=2)+"\n")

if __name__=="__main__":
    prepare(Path(json.loads((ROOT/"configs/runtime.free.json").read_text())["artifact_root"]))
