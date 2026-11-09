#!/usr/bin/env python3
"""Export E07 public statistics without transcripts, credentials or local paths.

python extract.py --run-root NO_MEMORY_RUN --baseline-root BASELINE_RUN \
  --baseline-data ../../baseline/analysis/data.json --output .
Optional: --memory-audit AUDIT_SUMMARY_JSON; otherwise discover the run summary.
"""
import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def percent(count, total):
    return str((Decimal(count) * 100 / Decimal(total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def episode(root, split, task, seed, no_memory=False):
    folder = root / f'composite_{split}' / f'{task}_s{seed}'
    result = read(folder / 'result.json')
    steps = read(folder / 'states.json')['steps']
    label = f'{split}/{task}/s{seed}'
    require(result['valid'] is True and type(result['success']) is bool, f'Invalid result: {label}')
    require((result['evaluation_split'], result['task_name'], result['seed']) == (f'composite_{split}', task, seed), f'Cell mismatch: {label}')
    require(result['protocol_id'] == 'robocasa-harness-vla-v2' and result['environment_split'] == 'target' and result['success_source'] == 'state.success', f'Protocol mismatch: {label}')
    require(result['planner'] == {'backend': 'codex', 'model': 'gpt-6-astra', 'reasoning_effort': 'xhigh', 'max_turns': 100}, f'Planner mismatch: {label}')
    require(result['runtime'] == {'cell_timeout_seconds': 3600, 'rldx_max_chunks': 40, 'rldx_settle_patience': 999, 'rldx_action_steps_per_chunk': 8}, f'Runtime mismatch: {label}')
    require(result['termination_reason'] in ('completed', 'planner_timeout'), f'Invalid termination: {label}')
    require(steps and [s['step_idx'] for s in steps] == list(range(len(steps))), f'State history mismatch: {label}')
    require(type(steps[-1]['extras']['success']) is bool and steps[-1]['extras']['success'] == result['success'], f'Final native score mismatch: {label}')
    require(math.isfinite(result['elapsed_s']) and result['elapsed_s'] >= 0, f'Invalid elapsed time: {label}')
    if no_memory:
        m = result['memory']
        require(m['policy'] == 'none' and m['selected_files'] == [] and m['read_files'] == [] and m['audit_status'] == 'ok', f'Memory audit mismatch: {label}')
        require((folder / 'launcher_exit_code.txt').read_text().strip() == '0', f'CLI exit mismatch: {label}')
    return {'success': result['success'], 'elapsed_s': result['elapsed_s'], 'termination_reason': result['termination_reason'],
            'final_native_success': steps[-1]['extras']['success'], 'result_sha256': digest(folder / 'result.json'),
            'states_sha256': digest(folder / 'states.json')}, steps[0]


def initial_comparison(a, b):
    require(a['state'].keys() == b['state'].keys(), 'Initial robot state keys differ')
    differences = []
    for key, values in a['state'].items():
        other = b['state'][key]
        require(isinstance(values, list) and isinstance(other, list) and len(values) == len(other), 'Initial state shape differs')
        require(all(type(v) in (int, float) and math.isfinite(v) for v in values + other), 'Nonfinite initial state')
        differences.extend(abs(x-y) for x, y in zip(values, other))
    require(bool(differences), 'Empty initial robot state')
    return {'initial_robot_state_max_abs_diff': max(differences), 'initial_robot_state_exact_equal': a['state'] == b['state'],
            'initial_task_language_equal': a['extras']['task_language'] == b['extras']['task_language']}


def summarize(rows):
    return {'total': len(rows), 'baseline_success': sum(r['baseline_success'] for r in rows),
            'nomemory_success': sum(r['nomemory_success'] for r in rows),
            'both_success': sum(r['baseline_success'] and r['nomemory_success'] for r in rows),
            'baseline_only': sum(r['baseline_success'] and not r['nomemory_success'] for r in rows),
            'nomemory_only': sum(not r['baseline_success'] and r['nomemory_success'] for r in rows),
            'neither': sum(not r['baseline_success'] and not r['nomemory_success'] for r in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('run-root', 'baseline-root', 'baseline-data', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--memory-audit', type=Path)
    args = parser.parse_args()
    baseline = read(args.baseline_data)
    refs = {(r['split'], r['task'], r['seed']): r for r in baseline['episodes'] if r['model'] == 'astra'}
    expected = {(split, task, seed) for split, tasks in baseline['tasks'].items() for task in tasks for seed in range(1, 6)}
    require(len(expected) == 160 and set(refs) == expected, 'Baseline coverage mismatch')
    validation = read(args.run_root / 'validation.json')
    require(validation['valid_cells'] == validation['expected_cells'] == 160, 'Final validation mismatch')
    for root in (args.run_root, args.baseline_root):
        found = {(p.parent.parent.name.removeprefix('composite_'), p.parent.name.rsplit('_s', 1)[0], int(p.parent.name.rsplit('_s', 1)[1])) for p in root.glob('composite_*/*/result.json')}
        require(found == expected, 'Actual result set differs from canonical 160 cells')
    rows = []
    for split, tasks in baseline['tasks'].items():
        for task in tasks:
            for seed in range(1, 6):
                b, b0 = episode(args.baseline_root, split, task, seed)
                n, n0 = episode(args.run_root, split, task, seed, True)
                require(b['success'] == refs[(split, task, seed)]['success'], 'Published baseline disagrees')
                rows.append({'split': split, 'task': task, 'seed': seed,
                             **{f'baseline_{k}': v for k, v in b.items()},
                             **{f'nomemory_{k}': v for k, v in n.items()}, **initial_comparison(b0, n0)})
    summary = {s: summarize([r for r in rows if s == 'all' or r['split'] == s]) for s in ('seen', 'unseen', 'all')}
    for split in ('seen', 'unseen'):
        require(summary[split]['nomemory_success'] == validation['splits'][f'composite_{split}']['successes'], 'Final score mismatch')
    require([summary[s]['nomemory_success'] for s in ('seen', 'unseen', 'all')] == [24, 17, 41], 'Unexpected E07 scores')
    provenance = read(args.run_root / 'source_revision.json')
    data = {'schema_version': 1, 'experiment': 'E07 NoMemory', 'generated_utc': datetime.now(timezone.utc).isoformat(),
            'completed_hkt': '2026-11-09T08:57:00+08:00', 'tasks': baseline['tasks'], 'summary': summary, 'episodes': rows,
            'sources': {'baseline': {'run': args.baseline_root.name, 'published_data_sha256': digest(args.baseline_data)},
                        'nomemory': {'run': args.run_root.name, 'base_commit': provenance['base_commit'],
                                     'source_files_sha256': provenance['source_files'], 'patch_sha256': digest(args.run_root / 'source.patch'),
                                     'manifest_sha256': digest(args.run_root / 'manifest.json'), 'validation_sha256': digest(args.run_root / 'validation.json')}},
            'initial_state_audit': {'pairs': 160, 'robot_state_threshold': 1e-6,
                'robot_state_differences': sum(r['initial_robot_state_max_abs_diff'] > 1e-6 for r in rows),
                'exact_robot_state_differences': sum(not r['initial_robot_state_exact_equal'] for r in rows),
                'task_language_differences': sum(not r['initial_task_language_equal'] for r in rows), 'all_scene_objects_checked': False},
            'validation': {'valid_results': 320, 'final_native_success_matches': 320, 'nomemory_exit_zero': 160,
                           'nomemory_empty_selected_files': 160, 'nomemory_empty_read_files': 160, 'nomemory_memory_audit_ok': 160},
            'memory_audit_scope': 'All 160 result memory audits report no selected/read files. The harness may internally validate/read the conventional corpus before returning empty memory; this does not deliver it to the Agent. This is not a claim of zero OS reads or complete shell/filesystem isolation.',
            'settings': {'removed': 'Historical task and global memory selection/supply; prompt states no historical memory; read_text_file rejects memory files.',
                         'retained': 'Current-episode history, geometry, contact, task progress, success, scoring source access, VLA inputs/control and native-success early stopping.'},
            'comparison_limits': ['One batch per setting and five seeds per task; no causal claim from individual outcome changes.',
                                  'Initial robot state and task text checked; full object state and independent VLA sampling are not matched.',
                                  'E07 and NoTaskGT both score 41/160 but remove different information.']}
    audit_paths = sorted(args.run_root.glob('final_memory_audit_summary_*.json'))
    memory_audit_path = args.memory_audit or (audit_paths[-1] if audit_paths else None)
    data['recorded_trajectory_audit'] = {'status': 'not_supplied'}
    if memory_audit_path:
        audit_doc = read(memory_audit_path)
        coverage, native, memory = audit_doc['trajectory_coverage'], audit_doc['native_shell'], audit_doc['memory_audit']
        require(audit_doc['results']['episodes'] == coverage['streams'] == 160 and coverage['parse_errors'] == [], 'Memory trajectory audit coverage mismatch')
        require(memory['historical_memory_read_attempts_observed'] == memory['historical_memory_reads_observed'] == 0, 'Memory trajectory audit reports historical reads')
        data['recorded_trajectory_audit'] = {
            'status': 'audited', 'source_sha256': digest(memory_audit_path),
            'streams': coverage['streams'], 'jsonl_events': coverage['jsonl_events'], 'parse_errors': 0,
            'native_shell_commands': native['count'], 'episodes_with_native_shell': native['episodes'],
            'native_shell_completed': native['completed'], 'native_shell_failed': native['failed'],
            'historical_memory_read_attempts_observed': memory['historical_memory_read_attempts_observed'],
            'historical_memory_reads_observed': memory['historical_memory_reads_observed'],
            'memory_reads_jsonl_count': memory['memory_reads_jsonl_count'], 'memory_reads_total_bytes': memory['memory_reads_total_bytes'],
            'source_content_read_or_search_attempts': audit_doc['source_inspection']['source_content_search_or_read_attempts'],
            'source_content_read_or_search_episodes': audit_doc['source_inspection']['source_content_search_or_read_episodes'],
            'tool_items_missing_completion_event': len(coverage['uncompleted_items']),
            'retryable_stream_errors': len(coverage['retryable_errors']),
            'scope': 'Recorded Agent trajectories including native shell; source/AGENTS/current-episode reads occurred and remain allowed. Not an OS syscall trace or a zero harness disk-I/O claim.'}
        data['memory_audit_scope'] = 'All 160 recorded Agent trajectories, including native shell commands, were audited: no historical task/global memory reads or attempts were observed. Source/AGENTS/current-episode reads occurred. Internal corpus validation is retained; this is not an OS-level non-access guarantee.'
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    with (args.output / 'episodes.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    lines = ['# E07 · NoMemory', '', 'GPT-6-Astra / xhigh · RLDX-1-FT-RC365 · 32 RoboCasa composite tasks × seeds 1–5.', '',
             '| Split | E01 baseline | E07 NoMemory | Difference |', '| --- | ---: | ---: | ---: |']
    for split, row in summary.items():
        n, b, v = row['total'], row['baseline_success'], row['nomemory_success']
        lines.append(f'| {split} | {b}/{n} ({percent(b,n)}%) | {v}/{n} ({percent(v,n)}%) | {percent(v-b,n)} pp |')
    lines += ['', '## Matched task/seed outcomes', '', '| Split | Both succeed | Baseline only | NoMemory only | Neither |', '| --- | ---: | ---: | ---: | ---: |']
    for split, row in summary.items():
        lines.append(f'| {split} | {row["both_success"]} | {row["baseline_only"]} | {row["nomemory_only"]} | {row["neither"]} |')
    audit = data['initial_state_audit']
    lines += ['', '## Settings and verification', '', 'Removed: ' + data['settings']['removed'], '', 'Retained: ' + data['settings']['retained'], '',
              'All 320 result scores agree with their final saved native success signal. All 160 NoMemory CLI exits are zero. Smoke episodes are excluded.', '',
              data['memory_audit_scope'], '',
              f'Initial robot state differs above 1e-6 in {audit["robot_state_differences"]}/160 pairs ({audit["exact_robot_state_differences"]} differ by exact comparison); task instructions differ in {audit["task_language_differences"]}/160 pairs. Full object states were not audited.', '',
              *[f'- {x}' for x in data['comparison_limits']], '', '## Task and seed results', '',
              'Each cell shows baseline / NoMemory; 1 = success, 0 = failure.', '',
              '| Split | Task | Baseline | NoMemory | Seed 1 | Seed 2 | Seed 3 | Seed 4 | Seed 5 |', '| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |']
    for split, tasks in baseline['tasks'].items():
        for task in tasks:
            rs = [r for r in rows if r['split'] == split and r['task'] == task]
            cells = [f'{int(r["baseline_success"])} / {int(r["nomemory_success"])}' for r in rs]
            lines.append(f'| {split} | {task} | {sum(r["baseline_success"] for r in rs)}/5 | {sum(r["nomemory_success"] for r in rs)}/5 | ' + ' | '.join(cells) + ' |')
    if data['recorded_trajectory_audit']['status'] == 'audited':
        a = data['recorded_trajectory_audit']
        lines += ['', '## Recorded memory access audit', '',
                  f"Audited {a['streams']} streams and {a['jsonl_events']:,} JSONL events with zero parse errors. Found {a['native_shell_commands']} native shell commands across {a['episodes_with_native_shell']} episodes ({a['native_shell_completed']} completed, {a['native_shell_failed']} failed). No historical memory reads or attempts were observed.", '',
                  f"All {a['memory_reads_jsonl_count']} memory-read logs total {a['memory_reads_total_bytes']} bytes. Source searches/reads occurred in {a['source_content_read_or_search_episodes']} episodes; these retained permissions are separate from historical memory.", '',
                  f"The source audit notes {a['tool_items_missing_completion_event']} VLA tool items without a completion event and {a['retryable_stream_errors']} retryable stream error. All 160 planner turns have completion events. This is a recorded-trajectory audit, not an OS syscall trace.", '',
                  f"Private source audit SHA-256: `{a['source_sha256']}`."]
    lines += ['', '## Provenance', '', f'Run: `{args.run_root.name}`. Finished 2026-11-09 08:57 HKT.', '',
              f'Official base: `{provenance["base_commit"]}` plus the archived NoMemory patch. NoMemory branch is not yet published.', '',
              'JSON/CSV include per-episode result and states SHA-256 hashes. JSON also records the source-file hashes, patch, manifest, validation and public baseline data hashes. Only selected public fields are exported.', '']
    (args.output / 'report.md').write_text('\n'.join(lines))
    print(json.dumps({'summary': summary, 'initial_state_audit': audit, 'validation': data['validation']}, indent=2))


if __name__ == '__main__':
    main()
