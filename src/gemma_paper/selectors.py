"""Fixed, inspectable probe ordering; no hidden test or gold-patch inputs."""
from __future__ import annotations
import ast
import calendar
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

def signature(value):
    return json.dumps(value, sort_keys=True)

def predictions(probe: dict) -> dict:
    params = probe["params"]
    case = probe["case"]
    if case == "T1" and params.get("frame", "month") == "month":
        start = datetime.fromisoformat(params["start"])
        count = params.get("count", 4)
        sequential = []
        day = start.day
        for offset in range(count):
            absolute = start.year * 12 + start.month - 1 + offset
            year, month = divmod(absolute, 12)
            month += 1
            day = min(day, calendar.monthrange(year, month)[1])
            sequential.append(f"{year:04d}-{month:02d}-{day:02d}")
        return {"sequential_clipping": sequential}
    if case == "T2":
        start = datetime.fromisoformat(params["start"])
        if params.get("zone"):
            start = start.replace(tzinfo=ZoneInfo(params["zone"])).astimezone(timezone.utc)
        return {"utc_phase": list(range(start.hour % 5, 24, 5))}
    if case == "T3":
        match = re.fullmatch(r"STD0DST-1,([J]?\d+)/0,([J]?\d+)/0", params["rule"])
        if not match:
            return {}
        def shifted_day(rule, year):
            julian = rule.startswith("J")
            number = int(rule.lstrip("J"))
            offset = number-1 if julian else number-1
            if julian and calendar.isleap(year) and number >= 59:
                offset += 1
            return date(year,1,1)+timedelta(days=offset)
        labels = []
        for value in params["dates"]:
            current = datetime.fromisoformat(value).date()
            start = shifted_day(match[1],current.year)
            end = shifted_day(match[2],current.year)
            labels.append("DST" if start <= current < end else "STD")
        return {"legacy_ordinal_shift": labels}
    if case == "T4":
        year, month, day = params["date"]
        wrong_weekday = (params.get("weekday", 0) + params["firstweekday"]) % 7
        matching = [day for day in range(1,calendar.monthrange(year,month)[1]+1) if datetime(year, month, day).weekday()==wrong_weekday]
        wrong_day = matching[-1] if params.get("method")=="last_of" else matching[params.get("n",1)-1] if params.get("method")=="nth_of" else matching[0]
        return {"global_layout_index": {"date":f"{year:04d}-{month:02d}-{wrong_day:02d}","global_unchanged":True},
                "global_reset": {**probe["expected"],"global_unchanged":False}}
    if case == "T5":
        start = datetime(*params["date"], tzinfo=ZoneInfo(params["zone"]))
        duration = timedelta(**params["duration"])
        elapsed = datetime.fromtimestamp(start.timestamp() + duration.total_seconds(), start.tzinfo)
        wall = start + duration
        return {"all_elapsed": {"wall":elapsed.strftime("%Y-%m-%d %H:%M"),"elapsed":int(duration.total_seconds())},
                "all_wall": {"wall":wall.strftime("%Y-%m-%d %H:%M"),"elapsed":int(wall.timestamp()-start.timestamp())}}
    if case == "T6":
        start = datetime.fromisoformat(params["start"])
        end = datetime.fromisoformat(params["end"])
        return {"wall_difference": max((end-start).total_seconds(), 0)}
    if case == "T7":
        fields=params["date"]
        source=datetime(fields["year"],fields["month"],fields["day"],fields["hour"],fields["minute"],tzinfo=ZoneInfo(params["source_zone"]))
        target=source.astimezone(ZoneInfo(params["target_zone"]))
        if params["keep_local"]:
            return {"preserve_instant": {"wall":target.strftime("%Y-%m-%d %H:%M")}}
        return {"preserve_wall": {"instant_preserved":False}}
    if case == "T8":
        start = datetime(*[params["start"][0], params["start"][1]+1, *params["start"][2:]], tzinfo=ZoneInfo("America/New_York"))
        end = datetime(*[params["end"][0], params["end"][1]+1, *params["end"][2:]], tzinfo=start.tzinfo)
        return {"elapsed_day_blocks": int((end.timestamp()-start.timestamp())/86400)}
    return {}

