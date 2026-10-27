"""Reproduce published initial and retained patch verdicts without model access."""
import argparse,hashlib,json
from pathlib import Path
from gemma_paper.runner import ROOT,workspace
from gemma_paper.subjects import evaluate,load_case


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ids',nargs='*')
    options=parser.parse_args()
    artifact=Path(json.loads((ROOT/'configs/runtime.free.json').read_text())['artifact_root'])
    manifest=json.loads((artifact/'receipts/source_manifest.json').read_text())
    by_id={c['id']:c for c in manifest['cases']}
    patches=json.loads((artifact/'published-patches.json').read_text())
    rows=[];evaluated={}
    for patch in patches:
        if options.ids and patch['root'] not in options.ids:continue
        source=Path(by_id[patch['root']]['revisions']['buggy']['path'])
        path=ROOT/patch['diff_file']
        case=load_case(patch['root'])
        diff=path.read_text();key=(patch['root'],hashlib.sha256(diff.encode()).hexdigest())
        reused=key in evaluated
        if reused:valid,reason,evaluation=evaluated[key]
        else:
            subject,valid,reason=workspace(source,artifact/'runs/published-replay'/patch['root'],diff,case['product_paths'])
            evaluation=evaluate(subject if valid else source,patch['root'])
            evaluated[key]=(valid,reason,evaluation)
        outcome=valid and evaluation['all_pass']
        matches=outcome==patch['joint_valid']
        record={**patch,'actual_joint_valid':outcome,'matches':matches,'applicable':valid,'reason':reason,'evaluation':evaluation,'evaluation_reused_for_identical_diff':reused,'diff_sha256':key[1]}
        rows.append(record)
        print(json.dumps({k:record[k] for k in ['campaign','root','replicate','label','joint_valid','actual_joint_valid','matches']}),flush=True)
    output=artifact/'results/published-replay';output.mkdir(parents=True,exist_ok=True)
    (output/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
    summary={'records':len(rows),'unique_patches_evaluated':len(evaluated),'all_verdicts_match':all(row['matches'] for row in rows),'model_requests':0}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)
    if not rows or not summary['all_verdicts_match']:raise SystemExit(1)

if __name__=='__main__':main()
