"""Summarize measured outcomes, information controls, and nonduplicated usage."""
import argparse
import json
from collections import Counter
from pathlib import Path
from analyze_campaign import all_role, signature


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def classify(evaluation,response):
    if not evaluation.get('proposal_valid'):
        return 'generation_budget_exhausted' if any(c.get('finishReason')=='MAX_TOKENS' for c in response.get('candidates',[])) else 'invalid_proposal'
    if any(r['execution'].startswith('INFRA') for r in evaluation['results']):return 'infrastructure_failure'
    if evaluation['all_pass']:return 'passes_frozen_checks'
    if any(r['execution']=='PRODUCT_EXCEPTION' for r in evaluation['results']):return 'product_runtime_failure'
    return 'observed_contract_failure'


def usage(paths):
    counts=Counter()
    for path in paths:
        value=read(path,{})
        counts['saved_responses']+=1
        counts.update({key:val for key,val in value.get('usageMetadata',{}).items() if isinstance(val,(int,float))})
    return dict(counts)


def arm_record(folder, arm, branch, initial):
    feedback=[read(file) for file in sorted(folder.glob(arm+'-feedback-*.json'))]
    results=[result for item in feedback for result in item['public_results']]
    initial_feedback=feedback[0] if feedback else {}
    witnesses=[result for result in initial_feedback.get('public_results',[]) if result['role']=='V' and not result['passed'] and result['execution']=='VALID']
    final=branch.get('final_feedback',{})
    return {'root':folder.parent.name,'replicate':folder.name,'arm':arm,
            'complete':branch.get('status')=='COMPLETE','joint_valid':branch.get('joint_valid'),
            'initial_joint_valid':bool(initial and initial.get('proposal_valid') and initial['all_pass']),
            'revision_responses':len(list(folder.glob(arm+'-proposal-*.json'))),
            'invalid_revision_proposals':sum(not item['proposal']['valid'] for item in feedback[1:]),
            'last_proposal_valid':final.get('proposal',{}).get('valid'),
            'retained_product_patch':bool(branch.get('last_valid_source')),
            'new_visible_subject_calls':sum(item['new_subject_calls'] for item in feedback),
            'all_public_feedback_subject_calls':sum(result['subject_calls'] for result in results),
            'public_feedback_elapsed_seconds':sum(result['elapsed_seconds'] for result in results),
            'initial_new_subject_calls':initial_feedback.get('new_subject_calls'),
            'initial_valid_visible_witness':bool(witnesses),
            'initial_bank_exhausted':initial_feedback.get('bank_exhausted'),
            'initial_selected_ids':initial_feedback.get('selected_probe_ids'),
            'initial_unmapped':initial_feedback.get('unmapped'),
            'initial_mapped_phases':initial_feedback.get('mapped_patch_phases'),
            'revision_usage':usage(sorted(folder.glob(arm+'-proposal-*.json')))}


