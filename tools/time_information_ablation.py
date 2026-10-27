"""Compare curated policy cards and visible reproducers without repair feedback."""
import argparse
import json
import time
from pathlib import Path
from gemma_paper.api import FreeGemmaClient,ApiPaused,PATCH_TOOL
from gemma_paper.runner import ROOT,make_packet,response_diff,workspace
from gemma_paper.subjects import load_case,evaluate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--replicates",nargs="+",default=["r01","r02"])
    options=parser.parse_args()
    config=json.loads((ROOT/"configs/runtime.free.json").read_text())
    artifact=Path(config["artifact_root"])
    manifest=json.loads((artifact/"receipts/source_manifest.json").read_text())
    by_id={item["id"]:item for item in manifest["cases"]}
    root=artifact/"runs/time-information-v1"
    rows=[]
    client=FreeGemmaClient(config,artifact/"api/time-attempts.jsonl")
    for replicate in options.replicates:
        for index,case_id in enumerate(["T1","T4","T5","T6"]):
            case=load_case(case_id)
            source=Path(by_id[case_id]["revisions"]["buggy"]["path"])
            conditions=["policy_without_Q0","Q0_without_added_policy"] if index%2==0 else ["Q0_without_added_policy","policy_without_Q0"]
            for condition in conditions:
                folder=root/case_id/replicate/condition
                folder.mkdir(parents=True,exist_ok=True)
                result_file=folder/"evaluation.json"
                if result_file.exists():
                    rows.append(json.loads(result_file.read_text()));continue
                packet=make_packet(case,source)
                if condition=="policy_without_Q0":
                    packet["visible_reproducer"]=[]
                else:
                    packet["contract"]="Repair the demonstrated faulty behavior without regressing the supplied functionality controls."
                    packet["policy_origin"]="No added policy card; original source and visible reproducer remain available."
                (folder/"packet.json").write_text(json.dumps(packet,indent=2)+"\n")
                response_file=folder/"response.json"
                try:
                    if response_file.exists():response=json.loads(response_file.read_text())
                    else:
                        client.request_tag=str(response_file)
                        response=client.generate([{"role":"user","parts":[{"text":json.dumps(packet)}]}],tools=[PATCH_TOOL],tool_mode="AUTO")
                        response_file.write_text(json.dumps(response,indent=2)+"\n")
                except ApiPaused as error:
                    (root/"pause.json").write_text(json.dumps({"reason":error.reason,"details":error.details,"case":case_id,"replicate":replicate,"condition":condition,"at":time.time()},indent=2)+"\n")
                    raise SystemExit(75)
                diff,error=response_diff(response,source,case["product_paths"])
                subject,valid,reason=workspace(source,folder/"subject",diff,case["product_paths"])
                result=evaluate(subject if valid else source,case_id)
                record={"case":case_id,"replicate":replicate,"condition":condition,"proposal_valid":valid,"proposal_reason":error or reason,
                        "joint_valid":valid and result["all_pass"],"evaluation":result,
                        "usage":response.get("usageMetadata"),"model_version":response.get("modelVersion"),"source_response":str(response_file)}
                result_file.write_text(json.dumps(record,indent=2)+"\n")
                rows.append(record)
                print(json.dumps({key:record[key] for key in ["case","replicate","condition","proposal_valid","joint_valid"]}),flush=True)
    (root/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")

if __name__=="__main__":main()
