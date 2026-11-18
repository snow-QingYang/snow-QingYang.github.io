#!/usr/bin/env python3
"""Recompute Agent takeover counts from canonical trajectories, without running models.

python extract.py --site PATH_TO_MOBILE_ASTRA --sources LOCAL_SOURCES_JSON --output DIR
Sources JSON maps E02/E03/E05/E06/E07/E08/E11 to {"root": RUN}, and E04/E10 to
{"archive": ZIP, "prefix": "results"}. Roots may also use a "prefix".
E01 uses the reviewed per-episode baseline traces in the site checkout.
Only selected numerical fields, action names and hashes are exported. Local paths,
RGB, memory, task text, tool arguments and model messages are not published.
"""
import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

VLA = {'rldx_skill', 'rldx_arm'}
MANUAL = {'move_to', 'move_delta', 'move_base', 'navigate_to', 'rotate_pitch',
          'set_gripper', 'release', 'scripted_grasp', 'execute_action'}
IDS = ['E01','E02','E03','E04','E05','E06','E07','E08','E10','E11']
PREFIXES = {'E02':'da3','E03':'notask','E04':'nocontact','E05':'nogeom','E07':'nomemory'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text())


def key(row):
    return row['split'], row['task'], row['seed']


def reference(row, eid):
    if eid in PREFIXES:
        prefix = PREFIXES[eid]
        return {k: row[f'{prefix}_{k}'] for k in ['success','result_sha256','states_sha256']}
    if eid == 'E06':
        return {'success':row['agent_success'],'result_sha256':row['result_sha256']}
    if eid == 'E08':
        return row['combined']
    if eid == 'E10':
        return row['current']
    return row


def classify(actions, success, timeline_available):
    assert type(success) is bool
    assert all(a['method'] in VLA | MANUAL for a in actions)
    first_success = next((a['step'] for a in actions if a.get('native_success') is True), None)
    if timeline_available and success:
        assert first_success is not None, 'Successful trajectory has no success step'
    attributed = [a for a in actions if first_success is None or a['step'] <= first_success]
    va = [a for a in attributed if a['method'] in VLA]
    ma = [a for a in attributed if a['method'] in MANUAL]
    post = [a for a in ma if va and a['step'] > va[0]['step']]
    path = 'takeover' if post else 'setup' if ma and va else 'vla_only' if va else 'manual_only' if ma else 'no_actions'
    assert path not in {'manual_only','no_actions'} or not success, 'Review new success category'
    takeover_success = success and path == 'takeover'
    return {
        'success':success, 'path':path, 'takeover_attempted':bool(post),
        'takeover_success':takeover_success,
        'confirmed_pre_success_takeover':takeover_success if timeline_available else None,
        'timeline_available':timeline_available,
        'first_vla_step':va[0]['step'] if va else None,
        'first_intervention_step':post[0]['step'] if post else None,
        'first_native_success_step':first_success,
        'vla_calls':len(va),'manual_calls':len(ma),
        'completion_actor':('vla' if attributed[-1]['method'] in VLA else 'manual') if success and attributed else None,
        'completion_actor_scope':'first_native_success' if timeline_available else 'last_action_before_final_score',
        'last_attributed_action':attributed[-1]['method'] if attributed else None,
        'actions':actions,
    }


def summarize(rows):
    successful = [r for r in rows if r['success']]
    takeovers = [r for r in successful if r['takeover_success']]
    return {
        'episodes':len(rows),'success':len(successful),
        'takeover_attempts':sum(r['takeover_attempted'] for r in rows),
        'takeover_success':len(takeovers),
        'takeover_then_vla_success':sum(r['completion_actor']=='vla' for r in takeovers),
        'takeover_then_manual_success':sum(r['completion_actor']=='manual' for r in takeovers),
        'vla_only_success':sum(r['path']=='vla_only' for r in successful),
        'setup_success':sum(r['path']=='setup' for r in successful),
    }


