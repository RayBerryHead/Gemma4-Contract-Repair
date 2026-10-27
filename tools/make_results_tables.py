"""Render final tables from complete root records without guessing missing cells."""
import argparse,json
from collections import Counter
from pathlib import Path

LABELS={
'C1':'Undici: existing Set-Cookie entry','C2':'Undici: redirect origin *','C3':'Django: Authorization','C4':'Django: cookie creation',
'C5':'django-graphex: user identity','C6':'Django: session renewal','C7':'Undici: empty private directive','C8':'Django: qualified directives',
'T1':'Arrow: original month anchor','T2':'croniter: caller zone','T3':'dateutil: POSIX ordinal','T4':'Pendulum: global calendar',
'T5':'Pendulum: duration units','T6':'APScheduler: elapsed wait','T7':'Luxon: keepLocalTime','T8':'date-fns: complete local days'}


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifact-root',type=Path,required=True);options=parser.parse_args()
    output=options.artifact_root/'results/formal-v1'
    analysis=json.loads((output/'analysis.json').read_text());report=json.loads((output/'report.json').read_text())
    assert analysis['complete_main'] and analysis['complete_F'] and report['information_controls']['complete'] and report['secondary_model']['complete'],'Do not publish incomplete tables.'
    sections={}
    for paper,prefix in [('cache','C'),('time','T')]:
        data=report['papers'][paper];stats=analysis['papers'][paper];rows=[]
        for number in range(1,9):
            root=prefix+str(number);initial=[r for r in data['initials'] if r['root']==root]
            counts=[str(sum(r['joint_valid'] for r in initial))+'/2']
            for arm in ['B','M','F']:
                selected=[r for r in data['records'] if r['root']==root and r['arm']==arm]
                counts.append(str(sum(bool(r['joint_valid']) for r in selected))+'/'+str(len(selected)) if selected else '—')
            rows.append([root+' '+LABELS[root],*counts])
        main_table=table(['Root / task','Initial','B','M','F (r01)'],rows)
        subset=[]
        for arm in ['B','M','F']:
            row=data['matched_F_subset'][arm]
            subset.append([arm,str(row['joint_valid'])+'/4',row['new_visible_subject_calls'],row['all_public_feedback_subject_calls'],format(row['public_feedback_elapsed_seconds'],'.2f'),row['revision_responses'],format(row['revision_total_tokens'],',')])
        f_table=table(['Controller','Passes','New V subject calls','All public-feedback subject calls','Feedback execution seconds','Revision responses','Provider total revision tokens'],subset)
        initial_class=dict(Counter(r['classification'] for r in data['initials']))
        sections[paper]={'main_table':main_table,'matched_F_table':f_table,'initial_classes':initial_class,
                         'initial_valid':stats['initial_joint_valid'],'initial_apparent':stats['apparent_passes'],
                         'apparent_broader_failures':stats['apparent_passes']-stats['initial_joint_valid'],
                         'apparent_E_failures':stats['apparent_pass_hidden_fail'],'paired_outcomes':stats['pairs'],
                         'same_initial_feedback_pairs':stats['same_initial_feedback_pairs'],
                         'same_feedback_discordant_outcomes':stats['same_feedback_discordant_outcomes'],
                         'arms':stats['arms'],'strata':data['strata'],'http_usage':data['http_usage'],
                         'saved_primary_response_usage':data['unique_saved_response_usage'],
                         'cpu_diagnostics':data['cpu_diagnostics']}
        (output/(paper+'_tables.md')).write_text(main_table+'\n\nMatched four-root/r01 subset:\n\n'+f_table+'\n')
    info=report['information_controls']['rows'];conditions=['policy_and_Q0','policy_without_Q0','Q0_without_added_policy']
    rows=[]
    for root in ['T1','T4','T5','T6']:
        rows.append([root]+[str(sum(r['joint_valid'] for r in info if r['root']==root and r['condition']==condition))+'/2' for condition in conditions])
    rows.append(['All four roots']+[str(sum(r['joint_valid'] for r in info if r['condition']==condition))+'/8' for condition in conditions])
    sections['information']={'table':table(['Root','Policy + Q0','Policy, no Q0','Q0, no added card'],rows),
                             'classes':{c:dict(Counter(r['classification'] for r in info if r['condition']==c)) for c in conditions},
                             'extra_usage':report['information_controls']['usage_extra_responses']}
    sections['secondary']=report['secondary_model']
    (output/'manuscript_sections.json').write_text(json.dumps(sections,indent=2)+'\n')
    print(json.dumps({'output':str(output/'manuscript_sections.json'),'main_draws':32,'main_B_M_branches':64,'F_branches':8,'information_cells':len(info),'secondary_initials':len(report['secondary_model']['rows'])}))

if __name__=='__main__':main()
