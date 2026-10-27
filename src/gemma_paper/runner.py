"""A small paired focused-repair runner with durable resume checkpoints."""
from __future__ import annotations
import argparse
import ast
import copy
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from .api import FreeGemmaClient, ApiPaused, PATCH_TOOL, extract_patch, tool_response_content
from .subjects import ROOT, load_case, run_probe, evaluate
from .selectors import compile_phase_map, patch_phases, select_probe, predictions, signature, project_observation

def digest(value) -> str:
    if not isinstance(value,bytes):
        value=json.dumps(value,sort_keys=True).encode()
    return hashlib.sha256(value).hexdigest()

def save(path: Path, value) -> None:
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(value,indent=2)+"\n")
    temporary.replace(path)

def public_source(source: Path, relative: str, case_id: str) -> str:
    text=(source/relative).read_text()
    context_file=ROOT/"configs/contexts"/(case_id+".json")
    if context_file.exists():
        context=json.loads(context_file.read_text())
        intervals=context.get("ranges",{}).get(relative)
        if intervals:
            lines=text.splitlines()
            selected=sorted({index for start,end in intervals for index in range(start,min(end,len(lines)))})
            chunks=[]
            previous=None
            for index in selected:
                if previous is None or index!=previous+1:
                    chunks.append("# Original line "+str(index+1) if relative.endswith(".py") else "// Original line "+str(index+1))
                chunks.append(lines[index]);previous=index
            return "\n".join(chunks)[:context["per_file_character_cap"]]
    if relative.endswith(".py"):
        names={"T1":{"range"},"T2":{"expand","__init__","_expand","_get_start_time"},
               "T3":{"_parse_tz_str","_parse_dst_start_end"},"T4":{"first_of","last_of","nth_of"},
               "T5":{"__add__","add","in_days","__radd__"},"T6":{"_process_jobs"},
               "C3":{"process_response","process_request"},"C4":{"process_response","process_request"},
               "C6":{"process_response"},"C8":{"process_response","process_request","has_cache_control_directive"}}
        selected=[]
        tree=ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                selected.append((node.lineno,ast.get_source_segment(text,node)))
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names.get(case_id,set()):
                selected.append((node.lineno,ast.get_source_segment(text,node)))
        if selected:
            return "\n\n".join(f"# Original line {line}\n{content}" for line,content in sorted(selected))[:30000]
    if relative.endswith((".js",".cjs")):
        lines=text.splitlines()
        selected=set(range(min(55,len(lines))))
        for mapping in compile_phase_map(source,[relative]):
            selected.update(range(max(mapping["start"]-1,0),min(mapping["end"],len(lines))))
        if selected:
            return "\n".join(f"{index+1}: {lines[index]}" for index in sorted(selected))[:18000]
    return text[:18000]

def make_packet(case: dict, source: Path) -> dict:
    return {"task_id":case["id"],"contract":case["contract"],"policy_origin":"source-backed supplied contract",
            "source":{name:public_source(source,name,case["id"]) for name in case["product_paths"]},
            "visible_reproducer":[probe for probe in case["probes"] if probe["role"]=="Q0"],
            "preserved_functionality":[probe for probe in case["probes"] if probe["role"]=="U"],
            "instructions":"Repair the existing product source. Submit one complete cumulative list of exact text replacements against the original buggy base through submit_patch. Use the full source path keys, and copy each old_text exactly once from the supplied source, preserving whitespace. All edits must be cumulative from the original source, including after feedback. Do not edit tests or evaluator files. Source localization is supplied. Use the stated contract and preserve legitimate behavior."}

def normalize_diff_paths(diff: str, allowed: list[str]) -> str:
    by_basename={}
    for name in allowed:
        by_basename.setdefault(Path(name).name,[]).append(name)
    def mapped(value, default_prefix):
        if value=="/dev/null":
            return value
        has_prefix=value.startswith(("a/","b/"))
        prefix=value[:2] if has_prefix else default_prefix
        name=value[2:] if has_prefix else value
        if name in allowed:
            return prefix+name
        matches=by_basename.get(Path(name).name,[])
        return prefix+matches[0] if len(matches)==1 else value
    output=[]
    for line in diff.splitlines(True):
        if line.startswith("diff --git "):
            parts=line.rstrip().split()
            if len(parts)==4:
                line="diff --git "+mapped(parts[2],"a/")+" "+mapped(parts[3],"b/")+"\n"
        elif line.startswith(("--- ","+++ ")):
            line=line[:4]+mapped(line[4:].strip(),"a/" if line.startswith("--- ") else "b/")+"\n"
        output.append(line)
    return "".join(output)

