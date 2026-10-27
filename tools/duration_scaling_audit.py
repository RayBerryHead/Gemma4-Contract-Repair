"""Check one newly observed public-operation regression without changing v1 scores."""
import hashlib,json,subprocess,sys
from pathlib import Path
from gemma_paper.runner import ROOT,digest,response_diff,workspace

PROGRAM='''import json,sys
from pathlib import Path
p=Path(sys.argv[1]);sys.path[:0]=[str(p/'src'),str(p)]
import pendulum
value=pendulum.duration(hours=24)
print(json.dumps({'input_total_seconds':value.total_seconds(),'half_seconds':(value*0.5).total_seconds(),'divided_by_two_seconds':(value/2).total_seconds()}))
'''


def main():
    artifact=Path(json.loads((ROOT/'configs/runtime.free.json').read_text())['artifact_root'])
    source=next(c for c in json.loads((artifact/'receipts/source_manifest.json').read_text())['cases'] if c['id']=='T5')
    base=Path(source['revisions']['buggy']['path'])
    case=json.loads((ROOT/'configs/cases/T5.json').read_text())
    pool=[('upstream_'+role,Path(item['path'])) for role,item in source['revisions'].items()]
    published=artifact/'published-patches.json'
    if published.exists():
        for patch in json.loads(published.read_text()):
            if patch['root']!='T5':continue
            diff=(ROOT/patch['diff_file']).read_text()
            path,valid,_=workspace(base,artifact/'runs/scaling-pool',diff,case['product_paths'])
            label=patch['replicate']+'_'+patch['label']
            if patch.get('campaign')!='formal-v1':label=patch['campaign']+'_'+label
            if valid:pool.append((label,path))
    else:
        for folder in (artifact/'runs/formal-v1/T5').glob('r*'):
            if (folder/'initial.json').exists():
                diff,error=response_diff(json.loads((folder/'initial.json').read_text()),base,case['product_paths'])
                path,valid,_=workspace(base,artifact/'runs/scaling-pool',diff,case['product_paths'])
                if valid:pool.append((folder.name+'_initial',path))
            state=json.loads((folder/'state.json').read_text()) if (folder/'state.json').exists() else {}
            for arm,branch in state.get('arms',{}).items():
                if branch.get('status')=='COMPLETE' and branch.get('last_valid_source'):
                    pool.append((folder.name+'_'+arm+'-retained',Path(branch['last_valid_source'])))
        for result_file in (artifact/'runs/time-information-v1/T5').glob('*/*/evaluation.json'):
            result=json.loads(result_file.read_text())
            if not result['proposal_valid']:continue
            folder=result_file.parent
            diff,error=response_diff(json.loads((folder/'response.json').read_text()),base,case['product_paths'])
            path=folder/'subject'/('patch-'+digest(diff)[:16])
            assert (path/'.paper-applied.json').exists()
            pool.append(('time-information-v1_'+folder.parent.name+'_'+folder.name,path))
    rows=[]
    for label,path in pool:
        result=subprocess.run([sys.executable,'-c',PROGRAM,str(path)],capture_output=True,text=True)
        observed=json.loads(result.stdout) if result.returncode==0 else {'execution':'PRODUCT_EXCEPTION','error':result.stderr.strip().splitlines()[-1]}
        row={'label':label,'product_sha256':hashlib.sha256(b''.join((path/name).read_bytes() for name in case['product_paths'])).hexdigest(),
             'observed':observed,'passed':observed=={'input_total_seconds':86400.0,'half_seconds':43200.0,'divided_by_two_seconds':43200.0}}
        rows.append(row);print(json.dumps(row),flush=True)
    assert all(row['passed'] for row in rows if row['label'] in {'upstream_buggy','upstream_fixed'})
    record={'status':'EXPLORATORY_AFTER_T5_R01','natural_roots':1,'new_model_calls':0,'changes_formal_v1_scores':False,'program':PROGRAM,'rows':rows}
    (artifact/'receipts/T5_fractional_duration_exploration.json').write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':main()
