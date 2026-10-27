"""Render inspectable paper figures from frozen cases and measured campaign rows."""
import argparse,csv,json,os
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument("--artifact-root",type=Path,required=True)
parser.add_argument("--source-root",type=Path,required=True)
parser.add_argument("--output",type=Path,required=True)
options=parser.parse_args()
os.environ.setdefault("MPLCONFIGDIR",str(options.artifact_root/"report-cache/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
options.output.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"savefig.facecolor":"white"})
def box(ax,x,y,width,height,text,color="#e8eef6",edge="#34445b"):
    patch=FancyBboxPatch((x,y),width,height,boxstyle="round,pad=0.012,rounding_size=0.015",facecolor=color,edgecolor=edge,linewidth=1.1)
    ax.add_patch(patch);ax.text(x+width/2,y+height/2,text,ha="center",va="center",linespacing=1.45)
def arrow(ax,x1,y1,x2,y2):
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),arrowprops={"arrowstyle":"->","color":"#34445b","lw":1.6})
fig,ax=plt.subplots(figsize=(11,3.4));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis("off")
box(ax,.02,.38,.21,.42,"1. Alice warms\na private cache\n\nbody: Alice\nSet-Cookie: Alice")
box(ax,.28,.38,.20,.42,"Shared store\ncontains the\nprivate entry")
box(ax,.53,.38,.20,.42,"2. Bob reads\nthrough shared cache\n\nPatch drops\nSet-Cookie")
box(ax,.78,.38,.20,.42,"Observed at Bob\n\nbody: Alice\nSet-Cookie: absent","#fde9e7","#a83a35")
for start,end in [(.23,.28),(.48,.53),(.73,.78)]:arrow(ax,start,.59,end,.59)
ax.text(.02,.96,"A natural repair hides the cookie but still replays Alice's body",fontsize=14,fontweight="bold",va="top")
ax.text(.02,.12,"Measured C1/r01 initial patch: 2 public requests, 1 origin call.\nReference fix and B final patch: Bob receives Bob's body; 2 origin calls.",fontsize=10,va="center")
fig.savefig(options.output/"cache-warm-state.png",dpi=220,bbox_inches="tight");plt.close(fig)