def response_diff(response: dict, source: Path, allowed: list[str]) -> tuple[str,str]:
    raw=extract_patch(response)
    if raw:
        return normalize_diff_paths(raw,allowed),""
    contents=[part for candidate in response.get("candidates",[]) for part in candidate.get("content",{}).get("parts",[])]
    call=next((part["functionCall"] for part in contents if part.get("functionCall",{}).get("name")=="submit_patch"),None)
    if not call or not isinstance(call.get("args",{}).get("edits"),list):
        return "","NO_VALID_PATCH_OR_EDITS"
    original={}
    updated={}
    for edit in call["args"]["edits"]:
        name=edit.get("path","")
        if name not in allowed:
            matches=[path for path in allowed if Path(path).name==Path(name).name]
            if len(matches)!=1:
                return "","AMBIGUOUS_OR_UNDECLARED_PRODUCT_PATH"
            name=matches[0]
        if name not in original:
            original[name]=(source/name).read_text()
            updated[name]=original[name]
        old=edit.get("old_text","")
        new=edit.get("new_text")
        if not isinstance(old,str) or not old or not isinstance(new,str):
            return "","INVALID_REPLACEMENT_FIELDS"
        occurrences=updated[name].count(old)
        if occurrences!=1:
            return "",f"OLD_TEXT_MATCH_COUNT_{occurrences}: copy an exact unique source string"
        updated[name]=updated[name].replace(old,new,1)
    result="".join("diff --git a/"+name+" b/"+name+"\n"+"".join(difflib.unified_diff(original[name].splitlines(True),updated[name].splitlines(True),
                            fromfile="a/"+name,tofile="b/"+name)) for name in original)
    return result,"" if result else "NO_PRODUCT_CHANGE"

