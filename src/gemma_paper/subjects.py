"""Replay frozen case probes without exposing independent evaluation data to models."""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def verdict(probe: dict, result: dict) -> bool:
    if result.get("execution") != "VALID":
        return False
    value = result["observed"]
    kind = probe["predicate"]
    if kind == "equal":
        return value == probe["expected"]
    if kind == "subset":
        return all(value.get(key) == expected for key, expected in probe["expected"].items())
    if kind == "public_origin_reuse":
        return value["bodies"]==probe["expected"] and value["origin_calls"]==1
    if kind == "redirect_integrity":
        return value["bodies"] == probe["expected"] and value["origin_calls"] >= 2
    if kind == "no_session_created":
        return all(item["cookie"] is None for item in value["responses"]) and value["origin_calls"]==1
    if kind == "lifecycle_cookie_isolation":
        return value["responses"][-1]["cookie"] != "session-for-"+probe["params"].get("owner","alice") and all(item["body"]=="public-body" for item in value["responses"])
    if kind == "session_not_replayed":
        return value["responses"][0]["cookie"] is not None and value.get("owner_preserved",False) and value["responses"][1]["cookie"] is None
    if kind == "cookie_isolation":
        cookies = [item["cookie"] for item in value["responses"]]
        return all(cookies) and len(set(cookies)) == len(cookies) and value["origin_calls"]==len(cookies)
    if kind in {"actor_isolation", "private_reuse"}:
        expected = probe["params"].get("actors", [])
        if probe["case"] in {"C1", "C7"}:
            expected = ["response for " + actor for actor in expected]
        if kind == "private_reuse" and probe["case"] == "C5":
            expected = probe["params"]["actors"]
        actual = [item["body"] for item in value["responses"]]
        correct = actual == expected

        if probe["case"]=="C1":
            correct = correct and [item.get("cookie") for item in value["responses"]]==["session-for-"+actor for actor in probe["params"]["actors"]]
        return correct and (value["origin_calls"] == 1 if kind == "private_reuse" else True)
    if kind == "public_reuse":
        return value["origin_calls"] == 1 and all(item["body"] == "public" for item in value["responses"])
    raise ValueError("Unknown verdict predicate: " + kind)

def run_probe(source: Path, probe: dict, timeout: int = 45) -> dict:
    node = probe["case"] in {"C1","C2","C7","T7","T8","CD1","CD2"}
    command = ["node", str(ROOT/"fixtures/probe_node.cjs")] if node else [sys.executable, str(ROOT/"fixtures/probe_python.py")]
    environment = dict(os.environ)
    for name in list(environment):
        if any(token in name.upper() for token in ("API_KEY", "ACCESS_TOKEN", "SECRET")):
            environment.pop(name)
    environment.update({"PYTHONNOUSERSITE":"1","OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","TZ":"America/New_York"})
    start = time.monotonic()
    try:
        completed = subprocess.run(command, input=json.dumps({"case":probe["case"],"source":str(source),"params":probe["params"]}),
                                   text=True, capture_output=True, timeout=timeout, env=environment, cwd=source)
        lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
        result = json.loads(lines[-1]) if lines else {"execution":"INFRA_ERROR","error":completed.stderr[-2500:]}
    except subprocess.TimeoutExpired:
        result = {"execution":"INFRA_TIMEOUT"}
    except Exception as error:
        result = {"execution":"INFRA_ERROR","error_type":type(error).__name__,"error":str(error)}
    shown_input=dict(probe["params"])
    if probe["case"]=="C1" and shown_input.get("lifecycle"):
        shown_input.update({"warm_actor":"warm-public","owner":shown_input.get("owner","alice"),
                            "reader":shown_input.get("reader","bob"),
                            "sequence":"warm public entry; trigger conditional revalidation or stale-while-revalidate; await replacement; read as another actor"})
    return {**result, "probe_id":probe["id"], "role":probe["role"],
            "passed":verdict(probe,result), "elapsed_seconds":time.monotonic()-start, "subject_calls":probe["cost"],
            "input":shown_input,"expected":probe["expected"],"contract_check":probe["predicate"],"tags":probe.get("tags",[])}

def load_case(case_id: str) -> dict:
    return json.loads((ROOT/"configs/cases"/(case_id+".json")).read_text())

def evaluate(source: Path, case_id: str, roles: set[str] | None = None) -> dict:
    specification = load_case(case_id)
    roles = roles if roles is not None else {"Q0","V","E","U"}
    results = [run_probe(source, probe) for probe in specification["probes"] if roles is None or probe["role"] in roles]
    return {"id":case_id,"results":results,"all_pass":bool(results) and all(item["passed"] for item in results),
            "infra_ok":all(not item["execution"].startswith("INFRA") for item in results)}