def select_probe(pending: list[dict], arm: str, covered: set[str], changed_phases: set[str],
                 active_hypotheses: set[str] | None = None) -> dict:
    neighbors = {"store":{"read","revalidate","invalidate"}, "read":{"store","revalidate"},
                 "identity/key":{"store","read","redirect"}, "redirect":{"identity/key","store"},
                 "revalidate":{"store","read"}}
    residual = set().union(*(neighbors.get(phase,set()) for phase in changed_phases))-changed_phases
    def scores(probe):
        tags = set(probe.get("tags",[]))
        gain = len(tags-covered)/max(len(tags),1)
        cost = probe["cost"]
        baseline = (1+gain)/cost
        if probe["case"].startswith("C"):
            boost = bool(tags & (residual if arm=="M" else changed_phases)) if arm in {"M","A"} else False
            return ((1+gain+int(boost))/cost, baseline)
        if arm in {"M","A"}:
            values = predictions(probe)
            if active_hypotheses is not None and arm=="M":
                values = {name:value for name,value in values.items() if name in active_hypotheses}
            allowed = signature(probe["expected"])
            distinct = {signature(value) for value in values.values()} - {allowed}
            return (len(distinct)/cost, baseline)
        return (baseline, baseline)
    if arm=="M" and pending and not pending[0]["case"].startswith("C"):
        if all(scores(probe)[0]==0 for probe in pending):
            return select_probe(pending,"B",covered,changed_phases)
    return min(pending,key=lambda probe:(-scores(probe)[0],-scores(probe)[1],probe["id"]))

def compile_phase_map(source: Path, product_paths: list[str]) -> list[dict]:
    responsibilities = {
        "process_response":"store", "process_request":"read",
        "onResponseStart":"store", "onResponseEnd":"store",
        "onRequestStart":"identity/key", "handleResult":"read",
        "parseCacheControlHeader":"identity/key", "makeCacheKey":"identity/key",
        "get_cache_key":"identity/key", "_get_cache_key":"identity/key",
        "invalidate_cache":"invalidate", "dispatch":"read",
    }
    mappings=[]
    for relative in product_paths:
        file=source/relative
        if not file.exists():
            continue
        content=file.read_text()
        if relative.endswith(".py"):
            for node in ast.walk(ast.parse(content)):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in responsibilities:
                    mappings.append({"path":relative,"start":node.lineno,"end":node.end_lineno,
                                     "phase":responsibilities[node.name],"symbol":node.name})
        else:
            lines=content.splitlines()
            declarations=[]
            pattern=re.compile(r"^(\s*)(?:async\s+)?(?:function\s+)?([A-Za-z_$][\w$]*)\s*\([^;]*")
            for index,line in enumerate(lines,1):
                match=pattern.match(line)
                if match and match[2] not in {"if","for","while","switch","catch"}:
                    declarations.append((index,len(match[1]),match[2]))
            for position,(start,indent,name) in enumerate(declarations):
                if name not in responsibilities:
                    continue
                end=next((line-1 for line,other_indent,_ in declarations[position+1:] if other_indent <= indent),len(lines))
                mappings.append({"path":relative,"start":start,"end":end,
                                 "phase":responsibilities[name],"symbol":name})
    return mappings

def patch_phases(diff: str, mappings: list[dict]) -> set[str]:
    phases=set()
    current=None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current=line[6:]
        match=re.match(r"@@ -(\d+)(?:,(\d+))? \+",line)
        if match and current:
            start=int(match[1]);end=start+max(int(match[2] or "1"),1)-1
            for mapping in mappings:
                if mapping["path"]==current and start <= mapping["end"] and end >= mapping["start"]:
                    phases.add(mapping["phase"])
    return phases

def project_observation(probe: dict, observed):
    if probe["predicate"]=="subset":
        return {key:observed.get(key) for key in probe["expected"]}
    return observed
