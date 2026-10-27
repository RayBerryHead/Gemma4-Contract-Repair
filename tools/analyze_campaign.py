"""Analyze frozen campaign records with explicit root and draw denominators."""
import argparse,csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
def normalize(value):
    if isinstance(value,list):return [normalize(item) for item in value]
    if not isinstance(value,dict):return value
    output={}
    for key,item in value.items():
        if key in {"elapsed_seconds","raw_proposal_hash","raw_diff_hash","applied_diff_hash"}:continue
        if key=="responses" and isinstance(item,list):
            cookies={}
            normalized=[]
            for response in item:
                response=dict(response)
                cookie=response.get("cookie")
                if cookie is not None:
                    cookies.setdefault(cookie,"cookie_"+str(len(cookies)+1))
                    response["cookie"]=cookies[cookie]
                normalized.append(normalize(response))
            output[key]=normalized
        else:output[key]=normalize(item)
    return output
def signature(value):
    return hashlib.sha256(json.dumps(normalize(value),sort_keys=True).encode()).hexdigest()
def all_role(results,roles):
    chosen=[item for item in results if item["role"] in roles]
    return bool(chosen) and all(item["passed"] for item in chosen)
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifact-root",type=Path,required=True)
    parser.add_argument("--source-root",type=Path,required=True)
    parser.add_argument("--require-complete",action="store_true")
    parser.add_argument("--run-root",type=Path)
    options=parser.parse_args()
    run=options.run_root or options.artifact_root/"runs/formal-v1"
    output=options.artifact_root/"results/formal-v1"
    output.mkdir(parents=True,exist_ok=True)
    data={"papers":{},"missing_main":[],"missing_F":[]}
    rows=[]
    repo_index={c["id"]:c["repo"] for c in json.loads((options.source_root/"docs/plans/20261023_research_ready/case_index.json").read_text())["cases"]}
    for paper,prefix,full_ids in [("cache","C",["C1","C2","C3","C4"]),("time","T",["T1","T4","T5","T6"])]:
        stats={"natural_roots":8,"planned_initial_draws":16,"initial_observed":0,"initial_applied":0,"initial_joint_valid":0,
               "apparent_passes":0,"apparent_pass_hidden_fail":0,"arms":{},"pairs":Counter(),
               "same_initial_feedback_pairs":0,"same_feedback_discordant_outcomes":0,"roots":[]}
        totals={arm:Counter() for arm in ["B","M","F"]}
        for number in range(1,9):
            case_id=prefix+str(number)
            case=json.loads((options.source_root/"configs/cases"/(case_id+".json")).read_text())
            stats["roots"].append({"id":case_id,"evidence_class":case["evidence_class"],"repo":repo_index[case_id]})
            for replicate in ["r01","r02"]:
                folder=run/case_id/replicate
                state_file=folder/"state.json"
                state=json.loads(state_file.read_text()) if state_file.exists() else {}
                initial_file=folder/"initial-evaluation.json"
                initial=json.loads(initial_file.read_text()) if initial_file.exists() else {}
                if initial:
                    stats["initial_observed"]+=1
                    applied=bool(initial.get("proposal_valid"))
                    joint=applied and initial["all_pass"]
                    apparent=applied and all_role(initial["results"],{"Q0","U"})
                    hidden_fail=apparent and not all_role(initial["results"],{"E"})
                    stats["initial_applied"]+=applied;stats["initial_joint_valid"]+=joint
                    stats["apparent_passes"]+=apparent;stats["apparent_pass_hidden_fail"]+=hidden_fail
                else:applied=joint=apparent=hidden_fail=None
                for arm in ["B","M"]+(["F"] if replicate=="r01" and case_id in full_ids else []):
                    branch=state.get("arms",{}).get(arm,{})
                    complete=branch.get("status")=="COMPLETE"
                    if not complete:
                        (data["missing_F"] if arm=="F" else data["missing_main"]).append([case_id,replicate,arm])
                    else:
                        totals[arm]["completed"]+=1
                        totals[arm]["joint_valid"]+=bool(branch["joint_valid"])
                        totals[arm]["recovered"]+=not joint and branch["joint_valid"]
                        totals[arm]["regressed"]+=bool(joint) and not branch["joint_valid"]
                    rows.append({"paper":paper,"root_id":case_id,"replicate":replicate,"arm":arm,
                                 "evidence_class":case["evidence_class"],"status":branch.get("status","not_started"),
                                 "initial_joint_valid":joint,"initial_apparent_pass":apparent,
                                 "initial_hidden_fail":hidden_fail,"joint_valid":branch.get("joint_valid")})
                b=state.get("arms",{}).get("B",{});m=state.get("arms",{}).get("M",{})
                if b.get("status")==m.get("status")=="COMPLETE":
                    stats["pairs"]["both" if b["joint_valid"] and m["joint_valid"] else "B_only" if b["joint_valid"] else "M_only" if m["joint_valid"] else "neither"]+=1
                    b0=folder/"B-feedback-0.json";m0=folder/"M-feedback-0.json"
                    same=b0.exists() and m0.exists() and signature(json.loads(b0.read_text()))==signature(json.loads(m0.read_text()))
                    stats["same_initial_feedback_pairs"]+=same
                    stats["same_feedback_discordant_outcomes"]+=same and b["joint_valid"]!=m["joint_valid"]
        stats["arms"]={arm:dict(counts) for arm,counts in totals.items()}
        stats["pairs"]=dict(stats["pairs"])
        data["papers"][paper]=stats
    data["complete_main"]=not data["missing_main"]
    data["complete_F"]=not data["missing_F"]
    (output/"analysis.json").write_text(json.dumps(data,indent=2)+"\n")
    with (output/"root_outcomes.csv").open("w") as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({"complete_main":data["complete_main"],"complete_F":data["complete_F"],
                      "observed_initial_draws":{paper:value["initial_observed"] for paper,value in data["papers"].items()},
                      "completed_arms":{paper:value["arms"] for paper,value in data["papers"].items()}}))
    if options.require_complete and not(data["complete_main"] and data["complete_F"]):raise SystemExit(75)
if __name__=="__main__":main()
