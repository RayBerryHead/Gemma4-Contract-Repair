"""Run or resume a frozen paper batch using only the configured free models."""
import argparse
import json
from pathlib import Path
from gemma_paper.runner import ROOT, run_pair

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("paper",choices=["cache","time"])
    parser.add_argument("--mode",choices=["main","dev","full","feedback","transfer"],default="main")
    parser.add_argument("--replicates",nargs="+")
    options=parser.parse_args()
    config=json.loads((ROOT/"configs/runtime.free.json").read_text())
    prefix="C" if options.paper=="cache" else "T"
    cases=[prefix+str(index) for index in range(1,9)]
    arms=["B","M"]
    stage="formal"
    campaign="formal-v1"
    repetitions=options.replicates or ["r01","r02"]
    if options.mode=="dev":
        cases=["CD1","CD2"] if prefix=="C" else ["TD1","TD2"]
        stage="development";campaign="development-v1"
    if options.mode in {"full","feedback"}:
        cases=["C1","C2","C3","C4"] if prefix=="C" else ["T1","T4","T5","T6"]
        repetitions=options.replicates or ["r01"]
        arms=["F"] if options.mode=="full" else ["J"]
        if options.mode=="feedback" and prefix=="C":
            parser.error("The matched feedback-order arm is specified for Time only")
    if options.mode=="transfer":
        cases=["C1","C3"] if prefix=="C" else ["T1","T6"]
        config["model"]=config["secondary_model"]
        repetitions=options.replicates or ["r01"]
        campaign="transfer-26b-v1"
    root=Path(config["artifact_root"])/"runs"/campaign
    for replicate in repetitions:
        for case in cases:
            result=run_pair(case,replicate,config,arms,root,stage)
            print(json.dumps({"case":case,"replicate":replicate,"status":result.get("status"),
                              "arms":{name:{"status":value.get("status"),"joint_valid":value.get("joint_valid")} for name,value in result["arms"].items()}}),flush=True)
            if result.get("status")=="PAUSED":
                print(json.dumps({"resume":"Run exactly the same command after resolving the recorded free-resource pause.","pause":result.get("pause")}),flush=True)
                raise SystemExit(75)

if __name__=="__main__":
    main()