def workspace(source: Path, parent: Path, diff: str, allowed: list[str]) -> tuple[Path,bool,str]:
    if not diff.strip():
        return source,False,"EMPTY_PATCH"
    destination=parent/("patch-"+digest(diff)[:16])
    marker=destination/".paper-applied.json"
    if marker.exists():
        data=json.loads(marker.read_text())
        return destination,data["valid"],data["reason"]
    destination.mkdir(parents=True,exist_ok=False)
    shutil.copytree(source,destination,dirs_exist_ok=True,ignore=shutil.ignore_patterns("__pycache__","*.pyc",".paper-source.json",".git"))
    for args in (["git","init","-q"],["git","config","user.name","Paper Runner"],
                 ["git","config","user.email","paper-runner@localhost"],["git","add","."],
                 ["git","commit","-qm","Pinned upstream source"]):
        subprocess.run(args,cwd=destination,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    applied=subprocess.run(["git","apply","--whitespace=nowarn","-"],input=diff,text=True,cwd=destination,capture_output=True)
    if applied.returncode:
        marker.write_text(json.dumps({"valid":False,"reason":"APPLY_FAILED: "+applied.stderr[-1200:]}))
        return destination,False,"APPLY_FAILED: "+applied.stderr[-1200:]
    changed=subprocess.check_output(["git","diff","--name-only"],cwd=destination,text=True).splitlines()
    valid=bool(changed) and all(name in allowed for name in changed)
    reason="APPLIED" if valid else "PRODUCT_SCOPE_VIOLATION"
    marker.write_text(json.dumps({"valid":valid,"reason":reason}))
    return destination,valid,reason

def probe_feedback(source: Path, case: dict, arm: str, diff: str, mappings: list[dict], previous: list[str]) -> dict:
    by_id={probe["id"]:probe for probe in case["probes"]}
    common=[probe for probe in case["probes"] if probe["role"] in {"Q0","U"}]
    common += [by_id[key] for key in previous if key in by_id and by_id[key]["role"]=="V"]
    results=[run_probe(source,probe) for probe in common]
    pending=[probe for probe in case["probes"] if probe["role"]=="V" and probe["id"] not in previous]
    covered=set()
    changed=patch_phases(diff,mappings)
    active=set().union(*(set(predictions(probe)) for probe in pending)) if pending else set()
    new_calls=0
    selected=[]
    skipped=[]
    while pending:
        probe=pending[0] if arm in {"F","J"} else select_probe(pending,arm,covered,changed,active)
        pending.remove(probe)
        if arm not in {"F","J"} and (new_calls+probe["cost"]>32 or case["id"].startswith("C") and len(selected)>=8):
            skipped.append(probe["id"])
            continue
        result=run_probe(source,probe)
        result["expected"]=probe["expected"]
        results.append(result)
        selected.append(probe["id"])
        new_calls+=probe["cost"]
        covered.update(probe.get("tags",[]))
        if result["execution"]=="VALID" and not case["id"].startswith("C"):
            observed=signature(project_observation(probe,result["observed"]))
            active={name for name in active if name not in predictions(probe) or signature(predictions(probe)[name])==observed}
        if not result["passed"] and arm not in {"F","J"}:
            break
    all_visible=not pending and not skipped and all(result["passed"] for result in results)
    output={"public_results":results,"selected_probe_ids":selected,
            "new_subject_calls":new_calls,"all_visible_pass":all_visible,
            "mapped_patch_phases":sorted(changed),"unmapped":case["id"].startswith("C") and not changed,
            "budget_skipped":skipped,"bank_exhausted":not pending and not skipped}
    if arm=="J":
        output["public_results"]=sorted(results,key=lambda item:(signature(by_id[item["probe_id"]].get("tags",[])),item["probe_id"]))
    return output

def proposal(client, history: list[dict], path: Path, model: str | None = None) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    client.request_tag=str(path)
    response=client.generate(history,tools=[PATCH_TOOL],tool_mode="AUTO",model=model)
    save(path,response)
    return response

def next_history(history: list[dict], response: dict, feedback: dict) -> list[dict]:
    calls=[part for part in response["candidates"][0]["content"].get("parts",[]) if "functionCall" in part]
    if calls:
        return history+tool_response_content(response,[feedback]*len(calls))
    return history+[response["candidates"][0]["content"],{"role":"user","parts":[{"text":json.dumps(feedback)}]}]

def run_pair(case_id: str, replicate: str, config: dict, arms: list[str], run_root: Path,
             stage: str="formal", offline_diff: str | None=None) -> dict:
    root=run_root/case_id/replicate
    root.mkdir(parents=True,exist_ok=True)
    case=load_case(case_id)
    if stage=="formal" and case.get("split")=="dev":
        raise ValueError("Development cases cannot enter the formal denominator")
    manifest=json.loads((Path(config["artifact_root"])/"receipts/source_manifest.json").read_text())
    entry=next(item for item in manifest["cases"] if item["id"]==case_id)
    source=Path(entry["revisions"]["buggy"]["path"])
    identity=digest({"case":case,"config":config,"replicate":replicate,"stage":stage})
    state_path=root/"state.json"
    state=json.loads(state_path.read_text()) if state_path.exists() else {
        "case_id":case_id,"replicate":replicate,"identity":identity,"stage":stage,"status":"RUNNING","arms":{},
        "source_sha":subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()}
    if state["identity"]!=identity:
        raise RuntimeError("Resume identity mismatch; use a new run root for changed inputs")
    if all(state["arms"].get(arm,{}).get("status")=="COMPLETE" for arm in arms):
        return state
    packet=make_packet(case,source)
    save(root/"public_packet.json",packet)
    mappings=compile_phase_map(source,case["product_paths"])
    save(root/"phase_map.json",mappings)
    history=[{"role":"user","parts":[{"text":json.dumps(packet)}]}]
    client=None
    save(state_path,state)
    try:
        if offline_diff is None:
            client=FreeGemmaClient(config,Path(config["artifact_root"])/"api"/("cache-attempts.jsonl" if case_id.startswith("C") else "time-attempts.jsonl"))
        if offline_diff is not None:
            initial={"candidates":[{"content":{"role":"model","parts":[{"functionCall":{"name":"submit_patch","args":{"diff":offline_diff}}}]}}]}
            save(root/"initial.json",initial)
        else:
            initial=proposal(client,history,root/"initial.json")
        initial_diff,initial_error=response_diff(initial,source,case["product_paths"])
        if stage=="technical-smoke" and not initial_diff and any(candidate.get("finishReason")=="MAX_TOKENS" for candidate in initial.get("candidates",[])):
            raise ApiPaused("MODEL_OUTPUT_TRUNCATED",{"response_saved":str(root/"initial.json")})
        state["initial_hash"]=digest(initial)
        if not (root/"initial-evaluation.json").exists():
            subject,valid,reason=workspace(source,root/"initial-workspace",initial_diff,case["product_paths"])
            if initial_error: reason=initial_error
            initial_evaluation=evaluate(subject if valid else source,case_id)
            initial_evaluation.update({"proposal_valid":valid,"reason":reason})
            save(root/"initial-evaluation.json",initial_evaluation)
        save(state_path,state)
        for arm in arms:
            if state["arms"].get(arm,{}).get("status")=="COMPLETE":
                continue
            branch=state["arms"].setdefault(arm,{"history":copy.deepcopy(history),"previous_witnesses":[],"step":0,"status":"RUNNING"})
            if branch.get("pending_step") is not None:
                pending=branch["pending_step"]
                response=proposal(client,branch["pending_history"],root/f"{arm}-proposal-{pending}.json")
                branch["step"]=pending
                branch["history"]=branch.pop("pending_history")
                branch.pop("pending_step")
                save(state_path,state)
            else:
                response=initial if branch["step"]==0 else json.loads((root/f"{arm}-proposal-{branch['step']}.json").read_text())
            diff,representation_error=response_diff(response,source,case["product_paths"])
            while True:
                subject,valid,reason=workspace(source,root/arm,diff,case["product_paths"])
                if representation_error: reason=representation_error
                if valid:
                    branch["last_valid_diff"]=diff
                    branch["last_valid_source"]=str(subject)
                elif branch.get("last_valid_source"):
                    subject=Path(branch["last_valid_source"])
                else:
                    subject=source
                feedback=probe_feedback(subject,case,arm,branch.get("last_valid_diff",""),mappings,branch["previous_witnesses"])
                feedback["proposal"]={"valid":valid,"reason":reason,"raw_proposal_hash":digest(response),"applied_diff_hash":digest(diff)}
                save(root/f"{arm}-feedback-{branch['step']}.json",feedback)
                branch["previous_witnesses"]=list(dict.fromkeys(branch["previous_witnesses"]+[item["probe_id"] for item in feedback["public_results"] if item["role"]=="V" and not item["passed"]]))
                if feedback["all_visible_pass"] or branch["step"]>=config["max_revisions"] or offline_diff is not None:
                    final=[run_probe(subject,probe) for probe in case["probes"] if probe["role"]=="E"]
                    known={item["probe_id"]:item for item in feedback["public_results"]}
                    audit=[known.get(probe["id"]) or run_probe(subject,probe) for probe in case["probes"] if probe["role"]=="V"]
                    common_ok=all(item["passed"] for item in feedback["public_results"])
                    common_ok=common_ok and all(item["passed"] for item in audit)
                    branch["final_audit"]=audit
                    branch.update({"status":"COMPLETE","final_holdout":final,"final_feedback":feedback,
                                   "joint_valid":bool(branch.get("last_valid_source")) and common_ok and all(item["passed"] for item in final)})
                    save(state_path,state)
                    break
                branch["pending_history"]=next_history(branch["history"],response,feedback)
                next_step=branch["step"]+1
                branch["pending_step"]=next_step
                save(state_path,state)
                response=proposal(client,branch["pending_history"],root/f"{arm}-proposal-{next_step}.json")
                branch["step"]=next_step
                branch["history"]=branch.pop("pending_history")
                branch.pop("pending_step")
                save(state_path,state)
                diff,representation_error=response_diff(response,source,case["product_paths"])
        state["status"]="COMPLETE"
        save(state_path,state)
    except ApiPaused as error:
        state["status"]="PAUSED"
        state["pause"]={"reason":error.reason,"details":error.details,"at":time.time()}
        save(state_path,state)
    return state

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",type=Path,default=ROOT/"configs/runtime.free.json")
    parser.add_argument("--cases",nargs="+",required=True)
    parser.add_argument("--replicate",default="r01")
    parser.add_argument("--arms",nargs="+",choices=["B","M","F","A","J"],default=["B","M"])
    parser.add_argument("--run-root",type=Path,required=True)
    parser.add_argument("--stage",choices=["formal","development","technical-smoke","offline-control"],default="formal")
    parser.add_argument("--offline-patch",type=Path)
    options=parser.parse_args()
    config=json.loads(options.config.read_text())
    for case_id in options.cases:
        state=run_pair(case_id,options.replicate,config,options.arms,options.run_root,options.stage,
                       options.offline_patch.read_text() if options.offline_patch else None)
        print(json.dumps({"case":case_id,"status":state.get("status"),"arms":{name:{"joint_valid":arm.get("joint_valid"),"revisions":arm.get("step")} for name,arm in state["arms"].items()}}),flush=True)
        if state.get("status")=="PAUSED":
            break

if __name__=="__main__":
    main()
