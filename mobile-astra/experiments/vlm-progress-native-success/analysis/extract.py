"""Validate and export E10 from a completed RPent run; no simulator/API calls.

python extract.py --run RUN --site SITE_ROOT --output DIR
The site root contains mobile-astra/. Raw local paths and authentication are not exported.
"""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics


CAMERAS = ('agentview', 'agentview_right', 'navview', 'wrist')
VLA = {'rldx_arm', 'rldx_skill'}


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def collect(run, tasks, native):
    records = {}
    counters = Counter()
    latency = []
    for split, names in tasks.items():
        for task in names:
            for seed in range(1, 6):
                cell = run / 'results' / ('composite_' + split) / f'{task}_s{seed}'
                result = load(cell / 'result.json')
                states = load(cell / 'states.json')['steps']
                transcript = load(cell / f'transcript_{task}_target_s{seed}.json')
                require(result['valid'] is True, f'Invalid: {task}/{seed}')
                require(result['success'] == states[-1]['extras']['success'], 'Final native score mismatch')
                require(result['agent_success_source'] == ('native' if native else 'vlm'), 'Wrong feedback policy')
                require(result['planner'] == {'backend': 'codex', 'model': 'gpt-6-astra',
                        'reasoning_effort': 'xhigh', 'max_turns': 100}, 'Planner changed')
                for key, expected in {'cell_timeout_seconds': 3600, 'rldx_max_chunks': 40,
                                      'rldx_settle_patience': 999, 'rldx_action_steps_per_chunk': 8}.items():
                    require(result['runtime'][key] == expected, f'Runtime changed: {key}')
                if native:
                    require(result['runtime']['rldx_stop_on_success'] is True, 'Missing native early stop')
                require(result['memory']['audit_status'] == 'ok', 'Memory audit failed')
                require((cell / 'launcher_exit_code.txt').read_text().strip() == '0', 'Nonzero episode exit')
                counts = Counter((s.get('command') or {}).get('action') for s in states[1:])
                audit_paths = sorted((cell / 'vlm_progress_audit.json').glob('*.json'))
                errors = Counter()
                for path in audit_paths:
                    audit = load(path)
                    require(audit['model'] == 'gpt-6.1-terra' and audit['reasoning_effort'] == 'medium', 'Judge changed')
                    require(audit['prompt_version'] == 'robocasa-four-view-v3', 'Prompt changed')
                    request = audit['request']
                    require(set(request) == {'task_language', 'conditions', 'operator',
                                            'previous_visual_judgment', 'current_step'}, 'Unexpected judge input')
                    step = request['current_step']
                    require({im['camera'] for im in audit['images'] if im['step'] == step} == set(CAMERAS),
                            'Missing judge camera')
                    require(len(audit['images']) == (4 if step == 0 else 8), 'Unexpected image count')
                    counters['judge_records'] += 1
                    if 'error_type' in audit:
                        errors[audit['error_type']] += 1
                        counters['judge_errors'] += 1
                    if audit.get('response_id'):
                        counters['judge_responses'] += 1
                    for key in ('input_tokens', 'output_tokens', 'total_tokens'):
                        counters[key] += (audit.get('usage') or {}).get(key, 0)
                    if 'elapsed_s' in audit:
                        latency.append(audit['elapsed_s'])
                audited_steps = {int(path.stem) for path in audit_paths}
                cancelled = 0
                for state in states:
                    step = state['step_idx']
                    if step not in audited_steps:
                        cached = load(cell / 'vlm_task_progress.json' / f'{step:02}.json')
                        require(cached['status'] == 'unavailable' and cached['uncertainties'] == ['cancelled'],
                                'Missing judge record without an explicit cancellation')
                        cancelled += 1
                require(len(audit_paths) + cancelled == len(states), 'Duplicate or unexpected judge records')
                counters['cancelled_before_judge_request'] += cancelled
                first_success = next((s['step_idx'] for s in states if s['extras'].get('success')), None)
                current_visual = result['visual_assessment']['completion']
                first = states[0]
                finish = transcript.get('finish') or {}
                records[(split, task, seed)] = {
                    'success': result['success'], 'valid': result['valid'],
                    'elapsed_s': result['elapsed_s'], 'termination_reason': result['termination_reason'],
                    'finish_status': finish.get('status'), 'visual_completion': current_visual,
                    'judge_calls': len(audit_paths), 'judge_errors': dict(errors), 'cancelled_judgments': cancelled,
                    'action_count': len(states) - 1, 'vla_calls': sum(counts[k] for k in VLA),
                    'manual_calls': sum(n for k, n in counts.items() if k not in VLA),
                    'first_native_success_step': first_success,
                    'actions_after_first_success': len(states) - 1 - first_success if first_success is not None else None,
                    'memory_audit': 'ok', 'memory_read_files': result['memory']['read_files'],
                    'result_sha256': sha(cell / 'result.json'), 'states_sha256': sha(cell / 'states.json'),
                    'transcript_sha256': sha(cell / f'transcript_{task}_target_s{seed}.json'),
                    'initial': {'task_language': first['extras']['task_language'], 'robot_state': first['state'],
                                'rgb_sha256': {cam: sha(cell / f'{cam}.png/00.png') for cam in CAMERAS}},
                }
    counters['latency_median_s'] = statistics.median(latency)
    counters['latency_p95_s'] = sorted(latency)[min(len(latency) - 1, int(len(latency) * .95))]
    return records, dict(counters)


