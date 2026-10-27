"""Explore the observed T5 unit collapse across thirty explicit contrast inputs."""
import hashlib
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from gemma_paper.runner import ROOT,digest,response_diff,workspace
from gemma_paper.subjects import run_probe


def probes():
    events={'America/New_York':['2021-03-14','2021-11-07'],
            'Europe/Paris':['2021-03-28','2021-10-31'],
            'Australia/Sydney':['2021-04-04','2021-10-03']}
    result=[]
    for zone,dates in events.items():
        starts=[]
        for date in dates:
            boundary=datetime.fromisoformat(date).replace(hour=10,minute=45,tzinfo=ZoneInfo(zone))
            starts.extend([(boundary-timedelta(days=1),1,'transition'),(boundary,-1,'transition')])
        starts.append((datetime(2021,1,15,10,45,tzinfo=ZoneInfo(zone)),1,'normal_day_control'))
        for start,direction,kind in starts:
            for unit,magnitude in [('days',direction),('hours',24*direction)]:
                duration=timedelta(**{unit:magnitude})
                end=start+duration if unit=='days' else (start.astimezone(timezone.utc)+duration).astimezone(start.tzinfo)
                result.append({'id':'T5-X-'+str(len(result)+1).zfill(2),'case':'T5','role':'X',
                               'params':{'date':[start.year,start.month,start.day,start.hour,start.minute],
                                         'zone':zone,'duration':{unit:magnitude}},
                               'expected':{'wall':end.strftime('%Y-%m-%d %H:%M'),'elapsed':int(end.timestamp()-start.timestamp())},
                               'predicate':'subset','cost':1,'tags':[kind,unit]})
    assert len(result)==30
    return result


def main():
    artifact=Path(json.loads((ROOT/'configs/runtime.free.json').read_text())['artifact_root'])
    source=next(c for c in json.loads((artifact/'receipts/source_manifest.json').read_text())['cases'] if c['id']=='T5')
    subjects=[('upstream_buggy',Path(source['revisions']['buggy']['path'])),('upstream_fixed',Path(source['revisions']['fixed']['path']))]
    case=json.loads((ROOT/'configs/cases/T5.json').read_text())
    published=artifact/'published-patches.json'
    if published.exists():
        for patch in json.loads(published.read_text()):
            if patch['root']!='T5':continue
            diff=(ROOT/patch['diff_file']).read_text()
            path,valid,_=workspace(subjects[0][1],artifact/'runs/contrast-pool',diff,case['product_paths'])
            label=patch['replicate']+'_'+patch['label'].replace('-','_')
            if patch.get('campaign')!='formal-v1':label=patch['campaign']+'_'+label
            if valid:subjects.append((label,path))
    else:
        for folder in sorted((artifact/'runs/formal-v1/T5').glob('r*')):
            response_file=folder/'initial.json'
            if response_file.exists():
                diff,error=response_diff(json.loads(response_file.read_text()),subjects[0][1],case['product_paths'])
                path,valid,_=workspace(subjects[0][1],artifact/'runs/contrast-pool'/folder.name,diff,case['product_paths'])
                if valid:subjects.append((folder.name+'_initial',path))
            state=json.loads((folder/'state.json').read_text()) if (folder/'state.json').exists() else {}
            for arm,value in state.get('arms',{}).items():
                if value.get('status')=='COMPLETE' and value.get('last_valid_source'):
                    subjects.append((folder.name+'_'+arm+'_retained',Path(value['last_valid_source'])))
        for result_file in (artifact/'runs/time-information-v1/T5').glob('*/*/evaluation.json'):
            result=json.loads(result_file.read_text())
            if not result['proposal_valid']:continue
            folder=result_file.parent
            diff,error=response_diff(json.loads((folder/'response.json').read_text()),subjects[0][1],case['product_paths'])
            path=folder/'subject'/('patch-'+digest(diff)[:16])
            assert (path/'.paper-applied.json').exists()
            subjects.append(('time-information-v1_'+folder.parent.name+'_'+folder.name,path))
    output=artifact/'results/time-contrast-v1';output.mkdir(parents=True,exist_ok=True)
    bank=probes();(output/'probes.json').write_text(json.dumps(bank,indent=2)+'\n')
    rows=[]
    for label,path in subjects:
        product_digest=hashlib.sha256(b''.join((path/name).read_bytes() for name in case['product_paths'])).hexdigest()
        file=output/(label+'.json')
        cached=json.loads(file.read_text()) if file.exists() else {}
        if cached.get('product_sha256')==product_digest:record=cached
        else:
            results=[run_probe(path,probe) for probe in bank]
            record={'label':label,'root':'T5','product_sha256':product_digest,'passed':sum(r['passed'] for r in results),'total':len(bank),'results':results}
            file.write_text(json.dumps(record,indent=2)+'\n')
        rows.append({k:v for k,v in record.items() if k!='results'})
        print(json.dumps(rows[-1]),flush=True)
    reference=next(r for r in rows if r['label']=='upstream_fixed')
    assert reference['passed']==reference['total'],'Exploratory oracle disagrees with source authority; do not report model comparisons.'
    (output/'summary.json').write_text(json.dumps({'status':'EXPLORATORY','natural_roots':1,'inputs_per_patch':30,'new_model_calls':0,'rows':rows},indent=2)+'\n')

if __name__=='__main__':main()