def build(site, sources):
    status = load(site/'project-status.json')
    settings = {e['id']:e for e in status['completed_experiments']}
    expected_keys = None
    experiments, evidence = [], {}
    for eid in IDS:
        setting = settings[eid]
        folder = site / setting['path']
        export = folder/('data.json' if eid=='E11' else 'analysis/data.json')
        published = load(export)
        ref_rows = [r for r in published['episodes'] if eid!='E01' or r['model']=='astra']
        refs = {key(r):reference(r,eid) for r in ref_rows}
        assert len(refs)==160 and len(ref_rows)==160, eid
        if expected_keys is None: expected_keys=set(refs)
        assert set(refs)==expected_keys, (eid,'task/seed coverage')
        evidence[eid] = {'export_sha256':digest(export.read_bytes())}
        if eid!='E01':
            source = sources[eid]
            archive = zipfile.ZipFile(source['archive']) if 'archive' in source else None
            if archive:
                evidence[eid]['archive_sha256'] = digest(Path(source['archive']).read_bytes())
            prefix = source.get('prefix','').strip('/')
            def read_cell(cell, name):
                relative = '/'.join(s for s in [prefix,cell,name] if s)
                return archive.read(relative) if archive else (Path(source['root'])/relative).read_bytes()
        rows=[]
        for split,task,seed in sorted(refs):
            ref=refs[split,task,seed]
            if eid=='E01':
                path=folder/'analysis/cases'/f'astra--{task}--{seed}.json'
                detail=load(path)
                assert detail['success']==ref['success'] and detail['valid'] is True
                actions=[{'step':a['step'],'method':a['method'],'native_success':a['success']}
                         for a in detail['trace']]
                row=classify(actions,ref['success'],True)
                assert row['takeover_success']==(ref['category']=='repair')
                assert row['vla_calls']==ref['vla_calls'] and row['manual_calls']==ref['manual_calls']
                hashes={'result_sha256':detail['source']['files']['result.json'],
                        'states_sha256':detail['source']['files']['states.json'],
                        'trace_export_sha256':digest(path.read_bytes())}
                evidence_mode='reviewed_action_trace'
            else:
                cell=f'composite_{split}/{task}_s{seed}'
                rb=read_cell(cell,'result.json');sb=read_cell(cell,'states.json')
                result=json.loads(rb);states=json.loads(sb)['steps']
                assert digest(rb)==ref['result_sha256'],(eid,cell,'result hash')
                states_hash_match = 'newly_recorded'
                if ref.get('states_sha256'):
                    if digest(sb)==ref['states_sha256']:
                        states_hash_match='raw_bytes'
                    else:
                        # Published ZIPs reformat JSON; reconstruct the original
                        # serialization and require its exact published hash.
                        recovered = [json.dumps(json.loads(sb), indent=2, ensure_ascii=a).encode()
                                     for a in (False, True)]
                        assert any(digest(b)==ref['states_sha256'] for b in recovered),(eid,cell,'states hash')
                        states_hash_match='json_serialization_only'
                assert result['valid'] is True and result['success']==ref['success'],(eid,cell,'result')
                assert result['task_name']==task and result['seed']==seed
                assert result['evaluation_split']=='composite_'+split
                assert all(states[i]['step_idx']<states[i+1]['step_idx'] for i in range(len(states)-1))
                timeline=eid!='E06'
                if timeline:
                    assert all(type(s['extras'].get('success')) is bool for s in states),(eid,cell,'success timeline')
                    assert states[-1]['extras']['success']==result['success']
                    assert states[0]['extras']['success'] is False,(eid,cell,'initial success')
                else:
                    assert result['success_source']=='env.check_success_after_planner'
                    assert all('success' not in s['extras'] for s in states)
                actions=[]
                for s in states:
                    action=(s.get('command') or {}).get('action')
                    if action is None:continue
                    assert action in VLA|MANUAL,(eid,cell,'unknown recorded action',action)
                    actions.append({'step':s['step_idx'],'method':action,'native_success':s['extras'].get('success')})
                row=classify(actions,result['success'],timeline)
                hashes={'result_sha256':digest(rb),'states_sha256':digest(sb),
                        'published_states_sha256':ref.get('states_sha256'),
                        'states_hash_verification':states_hash_match}
                evidence_mode='archived_native_states' if archive else 'canonical_native_states'
            row.update({'experiment':eid,'split':split,'task':task,'seed':seed,
                        'evidence_mode':evidence_mode,**hashes})
            rows.append(row)
        if eid!='E01' and archive:archive.close()
        summary={split:summarize([r for r in rows if split=='all' or r['split']==split])
                 for split in ['seen','unseen','all']}
        assert summary['all']['success']==setting['success'],(eid,'success total')
        for s in summary.values():
            assert s['success']==s['takeover_success']+s['vla_only_success']+s['setup_success']
            assert s['takeover_success']==s['takeover_then_vla_success']+s['takeover_then_manual_success']
        experiments.append({'id':eid,'name':setting.get('name',setting['source']['name']),
                            'path':setting['path'],'status':'final_score_proxy' if eid=='E06' else 'verified',
                            'scope_note':('No per-step success timeline; counts physical intervention after VLA followed by final native success. Cannot establish that success had not occurred before intervention.' if eid=='E06' else 'Physical intervention after VLA and before first native success; final native result must be successful.'),
                            'summary':summary,'episodes':rows})
    p=settings['E12']
    experiments.append({'id':'E12','name':'Pure VLA','path':p['path'],'status':'not_applicable',
                        'scope_note':'No Planner or manual takeover. Not applicable, rather than zero successful repairs.',
                        'summary':{s:{'episodes':80 if s!='all' else 160,'takeover_success':None} for s in ['seen','unseen','all']},'episodes':[]})
    return {'schema_version':1,'generated_utc':datetime.now(timezone.utc).isoformat(),
            'metric_id':'post_vla_physical_takeover_success_v1',
            'label':'Agent 接管后成功',
            'definition':'VLA action followed by a non-VLA physical action and final native success. With a native success timeline, only actions through the first success count; intervention before the first VLA is preparation, not takeover. E06 has final scoring only and is separately marked.',
            'exclusions':['Read-only queries','Memory/file reads and writes','finish declarations','VLA continuation without non-VLA physical actions','Preparation only before the first VLA call'],
            'limitations':['Describes an observed path, not proof that VLA alone would fail.','VLA-only paths still include Planner scheduling.','E06 lacks a per-step success timeline and is a final-score proxy.','E09 is withheld. E12 is not applicable.','Each setting is a separate batch; initial states and VLA sampling are not fully controlled.'],
            'coverage':{'planner_experiments':10,'planner_episodes':1600,'native_timeline_episodes':1440,'final_score_only_episodes':160},
            'evidence':evidence,'experiments':experiments}


def write(data,out):
    out.mkdir(parents=True,exist_ok=True)
    (out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    summary=[];episodes=[]
    for e in data['experiments']:
        for split,s in e['summary'].items():
            summary.append({'experiment':e['id'],'name':e['name'],'status':e['status'],'split':split,**s})
        episodes.extend({k:v for k,v in r.items() if k!='actions'} for r in e['episodes'])
    for filename,rows in [('summary.csv',summary),('episodes.csv',episodes)]:
        fields=list(dict.fromkeys(k for r in rows for k in r))
        with (out/filename).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,required=True)
    parser.add_argument('--sources',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    data=build(args.site,load(args.sources));write(data,args.output)
    for e in data['experiments']:
        print(e['id'], e['status'], {k:v['takeover_success'] for k,v in e['summary'].items()})

if __name__=='__main__':main()