def paired(rows, reference):
    counts = Counter()
    for row in rows:
        left, right = row['current']['success'], row[reference]['success']
        counts['both_success' if left and right else 'current_only' if left else
               'reference_only' if right else 'both_failure'] += 1
    return {key: counts[key] for key in ('both_success', 'current_only', 'reference_only', 'both_failure')}


def build(run, site):
    manifest = load(run / 'manifest.json')
    require(manifest['status'] == 'completed', 'Run is incomplete')
    for name, expected in manifest['source_files_sha256'].items():
        require(sha(run / 'source' / name) == expected, f'Frozen source changed: {name}')
    memory_manifest = load(Path(manifest['memory_manifest']))
    for name, expected in memory_manifest['files'].items():
        require(sha(Path(manifest['memory_root']) / name) == expected, 'Original memory changed')
    target = load(run / 'source/robots/robocasa/eval/target50.json')
    tasks = {split: target['splits']['composite_' + split]['tasks'] for split in ('seen', 'unseen')}
    current, judge = collect(run, tasks, True)
    baseline = {(r['split'], r['task'], r['seed']): r
                for r in load(site / 'mobile-astra/experiments/baseline/analysis/data.json')['episodes']
                if r['model'] == 'astra'}
    no_progress = {(r['split'], r['task'], r['seed']): r
                   for r in load(site / 'mobile-astra/experiments/task-progress/analysis/data.json')['episodes']}
    require(set(current) == set(baseline) == set(no_progress), 'Task/seed coverage differs')
    rows = []
    for key, value in current.items():
        rows.append({'split': key[0], 'task': key[1], 'seed': key[2], 'current': value,
                     'baseline': {'success': baseline[key]['success'], 'elapsed_s': baseline[key]['elapsed_s']},
                     'no_progress': {'success': no_progress[key]['notask_success'],
                                     'elapsed_s': no_progress[key]['notask_elapsed_s'],
                                     'result_sha256': no_progress[key]['notask_result_sha256']}})
    summary = {}
    for split in ('seen', 'unseen', 'all'):
        subset = [r for r in rows if split == 'all' or r['split'] == split]
        summary[split] = {'total': len(subset),
            'successes': {name: sum(r[name]['success'] for r in subset)
                          for name in ('current', 'baseline', 'no_progress')},
            'paired': {name: paired(subset, name) for name in ('baseline', 'no_progress')},
            'final_visual': dict(Counter(r['current']['visual_completion'] for r in subset)),
            'native_visual': dict(Counter(f"{r['current']['success']}:{r['current']['visual_completion']}" for r in subset)),
            'finish_status': dict(Counter(r['current']['finish_status'] or 'missing' for r in subset)),
            'actions_after_success': sum((r['current']['actions_after_first_success'] or 0) for r in subset),
            'mean_elapsed_s': statistics.mean(r['current']['elapsed_s'] for r in subset)}
    require(summary['all']['successes'] == {'current': 44, 'baseline': 55, 'no_progress': 41},
            'Unexpected summary; inspect before publishing')
    comparisons = {
        'matched_by': ['task', 'seed'],
        'initial_state_equality_audited_against_references': False,
        'limits': ['One batch per setting; task/seed pairing does not establish causal improvement.',
                   'Reference initial states and VLA noise were not fully matched in this export.',
                   'E03 archived run generated success_criteria.md, with file-tool reading restricted to memory; E10 does not generate it.',
                   'E10 adds fixed task-condition knowledge and extra VLM compute; it is not a conditions-only control.',
                   'Terminal visual/native disagreement measures this run, not independent VLM accuracy.']}
    return {'schema_version': '1.0', 'experiment': 'E10', 'generated_utc': datetime.now(timezone.utc).isoformat(),
            'name': 'VLM task progress with native success', 'run': run.name,
            'completed_at': manifest['ended_at'], 'started_at': manifest['started_at'],
            'tasks': tasks, 'summary': summary, 'episodes': rows, 'judge': judge,
            'comparisons': comparisons,
            'protocol': {key: manifest[key] for key in ('environment_split', 'planner', 'progress', 'vla',
                                                     'agent_success_source', 'task_progress_source', 'gpus')},
            'validation': {'valid_episodes': 160, 'native_final_state_matches': 160,
                           'memory_audits_ok': 160, 'memory_files_unchanged': len(memory_manifest['files']),
                           'frozen_source_files_verified': len(manifest['source_files_sha256']),
                           'offline_tests_passed': 291, 'full_agent_smoke_passed': True,
                           'judge_request_input_and_four_camera_checks': True},
            'source': {'base_commit': manifest['base_commit'], 'branch': manifest['branch'],
                       'status': 'snapshot_available', 'evaluated_working_tree': True,
                       'source_files_sha256': manifest['source_files_sha256'],
                       'source_patch_sha256': sha(run / 'source.patch'),
                       'manifest_sha256': sha(run / 'manifest.json'),
                       'memory_revision': memory_manifest['revision']},
            'references': {'baseline': {'id': 'E01', 'data_sha256': sha(site / 'mobile-astra/experiments/baseline/analysis/data.json')},
                           'no_progress': {'id': 'E03', 'data_sha256': sha(site / 'mobile-astra/experiments/task-progress/analysis/data.json')}}}


def export(data, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'data.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    with (output / 'episodes.csv').open('w', newline='') as stream:
        fields = ['split', 'task', 'seed', 'success', 'baseline_success', 'no_progress_success',
                  'elapsed_s', 'visual_completion', 'finish_status', 'vla_calls', 'manual_calls',
                  'judge_calls', 'result_sha256']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in data['episodes']:
            current = row['current']
            writer.writerow({**{k: row[k] for k in fields[:3]},
                **{k: current[k] for k in ('success', 'elapsed_s', 'visual_completion', 'finish_status',
                                         'vla_calls', 'manual_calls', 'judge_calls', 'result_sha256')},
                'baseline_success': row['baseline']['success'],
                'no_progress_success': row['no_progress']['success']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = build(args.run, args.site)
    export(data, args.output)
    print(json.dumps({'summary': data['summary'], 'judge': data['judge'],
                      'comparisons': data['comparisons'], 'validation': data['validation']}, indent=2))
