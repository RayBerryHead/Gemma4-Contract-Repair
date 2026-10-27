"""Replay B/M/A/F ordering on pinned controls and available natural initial patches."""
import argparse
import json
from pathlib import Path
from gemma_paper.runner import ROOT, response_diff, workspace, probe_feedback
from gemma_paper.subjects import load_case
from gemma_paper.selectors import compile_phase_map

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("paper",choices=["cache","time"])
    parser.add_argument("--run-root",type=Path)
    parser.add_argument("--extra-patches",type=Path)
    options=parser.parse_args()
    config=json.loads((ROOT/"configs/runtime.free.json").read_text())
    artifact=Path(config["artifact_root"])
    manifest=json.loads((artifact/"receipts/source_manifest.json").read_text())
    by_id={item["id"]:item for item in manifest["cases"]}
    ids=["C1","C2","C3","C4"] if options.paper=="cache" else ["T1","T4","T5","T6"]
    output=[]
    extras=json.loads(options.extra_patches.read_text()) if options.extra_patches else []
    for case_id in ids:
        case=load_case(case_id);source=by_id[case_id]
        base=Path(source["revisions"]["buggy"]["path"])
        mappings=compile_phase_map(base,case["product_paths"])
        pool=[("upstream_buggy",base,"","control"),("upstream_fixed",Path(source["revisions"]["fixed"]["path"]),"","control")]
        if options.run_root:
            for response_file in sorted((options.run_root/case_id).glob("*/initial.json")):
                response=json.loads(response_file.read_text())
                diff,error=response_diff(response,base,case["product_paths"])
                if error:continue
                subject,valid,_=workspace(base,artifact/"runs/cpu-pool"/case_id,diff,case["product_paths"])
                if valid:pool.append((response_file.parent.name,subject,diff,"natural_initial"))
        for entry in extras:
            if entry["case"]!=case_id:continue
            diff=Path(entry["diff"]).read_text()
            subject,valid,_=workspace(base,artifact/"runs/cpu-pool"/case_id,diff,case["product_paths"])
            if valid:pool.append((entry["label"],subject,diff,entry.get("kind","artificial_control")))
        for label,subject,diff,kind in pool:
            for arm in ["B","M","A","F"]:
                feedback=probe_feedback(subject,case,arm,diff,mappings,[])
                witnesses=[item for item in feedback["public_results"] if item["role"]=="V" and not item["passed"] and item["execution"]=="VALID"]
                output.append({"case":case_id,"patch_label":label,"patch_kind":kind,"arm":arm,
                               "new_subject_calls":feedback["new_subject_calls"],"found_visible_witness":bool(witnesses),
                               "bank_exhausted":feedback["bank_exhausted"],"budget_skipped":feedback["budget_skipped"],
                               "selected_probe_ids":feedback["selected_probe_ids"],"mapped_phases":feedback["mapped_patch_phases"]})
    destination=artifact/"receipts"/("cpu-diagnostics-"+options.paper+".json")
    destination.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({"rows":len(output),"output":str(destination),"live_model_calls":0}))

if __name__=="__main__":
    main()
