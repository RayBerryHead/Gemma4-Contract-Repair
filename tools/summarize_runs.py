"""Export formal evidence without mixing development, technical smoke, or shared costs."""
import argparse
import csv
import json
from pathlib import Path

def usage(path):
    if not path.exists():return 0
    data=json.loads(path.read_text())
    return data.get("usageMetadata",{}).get("totalTokenCount",0)

def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w") as output:
        writer=csv.DictWriter(output,fieldnames=fields)
        writer.writeheader();writer.writerows(rows)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("run_root",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--stage",default="formal")
    options=parser.parse_args()
    rows=[];pairs=[]
    for file in sorted(options.run_root.glob("*/*/state.json")):
        state=json.loads(file.read_text())
        if state.get("stage")!=options.stage:continue
        folder=file.parent
        initial_path=folder/"initial-evaluation.json"
        initial=json.loads(initial_path.read_text()) if initial_path.exists() else {}
        initial_results=initial.get("results",[])
        initial_valid=bool(initial.get("proposal_valid")) and bool(initial.get("all_pass"))
        apparent=bool(initial.get("proposal_valid")) and all(r["passed"] for r in initial_results if r["role"] in {"Q0","U"})
        hidden_fail=any(not r["passed"] for r in initial_results if r["role"]=="E")
        specification=Path(__file__).resolve().parents[1]/"configs/cases"/(state["case_id"]+".json")
        evidence=json.loads(specification.read_text())["evidence_class"]
        for name,arm in state.get("arms",{}).items():
            feedback_files=sorted(folder.glob(name+"-feedback-*.json"))
            feedback=[json.loads(p.read_text()) for p in feedback_files]
            final=arm.get("final_feedback",{})
            values=final.get("public_results",[])
            token_total=sum(usage(path) for path in folder.glob(name+"-proposal-*.json"))
            rows.append({
                "root_id":state["case_id"],"evidence_class":evidence,"replicate":state["replicate"],"arm":name,
                "status":arm.get("status",state.get("status")),"initial_hash":state.get("initial_hash"),
                "initial_joint_valid":initial_valid,"initial_apparent_pass":apparent,
                "initial_apparent_pass_hidden_fail":apparent and hidden_fail,
                "joint_valid":arm.get("joint_valid"),
                "recovered":not initial_valid and bool(arm.get("joint_valid")),
                "regressed":initial_valid and arm.get("joint_valid") is False,
                "last_proposal_valid":final.get("proposal",{}).get("valid"),
                "u_q0_pass":all(v["passed"] for v in values if v["role"] in {"Q0","U"}) if values else None,
                "holdout_pass":all(v["passed"] for v in arm.get("final_holdout",[])) if arm.get("final_holdout") else None,
                "visible_audit_pass":all(v["passed"] for v in arm.get("final_audit",[])) if "final_audit" in arm else None,
                "revisions":arm.get("step"),
                "new_probe_subject_calls":sum(f["new_subject_calls"] for f in feedback),
                "public_feedback_subject_calls":sum(v["subject_calls"] for f in feedback for v in f["public_results"]),
                "public_feedback_elapsed_seconds":sum(v["elapsed_seconds"] for f in feedback for v in f["public_results"]),
                "shared_initial_tokens":usage(folder/"initial.json"),"arm_revision_tokens":token_total,
                "source_sha":state.get("source_sha"),"state_file":str(file)})
        b=state.get("arms",{}).get("B",{});m=state.get("arms",{}).get("M",{})
        complete=b.get("status")==m.get("status")=="COMPLETE"
        outcome="incomplete"
        if complete:
            outcome="both" if b["joint_valid"] and m["joint_valid"] else "M_only" if m["joint_valid"] else "B_only" if b["joint_valid"] else "neither"
        pairs.append({"root_id":state["case_id"],"evidence_class":evidence,"replicate":state["replicate"],
                      "outcome":outcome,"initial_hash":state.get("initial_hash"),
                      "shared_initial_tokens":usage(folder/"initial.json"),"state_file":str(file)})
    fields=["root_id","evidence_class","replicate","arm","status","initial_hash","initial_joint_valid",
            "initial_apparent_pass","initial_apparent_pass_hidden_fail","joint_valid","recovered","regressed",
            "last_proposal_valid","u_q0_pass","holdout_pass","visible_audit_pass","revisions",
            "new_probe_subject_calls","public_feedback_subject_calls","public_feedback_elapsed_seconds",
            "shared_initial_tokens","arm_revision_tokens","source_sha","state_file"]
    write_csv(options.output,rows,fields)
    pair_path=options.output.with_name(options.output.stem+"-pairs.csv")
    write_csv(pair_path,pairs,["root_id","evidence_class","replicate","outcome","initial_hash","shared_initial_tokens","state_file"])
    print(json.dumps({"rows":len(rows),"paired_blocks":len(pairs),"stage":options.stage,
                      "shared_initial_accounting":"Count once per paired block, not once per arm."}))

if __name__=="__main__":
    main()
