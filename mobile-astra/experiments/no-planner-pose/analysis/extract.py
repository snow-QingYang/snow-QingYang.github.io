"""Export E09 and matched E08/baseline outcomes from completed local runs.

Usage: python extract.py --no-pose RUN --combined RUN --baseline RUN --output DIR
Reads retained artifacts and completed audits; never starts evaluation.
Public exports contain counts and hashes, not raw prompts, images or local paths.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

VLA = {"rldx_skill", "rldx_arm"}
MANUAL = {"move_to", "move_delta", "move_base", "navigate_to", "rotate_pitch",
          "set_gripper", "release", "scripted_grasp", "execute_action"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def episode(root, cell):
    directory = root / cell
    result = load(directory / "result.json")
    steps = load(directory / "states.json")["steps"]
    require(result["valid"] is True, f"Invalid episode: {cell}")
    require(result["success"] == steps[-1]["extras"]["success"], f"Score mismatch: {cell}")
    require(result["planner"]["model"] == "gpt-6-astra", f"Unexpected planner: {cell}")
    actions = [s for s in steps if (s.get("command") or {}).get("action") in VLA | MANUAL]
    counts = Counter(s["command"]["action"] for s in actions)
    first_success = next((s for s in steps if s["extras"].get("success")), None)
    terminal_action = (first_success.get("command") or {}).get("action") if first_success else None
    vla_count = sum(counts[k] for k in VLA)
    manual_count = sum(counts[k] for k in MANUAL)
    if not result["success"]:
        path = "unsuccessful"
    elif manual_count == 0:
        path = "vla_only"
    elif terminal_action in VLA:
        path = "manual_then_vla_finish"
    elif terminal_action in MANUAL:
        path = "manual_finish"
    else:
        raise ValueError(f"Unclassified success: {cell}")
    return {
        "success": result["success"], "valid": True,
        "elapsed_s": result.get("elapsed_s"),
        "termination_reason": result["termination_reason"],
        "final_native_success": steps[-1]["extras"]["success"],
        "final_terminated": steps[-1]["terminated"],
        "success_path": path, "vla_calls": vla_count, "manual_calls": manual_count,
        "action_counts": dict(sorted(counts.items())),
        "first_success_step": first_success["step_idx"] if first_success else None,
        "first_success_action": terminal_action,
        "result_sha256": sha(directory / "result.json"),
        "states_sha256": sha(directory / "states.json"),
    }



def paired(rows, reference):
    return {
        'both_success': sum(r['no_pose']['success'] and r[reference]['success'] for r in rows),
        'no_pose_only': sum(r['no_pose']['success'] and not r[reference]['success'] for r in rows),
        'reference_only': sum(not r['no_pose']['success'] and r[reference]['success'] for r in rows),
        'both_failure': sum(not r['no_pose']['success'] and not r[reference]['success'] for r in rows),
    }


def initial(root, cell):
    directory = root / cell
    first = load(directory / 'states.json')['steps'][0]
    return {
        'task_language': hashlib.sha256(first['extras']['task_language'].encode()).hexdigest(),
        'rgb': {camera: sha(directory / f'{camera}.png' / '00.png')
                for camera in ('agentview', 'navview', 'wrist')},
        'camera_metadata': {camera: sha(directory / f'{camera}_metadata.json' / '00.json')
                            for camera in ('agentview', 'wrist')},
    }


def initial_comparison(left, right):
    row = {
        'task_language_equal': left['task_language'] == right['task_language'],
        'rgb_exact_equal': {k: left['rgb'][k] == right['rgb'][k] for k in left['rgb']},
        'camera_metadata_equal': {k: left['camera_metadata'][k] == right['camera_metadata'][k]
                                  for k in left['camera_metadata']},
        'robot_state_comparable': False,
    }
    row['observed_inputs_equal'] = (row['task_language_equal']
        and all(row['rgb_exact_equal'].values()) and all(row['camera_metadata_equal'].values()))
    return row


def build(no_pose, combined, baseline):
    roots = {'no_pose': no_pose, 'combined': combined, 'baseline': baseline}
    manifest = load(no_pose / 'manifest.json')
    source = load(no_pose / 'source_revision.json')
    status = load(no_pose / 'status.json')
    audit_dir = no_pose / 'maintenance/final_audit_20261112'
    context = load(audit_dir / 'context_audit.json')['public_summary']
    reliability = load(audit_dir / 'independent_final_result_audit.json')
    require(status['phase'] == 'validated' and status['completed'] == 160, 'Run incomplete')
    require(len(reliability['current_results']) == 160 and
            all(r['accepted'] for r in reliability['current_results']), 'Unaccepted result')
    require(not reliability['native_error_candidates'] and not reliability['nonzero_exit_metadata'],
            'Native error in current results')
    require(reliability['source_matches'] is True, 'Source mismatch')
    require(context['episodes'] == 160 and context['native_scoring_consistent'] == 160,
            'Incomplete context or scoring audit')
    for key in ('hidden_feedback_field_occurrences', 'native_command_calls',
                'file_read_list_search_calls', 'geometry_tool_calls', 'parser_errors',
                'tool_transport_errors', 'tool_payload_errors', 'unexpected_tools'):
        require(context[key] == 0, f'Context audit failed: {key}')
    tasks = {split: manifest['splits']['composite_' + split]['tasks'] for split in ('seen', 'unseen')}
    rows = []
    for split, names in tasks.items():
        require(len(names) == 16, 'Expected 16 tasks per split')
        for task in names:
            for seed in range(1, 6):
                cell = f'composite_{split}/{task}_s{seed}'
                row = {'split': split, 'task': task, 'seed': seed}
                row.update({label: episode(root, cell) for label, root in roots.items()})
                row['initial_sha256'] = {label: initial(root, cell) for label, root in roots.items()}
                row['initial_conditions'] = {
                    ref: initial_comparison(row['initial_sha256']['no_pose'], row['initial_sha256'][ref])
                    for ref in ('combined', 'baseline')}
                rows.append(row)
    summary = {}
    for split in ('seen', 'unseen', 'all'):
        selected = [r for r in rows if split == 'all' or r['split'] == split]
        summary[split] = {
            'total': len(selected),
            'successes': {label: sum(r[label]['success'] for r in selected) for label in roots},
            'paired_combined': paired(selected, 'combined'),
            'paired_baseline': paired(selected, 'baseline'),
            'no_pose_success_paths': dict(Counter(r['no_pose']['success_path'] for r in selected
                                                if r['no_pose']['success'])),
        }
    require(summary['seen']['successes'] == {'no_pose': 17, 'combined': 27, 'baseline': 34}, 'Seen totals changed')
    require(summary['unseen']['successes'] == {'no_pose': 10, 'combined': 14, 'baseline': 21}, 'Unseen totals changed')
    initial_totals = {}
    for ref in ('combined', 'baseline'):
        selected = [r for r in rows if r['initial_conditions'][ref]['observed_inputs_equal']]
        initial_totals[ref] = {
            'observed_inputs_equal_count': len(selected),
            'task_language_equal_count': sum(r['initial_conditions'][ref]['task_language_equal'] for r in rows),
            'rgb_exact_equal_counts': {cam: sum(r['initial_conditions'][ref]['rgb_exact_equal'][cam] for r in rows)
                                       for cam in ('agentview', 'navview', 'wrist')},
            'camera_metadata_equal_counts': {cam: sum(r['initial_conditions'][ref]['camera_metadata_equal'][cam] for r in rows)
                                             for cam in ('agentview', 'wrist')},
            'subset_successes': {label: sum(r[label]['success'] for r in selected) for label in ('no_pose', ref)},
            'subset_paired': paired(selected, ref),
        }
    source_files = source['source_files']
    require(all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in source_files), 'Unsafe source path')
    evidence = ['manifest.json', 'source_revision.json', 'validation.json',
                'maintenance/final_audit_20261112/context_audit.json',
                'maintenance/final_audit_20261112/independent_final_result_audit.json']
    return {
        'schema_version': '1.0', 'experiment_id': 'E09',
        'name': '组合信息移除 · 不提供位姿坐标',
        'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'completed_local': datetime.fromtimestamp(status['updated_at'], ZoneInfo('Asia/Hong_Kong')).isoformat(timespec='seconds'),
        'runs': {label: root.name for label, root in roots.items()},
        'code': {'branch': 'no_privileged_info_no_planner_pose', 'commit': source['commit'],
                 'base_commit': manifest['source_base'], 'parent_commit': source['parent_commit'],
                 'publication_status': 'published',
                 'branch_url': 'https://github.com/snow-QingYang/RPent/tree/no_privileged_info_no_planner_pose',
                 'commit_url': 'https://github.com/snow-QingYang/RPent/commit/f2d62d21104f412b5e020931d11d7054b6ef3818',
                 'evaluated_code_commit': 'f2d62d21104f412b5e020931d11d7054b6ef3818',
                 'publication_commit': 'f2d62d21104f412b5e020931d11d7054b6ef3818',
                 'publication_commit_url': 'https://github.com/snow-QingYang/RPent/commit/f2d62d21104f412b5e020931d11d7054b6ef3818',
                 'instructions_url': 'https://github.com/snow-QingYang/RPent/blob/f2d62d21104f412b5e020931d11d7054b6ef3818/EXPERIMENT.md'},
        'protocol': {'model': 'gpt-6-astra', 'reasoning_effort': 'xhigh', 'vla': 'RLDX-1-FT-RC365',
                     'environment_split': 'target', 'seeds': [1, 2, 3, 4, 5], 'planner_max_turns': 100,
                     'timeout_seconds': 3600, 'vla_max_chunks': 40, 'vla_actions_per_chunk': 8,
                     'settle_patience': 999, 'success_source': 'state.success', 'native_success_early_stop': True,
                     'memory_policy': 'none', 'hidden_feedback_fields': manifest['ablation']['hidden_feedback_fields']},
        'tasks': tasks, 'summary': summary, 'episodes': rows, 'context_audit': context,
        'reliability_audit': {
            'accepted_episodes': len(reliability['current_results']),
            'checked_log_files': reliability['checked_log_files'],
            'missing_or_empty_logs': len(reliability['missing_or_empty_logs']),
            'native_error_candidates': len(reliability['native_error_candidates']),
            'nonzero_exit_metadata': len(reliability['nonzero_exit_metadata']),
            'source_matches': reliability['source_matches'],
            'preserved_results': reliability['pause_baseline_count'],
            'preserved_result_hash_mismatches': len(reliability['pause_hash_mismatches']),
            'recovered_network_events': len(reliability['planner_network_events']),
            'prior_excluded_attempts': len(reliability['prior_16_excluded_results']),
            'late_contention_replacements': [
                {k: r[k] for k in ('cell', 'current_attempts', 'current_valid', 'current_success',
                                   'current_log_has_native_error')}
                for r in reliability['retry_attempt_4']],
            'scope': 'Accepted attempts only. Infrastructure-fault attempts are archived and excluded. No logged native error does not prove the absence of silent contention.',
        },
        'initial_comparison': {
            'comparisons': initial_totals,
            'robot_state_comparable': False,
            'scope': 'Task text, initial RGB file bytes and retained camera-metadata file bytes only. E09 does not save Planner robot state. Equality of these artifacts does not establish identical simulator initial states or a causal effect.',
        },
        'evidence_sha256': {name: sha(no_pose / name) for name in evidence},
        'source_files_sha256': source_files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for label in ('no-pose', 'combined', 'baseline', 'output'):
        parser.add_argument('--' + label, type=Path, required=True)
    args = parser.parse_args()
    data = build(args.no_pose, args.combined, args.baseline)
    args.output.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    require(not any(token in text for token in ('/home/', '/mnt/', 'sk-', 'Bearer ')), 'Private data in export')
    (args.output / 'data.json').write_text(text, encoding='utf-8')
    flat = []
    for row in data['episodes']:
        item = {k: row[k] for k in ('split', 'task', 'seed')}
        for label in ('no_pose', 'combined', 'baseline'):
            for key in ('success', 'valid', 'elapsed_s', 'termination_reason', 'final_native_success',
                        'success_path', 'vla_calls', 'manual_calls', 'first_success_step',
                        'first_success_action', 'result_sha256', 'states_sha256'):
                item[f'{label}_{key}'] = row[label][key]
        for ref in ('combined', 'baseline'):
            for key in ('observed_inputs_equal', 'task_language_equal', 'robot_state_comparable'):
                item[f'initial_vs_{ref}_{key}'] = row['initial_conditions'][ref][key]
        flat.append(item)
    with (args.output / 'episodes.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(flat)
    print(json.dumps({'episodes': len(flat), 'summary': data['summary'],
                      'initial_comparison': data['initial_comparison']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