case=json.loads((options.source_root/"configs/cases/T5.json").read_text())
day=next(p for p in case["probes"] if p["role"]=="Q0")
hours=next(p for p in case["probes"] if p["role"]=="V" and p["params"].get("duration")=={"hours":24})
fig,ax=plt.subplots(figsize=(10,3.4));ax.axis("off");ax.set_xlim(0,1);ax.set_ylim(0,1)
ax.text(.02,.96,"Source contracts require opposite temporal choices",fontsize=14,fontweight="bold",va="top")
box(ax,.03,.38,.28,.40,"Pendulum duration(days=1)\n"+day["expected"]["wall"]+"\n"+str(day["expected"]["elapsed"]//3600)+" elapsed hours")
box(ax,.36,.38,.28,.40,"Pendulum duration(hours=24)\n"+hours["expected"]["wall"]+"\n24 elapsed hours")
box(ax,.69,.38,.28,.40,"APScheduler DST wait\n01:59:59 to 03:00:00\n1 elapsed second")
ax.text(.03,.14,"Reference behaviors from T5/T6 fixed-version replays.\nCalendar preservation and elapsed-time preservation are distinct obligations.",va="center")
fig.savefig(options.output/"time-policy-duals.png",dpi=220,bbox_inches="tight");plt.close(fig)
initial_file=options.artifact_root/"runs/formal-v1/T5/r01/initial-evaluation.json"
reference_file=options.artifact_root/"receipts/case_replays/T5.json"
if initial_file.exists() and reference_file.exists():
    reference=json.loads(reference_file.read_text())
    initial=json.loads(initial_file.read_text())
    probes=[day["id"],hours["id"]]
    measured=[("Upstream buggy",reference["buggy"]),("Gemma initial (r01)",initial),("Upstream reference",reference["fixed"])]
    fig,ax=plt.subplots(figsize=(10,4));ax.axis("off");ax.set_xlim(0,1);ax.set_ylim(0,1)
    ax.text(.02,.98,"A passing day repair can turn 24 hours into 23",fontsize=14,fontweight="bold",va="top")
    ax.text(.43,.81,"duration(days=1)",ha="center",fontweight="bold")
    ax.text(.79,.81,"duration(hours=24)",ha="center",fontweight="bold")
    for index,(label,data) in enumerate(measured):
        y=.58-index*.19
        ax.text(.02,y+.06,label,va="center")
        for column,probe_id in enumerate(probes):
            result=next(r for r in data["results"] if r["probe_id"]==probe_id)
            value=result["observed"]
            box(ax,.28+column*.36,y,.30,.13,value["wall"]+"\n"+str(value["elapsed"]//3600)+" elapsed hours", "#e5f2ed" if result["passed"] else "#fde9e7")
    ax.text(.02,.025,"Measured T5: start 2017-03-11 10:45, America/Los_Angeles.\nThe natural initial patch fixes the day reproducer but breaks the hour contrast. Green = declared contract passes.",fontsize=9,va="center")
    fig.savefig(options.output/"time-measured-contrast.png",dpi=220,bbox_inches="tight");plt.close(fig)

scaling_file=options.artifact_root/"receipts/T5_fractional_duration_exploration.json"
contrast_file=options.artifact_root/"results/time-contrast-v1/summary.json"
state_file=options.artifact_root/"runs/formal-v1/T5/r01/state.json"
if scaling_file.exists() and contrast_file.exists() and state_file.exists():
    scaling={r["label"]:r for r in json.loads(scaling_file.read_text())["rows"]}
    contrasts={r["label"]:r for r in json.loads(contrast_file.read_text())["rows"]}
    state=json.loads(state_file.read_text())
    labels=[("Upstream reference","upstream_fixed","upstream_fixed",True),("Gemma B retained","r01_B-retained","r01_B_retained",state["arms"]["B"].get("joint_valid")),("Gemma M retained","r01_M-retained","r01_M_retained",state["arms"]["M"].get("joint_valid"))]
    if all(a in scaling and b in contrasts for _,a,b,_ in labels):
        fig,ax=plt.subplots(figsize=(11,3.7));ax.axis("off");ax.set_xlim(0,1);ax.set_ylim(0,1)
        ax.text(.02,.98,"Passing day/hour checks does not preserve duration arithmetic",fontsize=14,fontweight="bold",va="top")
        for x,label in [(.39,"Frozen suite"),(.62,"30 unit contrasts"),(.86,"24 hours x 0.5")]:ax.text(x,.79,label,ha="center",fontweight="bold")
        for index,(label,key,contrast,passed) in enumerate(labels):
            y=.56-index*.18;ax.text(.02,y+.055,label,va="center")
            box(ax,.29,y,.20,.12,"PASS" if passed else "FAIL","#e5f2ed" if passed else "#fde9e7")
            row=contrasts[contrast];box(ax,.52,y,.20,.12,str(row["passed"])+" / "+str(row["total"]),"#e5f2ed" if row["passed"]==row["total"] else "#fde9e7")
            row=scaling[key];box(ax,.75,y,.22,.12,format(row["observed"]["half_seconds"],",.0f")+" seconds","#e5f2ed" if row["passed"] else "#fde9e7")
        ax.text(.02,.025,"Exploratory T5/r01: the public scaling operation was outside the frozen suite.\nExpected half of 24 hours: 43,200 seconds. Primary pass verdicts remain unchanged.",fontsize=9,va="center")
        fig.savefig(options.output/"time-residual-scaling.png",dpi=220,bbox_inches="tight");plt.close(fig)

analysis_file=options.artifact_root/"results/formal-v1/analysis.json"
if analysis_file.exists():
    analysis=json.loads(analysis_file.read_text())
    if analysis.get("complete_main"):
        rows=list(csv.DictReader((analysis_file.parent/"root_outcomes.csv").open()))
        for paper,prefix in [("cache","C"),("time","T")]:
            fig,ax=plt.subplots(figsize=(9,5))
            columns=[("initial","r01"),("initial","r02"),("B","r01"),("B","r02"),("M","r01"),("M","r02"),("F","r01")]
            for i in range(8):
                root_id=prefix+str(i+1)
                for j,(arm,replicate) in enumerate(columns):
                    matches=[r for r in rows if r["root_id"]==root_id and r["replicate"]==replicate and (r["arm"]==arm or arm=="initial" and r["arm"]=="B")]
                    value=(matches[0]["initial_joint_valid"] if arm=="initial" else matches[0]["joint_valid"]) if matches else ""
                    if value=="True":color="#287c65";symbol="1"
                    elif value=="False":color="#bc5047";symbol="0"
                    else:color="#eeeeee";symbol="-"
                    ax.add_patch(plt.Rectangle((j-.45,i-.38),.9,.76,facecolor=color,edgecolor="white"))
                    ax.text(j,i,symbol,ha="center",va="center",color="white" if value in {"True","False"} else "#555",fontweight="bold")
            ax.set_xlim(-.6,len(columns)-.4);ax.set_ylim(7.6,-.6)
            ax.set_xticks(range(len(columns)),[a+"\n"+r for a,r in columns])
            ax.set_yticks(range(8),[prefix+str(i+1)+(" *" if paper=="cache" and i==1 else "") for i in range(8)])
            ax.set_title("Contract-valid outcomes by natural root and draw",loc="left",fontweight="bold",pad=18)
            for spine in ax.spines.values():spine.set_visible(False)
            ax.tick_params(length=0,pad=8)
            fig.text(.02,.01,"1 = valid; 0 = invalid; - = not in the F subset. Initial is shared within each paired block." + ("  * C2: origin integrity." if paper=="cache" else ""),fontsize=8)
            fig.savefig(options.output/(paper+"-outcomes.png"),dpi=220,bbox_inches="tight");plt.close(fig)
print(json.dumps({"output":str(options.output),"figures":[p.name for p in options.output.glob("*.png")]}))
