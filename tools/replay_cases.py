"""Record identical-bundle buggy/fixed observations for each natural candidate."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from gemma_paper.subjects import evaluate, load_case, run_probe

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifact-root",type=Path,required=True)
    parser.add_argument("--ids",nargs="*")
    options=parser.parse_args()
    manifest=json.loads((options.artifact_root/"receipts/source_manifest.json").read_text())
    receipt={"kind":"NATURAL_SOURCE_REPLAY","created_at":time.time(),"cases":[]}
    for source in manifest["cases"]:
        case_id=source["id"]
        if options.ids and case_id not in options.ids:
            continue
        item={"id":case_id}
        for role in ["buggy","fixed"]:
            item[role]=evaluate(Path(source["revisions"][role]["path"]),case_id)
        diagnostics=[probe for probe in load_case(case_id)["probes"] if probe["role"]=="D"]
        if diagnostics:
            item["exploratory_diagnostics"]={role:[run_probe(Path(source["revisions"][role]["path"]),probe) for probe in diagnostics] for role in ["buggy","fixed"]}
        buggy=item["buggy"];fixed=item["fixed"]
        has_bug=any(not result["passed"] and result["execution"] in {"VALID","PRODUCT_EXCEPTION"} for result in buggy["results"] if result["role"]=="Q0")
        utility_ok=all(result["passed"] for result in buggy["results"] if result["role"]=="U")
        item["status"]="READY" if has_bug and utility_ok and fixed["all_pass"] else ("ENVIRONMENT_BLOCKED" if not fixed["infra_ok"] or not buggy["infra_ok"] else "CONTRACT_REPLAY_NEEDS_CORRECTION")
        record_dir=options.artifact_root/"receipts/case_replays"
        record_dir.mkdir(exist_ok=True)
        (record_dir/(case_id+".json")).write_text(json.dumps(item,indent=2)+"\n")
        receipt["cases"]=[json.loads(file.read_text()) for file in sorted(record_dir.glob("*.json"))]
        (options.artifact_root/"receipts/replay_cases.json").write_text(json.dumps(receipt,indent=2)+"\n")
        failures=[{"role":role,"probe":result["probe_id"],"execution":result["execution"],"observed":result.get("observed"),"error":result.get("error")} for role in ["buggy","fixed"] for result in item[role]["results"] if not result["passed"]]
        print(json.dumps({"id":case_id,"status":item["status"],"failures":failures}),flush=True)
    return receipt

if __name__=="__main__":
    main()