def aggregate(records):
    complete=[row for row in records if row['complete']]
    return {'complete':len(complete),'joint_valid':sum(bool(row['joint_valid']) for row in complete),
            'recovered':sum(not row['initial_joint_valid'] and bool(row['joint_valid']) for row in complete),
            'regressed':sum(row['initial_joint_valid'] and not row['joint_valid'] for row in complete),
            'revision_responses':sum(row['revision_responses'] for row in records),
            'revision_total_tokens':sum(row['revision_usage'].get('totalTokenCount',0) for row in records),
            'invalid_revision_proposals':sum(row['invalid_revision_proposals'] for row in records),
            'new_visible_subject_calls':sum(row['new_visible_subject_calls'] for row in records),
            'all_public_feedback_subject_calls':sum(row['all_public_feedback_subject_calls'] for row in records),
            'public_feedback_elapsed_seconds':sum(row['public_feedback_elapsed_seconds'] for row in records),
            'initial_valid_visible_witnesses':sum(row['initial_valid_visible_witness'] for row in records),
            'initial_bank_exhausted':sum(bool(row['initial_bank_exhausted']) for row in records),
            'initial_new_subject_calls':sum(row['initial_new_subject_calls'] or 0 for row in records),
            'initial_unmapped':sum(bool(row['initial_unmapped']) for row in records)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--artifact-root',type=Path,required=True)
    parser.add_argument('--require-complete',action='store_true')
    parser.add_argument("--run-root",type=Path)
    options=parser.parse_args()
    artifact=options.artifact_root
    output=artifact/'results/formal-v1'
    analysis=read(output/'analysis.json',{})
    report={'complete_main':analysis.get('complete_main',False),'complete_F':analysis.get('complete_F',False),'papers':{}}
    for paper,prefix,subset in [('cache','C',{'C1','C2','C3','C4'}),('time','T',{'T1','T4','T5','T6'})]:
        root=options.run_root or artifact/'runs/formal-v1'
        records=[];initials=[];pair_rows=[]
        for number in range(1,9):
            case_id=prefix+str(number)
            for replicate in ['r01','r02']:
                folder=root/case_id/replicate
                state=read(folder/'state.json',{})
                initial=read(folder/'initial-evaluation.json',{})
                if initial:
                    initials.append({'root':case_id,'replicate':replicate,'applicable':initial['proposal_valid'],
                                     'joint_valid':initial['proposal_valid'] and initial['all_pass'],
                                     'reason':initial['reason'],'classification':classify(initial,read(folder/'initial.json',{})),
                                     'Q0_U_pass':initial['proposal_valid'] and all_role(initial['results'],{'Q0','U'}),
                                     'V_pass':all_role(initial['results'],{'V'}),'E_pass':all_role(initial['results'],{'E'}),
                                     'failures':[{'probe':r['probe_id'],'execution':r['execution']} for r in initial['results'] if not r['passed']]})
                for arm,branch in state.get('arms',{}).items():
                    records.append(arm_record(folder,arm,branch,initial))
                b=read(folder/'B-feedback-0.json');m=read(folder/'M-feedback-0.json')
                if b and m:
                    pair_rows.append({'root':case_id,'replicate':replicate,'same_feedback':signature(b)==signature(m),
                                      'same_selected_order':b['selected_probe_ids']==m['selected_probe_ids']})
        all_responses=[file for case_id in [prefix+str(n) for n in range(1,9)] for file in (root/case_id).glob('*/*.json') if file.name=='initial.json' or '-proposal-' in file.name]
        ledger=artifact/'api'/(paper+'-attempts.jsonl')
        events=[json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
        relevant=[event for event in events if any('/runs/'+campaign+'/'+prefix in (event.get('request_tag') or '') for campaign in ['formal-v1','formal-c3-semantic-v1'])]
        finishes=[event for event in relevant if event['event']=='attempt_finished']
        gross_usage=Counter()
        for event in finishes:gross_usage.update({k:v for k,v in event.get('usage',{}).items() if isinstance(v,(int,float))})
        stats={'initials':initials,'arms':{arm:aggregate([r for r in records if r['arm']==arm]) for arm in ['B','M','F']},
               'matched_F_subset':{arm:aggregate([r for r in records if r['arm']==arm and r['root'] in subset and r['replicate']=='r01']) for arm in ['B','M','F']},
               'matched_F_subset_initial_valid':sum(row['joint_valid'] for row in initials if row['root'] in subset and row['replicate']=='r01'),
               'records':records,'feedback_pairs':pair_rows,
               'unique_saved_response_usage':usage(all_responses),
               'http_usage':{'usage_including_superseded_C3':dict(gross_usage),'generation_attempts':sum(event['event']=='attempt_started' for event in relevant),
                             'finished_generation_attempts':len(finishes),'http_statuses':dict(Counter(str(e.get('http_status',e.get('status'))) for e in finishes)),
                             'inference_elapsed_seconds':sum(e.get('elapsed_seconds',0) for e in finishes),
                             'known_price_usd':sum(e.get('known_price_usd',0) for e in finishes)},
               'strata':{}}
        for label,ids in [('privacy',set('C'+str(n) for n in [1,3,4,5,6,7,8])),('origin_integrity',{'C2'})] if paper=='cache' else [('temporal',set('T'+str(n) for n in range(1,9)))]:
            stats['strata'][label]={'natural_roots':len(ids),'initial_valid':sum(r['joint_valid'] for r in initials if r['root'] in ids),
                                  'initial_observed':sum(r['root'] in ids for r in initials),
                                  'arms':{arm:aggregate([r for r in records if r['arm']==arm and r['root'] in ids]) for arm in ['B','M']}}
        primary_cpu=artifact/'receipts'/('cpu-diagnostics-'+paper+'-primary.json')
        diagnostics=read(primary_cpu if primary_cpu.exists() else artifact/'receipts'/('cpu-diagnostics-'+paper+'.json'),[])
        stats['cpu_diagnostics']={kind:{arm:{'patches':len([r for r in diagnostics if r['patch_kind']==kind and r['arm']==arm]),
                                                           'found_visible_witness':sum(r['found_visible_witness'] for r in diagnostics if r['patch_kind']==kind and r['arm']==arm),
                                                           'subject_calls':sum(r['new_subject_calls'] for r in diagnostics if r['patch_kind']==kind and r['arm']==arm)} for arm in ['B','M','A','F']} for kind in ['control','natural_initial']}
        report['papers'][paper]=stats
    information=[]
    for root in ['T1','T4','T5','T6']:
        for replicate in ['r01','r02']:
            initial=read(artifact/'runs/formal-v1'/root/replicate/'initial-evaluation.json')
            if initial:information.append({'root':root,'replicate':replicate,'condition':'policy_and_Q0','applicable':initial['proposal_valid'],'joint_valid':initial['proposal_valid'] and initial['all_pass'],'classification':classify(initial,read(artifact/'runs/formal-v1'/root/replicate/'initial.json',{}))})
            for condition in ['policy_without_Q0','Q0_without_added_policy']:
                result=read(artifact/'runs/time-information-v1'/root/replicate/condition/'evaluation.json')
                if result:information.append({'root':root,'replicate':replicate,'condition':condition,'applicable':result['proposal_valid'],'joint_valid':result['joint_valid'],'classification':classify({**result['evaluation'],'proposal_valid':result['proposal_valid']},read(artifact/'runs/time-information-v1'/root/replicate/condition/'response.json',{})),
                                              'failures':[{'probe':r['probe_id'],'execution':r['execution']} for r in result['evaluation']['results'] if not r['passed']]})
    report['information_controls']={'complete':len(information)==24,'rows':information,
                                     'usage_extra_responses':usage(list((artifact/'runs/time-information-v1').glob('*/*/*/response.json')))}
    transfer=[]
    transfer_root=artifact/'runs/transfer-initials-26b-v1'
    for case in ['C1','C3','T1','T6']:
        folder=transfer_root/case/'r01'
        state=read(folder/'state.json',{})
        initial=read(folder/'initial-evaluation.json',{})
        response=read(folder/'initial.json',{})
        if initial:
            transfer.append({'root':case,'model':'gemma-4-26b-a4b-it','initial_applicable':initial['proposal_valid'],
                             'initial_joint_valid':initial['proposal_valid'] and initial['all_pass'],
                             'source_sha':state.get('source_sha'),'classification':classify(initial,response),
                             'finish_reasons':[c.get('finishReason') for c in response.get('candidates',[])],
                             'usage':response.get('usageMetadata')})
    report['secondary_model']={'complete':len(transfer)==4,'protocol':'INITIAL_ONLY_EXPLORATORY_SCOPE_AMENDMENT',
                               'rows':transfer,'usage':usage(list(transfer_root.glob('*/*/initial.json')))}
    secondary_events=[]
    for paper in ['cache','time']:
        for line in (artifact/'api'/(paper+'-attempts.jsonl')).read_text().splitlines():
            event=json.loads(line)
            if any('/runs/'+campaign+'/' in (event.get('request_tag') or '') for campaign in ['transfer-26b-v1','transfer-initials-26b-v1']):secondary_events.append(event)
    secondary_finished=[e for e in secondary_events if e['event']=='attempt_finished']
    gross_secondary=Counter()
    for event in secondary_finished:gross_secondary.update({k:v for k,v in event.get('usage',{}).items() if isinstance(v,(int,float))})
    report['secondary_model']['gross_http_usage_including_superseded_expansion']={'attempts':sum(e['event']=='attempt_started' for e in secondary_events),'usage':dict(gross_secondary),'known_price_usd':sum(e.get('known_price_usd',0) for e in secondary_finished)}
    report['preparation_excluded_from_formal_results']={'generation_attempts':20,'manual_tool_smoke_attempts_included':2,'manual_tool_smoke_tokens':220,'source':'docs/execution/acceptance_20261027.json'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'complete_main':report['complete_main'],'complete_F':report['complete_F'],
                      'information_observed':len(information),'secondary_initials_observed':len(transfer),'output':str(output/'report.json')}))
    if options.require_complete and not(report['complete_main'] and report['complete_F'] and report['information_controls']['complete'] and report['secondary_model']['complete']):raise SystemExit(75)

if __name__=='__main__':main()
