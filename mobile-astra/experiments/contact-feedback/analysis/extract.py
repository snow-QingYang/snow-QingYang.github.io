"""Export E04 with full native progress from a completed canonical run.

Usage: python extract.py --run RUN --site SITE_CHECKOUT --output OUTPUT
The E01 reference is the existing public export, not newly reread raw logs.
Only selected fields and hashes are exported; no model messages or credentials.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import csv
import hashlib
import json
from pathlib import Path

REMOVED = ('grasp_contact', 'grasp_obj', 'grasped', 'grasp_detected')
VLA = {'rldx_skill', 'rldx_arm'}
COMMIT = '092d8b8d344a7a0b2f8b6d5dd3bfae6a81342804'
BASE = 'a744bd5f128ebef3cb8c6736cf7cd98adff681f1'
PLANNER = {'backend': 'codex', 'model': 'gpt-6-astra', 'reasoning_effort': 'xhigh', 'max_turns': 100}
RUNTIME = {'cell_timeout_seconds': 3600, 'rldx_max_chunks': 40,
           'rldx_settle_patience': 999, 'rldx_action_steps_per_chunk': 8}


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys(child)


def summary(rows):
    return {'total': len(rows),
            'baseline_success': sum(r['baseline_success'] for r in rows),
            'nocontact_success': sum(r['nocontact_success'] for r in rows),
            'both_success': sum(r['baseline_success'] and r['nocontact_success'] for r in rows),
            'baseline_only': sum(r['baseline_success'] and not r['nocontact_success'] for r in rows),
            'nocontact_only': sum(not r['baseline_success'] and r['nocontact_success'] for r in rows),
            'neither': sum(not r['baseline_success'] and not r['nocontact_success'] for r in rows)}


def build(run, site):
    manifest = load(run / 'manifest.json')
    controller = load(run / 'dynamic-control/state.json')
    guard = load(run / 'dynamic-control/runtime-guard-state.json')
    validation = load(run / 'dynamic-control/final-validation.log')
    require(controller['status'] == 'completed' and controller['final_validation_exit_code'] == 0,
            'Batch or validation incomplete')
    require(not controller['errors'] and not guard['alerts'] and guard['launcher_logs_checked'] == 160,
            'Unreviewed infrastructure error')
    require(manifest['evaluated_commit'] == COMMIT and manifest['base_commit'] == BASE, 'Wrong code revision')
    require(manifest['task_progress_source'] == 'native_unfiltered'
            and manifest['agent_success_source'] == 'native' and manifest['vlm_enabled'] is False,
            'Wrong experiment scope')
    for name, expected in manifest['source_files_sha256'].items():
        require(sha(run / 'source' / name) == expected, 'Frozen source changed: ' + name)
    memory = load(Path(manifest['memory_manifest']))
    for name, expected in memory['files'].items():
        require(sha(Path(manifest['memory_root']) / name) == expected, 'Memory changed: ' + name)
    target = load(run / 'source/robots/robocasa/eval/target50.json')
    tasks = {s: target['splits']['composite_' + s]['tasks'] for s in ('seen', 'unseen')}
    expected = {(s, t, seed) for s in tasks for t in tasks[s] for seed in range(1, 6)}
    actual = {(p.parent.parent.name.removeprefix('composite_'),
               p.parent.name.rsplit('_s', 1)[0], int(p.parent.name.rsplit('_s', 1)[1]))
              for p in (run / 'results').glob('composite_*/*/result.json')}
    require(actual == expected and len(actual) == 160, 'Task/seed coverage mismatch')
    refdir = site / 'mobile-astra/experiments/baseline/analysis'
    reference = load(refdir / 'data.json')
    baseline = {(r['split'], r['task'], r['seed']): r for r in reference['episodes'] if r['model'] == 'astra'}
    require(set(baseline) == expected, 'Baseline task/seed coverage mismatch')
    rows, selected, audit, progress = [], set(), Counter(), {}
    for split in tasks:
        for task in tasks[split]:
            progress[task] = set()
            for seed in range(1, 6):
                cell = run / 'results' / ('composite_' + split) / f'{task}_s{seed}'
                result = load(cell / 'result.json')
                states = load(cell / 'states.json')['steps']
                b = baseline[split, task, seed]
                bp = refdir / 'cases' / f'astra--{task}--{seed}.json'
                detail = load(bp)
                require(detail['success'] == b['success'] and detail['valid'] is True, 'Baseline export mismatch')
                require(result['task_name'] == task and result['seed'] == seed
                        and result['evaluation_split'] == 'composite_' + split, 'Result identity mismatch')
                require(result['valid'] is True and result['environment_split'] == 'target'
                        and result['protocol_id'] == 'robocasa-harness-vla-v2', 'Invalid result protocol')
                require(result['planner'] == PLANNER and result['runtime'] == RUNTIME, 'Runtime configuration changed')
                require(result['memory']['profile'] == 'local' and result['memory']['policy'] == 'task-global'
                        and result['memory']['audit_status'] == 'ok', 'Memory audit failed')
                selected.update(result['memory']['selected_files'])
                require(result['termination_reason'] == 'completed', 'Unexpected termination')
                require((cell / 'launcher_exit_code.txt').read_text().strip() == '0', 'Nonzero episode exit')
                require(result['success_source'] == 'state.success' and type(result['success']) is bool,
                        'Invalid success source')
                require(states and [s['step_idx'] for s in states] == list(range(len(states))), 'Incomplete history')
                require(all(type(s['extras'].get('success')) is bool for s in states), 'Native success missing')
                require(states[-1]['extras']['success'] == result['success']
                        == any(s['extras']['success'] for s in states), 'Native score mismatch')
                actions = Counter()
                for state in states:
                    output = state.get('result') or {}
                    action = (state.get('command') or {}).get('action')
                    p = state['extras'].get('task_progress')
                    require(isinstance(p, dict), 'Missing native task progress')
                    require(not set(REMOVED).intersection(keys(output)), 'Removed label leaked into action result')
                    progress[task].update(p)
                    audit['observations'] += 1
                    audit['observations_with_nonempty_progress'] += bool(p)
                    if action:
                        actions[action] += 1
                    if action in VLA:
                        audit['vla_action_records'] += 1
                        audit['vla_records_with_held_apart'] += 'held_apart' in output
                        audit['interrupted_vla_records'] += output.get('interrupted') is True
                first = next((s['step_idx'] for s in states if s['extras']['success']), None)
                row = {'split': split, 'task': task, 'seed': seed,
                       'baseline_success': b['success'], 'nocontact_success': result['success'],
                       'baseline_elapsed_s': b['elapsed_s'], 'nocontact_elapsed_s': result['elapsed_s'],
                       'baseline_termination_reason': detail['termination_reason'],
                       'nocontact_termination_reason': result['termination_reason'],
                       'baseline_final_native_success': b['success'],
                       'nocontact_final_native_success': states[-1]['extras']['success'],
                       'nocontact_final_terminated': states[-1]['terminated'],
                       'baseline_result_sha256': detail['source']['files']['result.json'],
                       'baseline_states_sha256': detail['source']['files']['states.json'],
                       'baseline_export_sha256': sha(bp),
                       'nocontact_result_sha256': sha(cell / 'result.json'),
                       'nocontact_states_sha256': sha(cell / 'states.json'),
                       'initial_task_language_equal': detail['task_language'] == states[0]['extras']['task_language'],
                       'initial_robot_state_max_abs_diff': None,
                       'initial_robot_state_exact_equal': None,
                       'nocontact_vla_calls': sum(actions[a] for a in VLA),
                       'nocontact_manual_calls': sum(n for a, n in actions.items() if a not in VLA),
                       'nocontact_first_success_step': first,
                       'nocontact_actions_after_success': len(states) - 1 - first if first is not None else None,
                       'nocontact_progress_keys': sorted({k for s in states for k in s['extras']['task_progress']}),
                       'memory_audit_status': 'ok', 'exit_code': 0}
                rows.append(row)
    for name in selected:
        require(name in memory['files'], 'Selected memory missing from immutable corpus')
    summaries = {s: summary([r for r in rows if s == 'all' or r['split'] == s]) for s in ('seen','unseen','all')}
    require([summaries[s]['nocontact_success'] for s in ('seen','unseen','all')] == [29,15,44],
            'Unexpected outcome; review before publication')
    require(summaries['all']['baseline_success'] == 55, 'Wrong baseline')
    require(validation['valid_cells'] == 160 and validation['splits']['composite_seen']['successes'] == 29
            and validation['splits']['composite_unseen']['successes'] == 15, 'Built-in validation disagrees')
    audit.update({'episodes_checked': 160, 'forbidden_vla_result_fields_found': 0})
    return {'schema_version': 2, 'experiment': 'E04', 'variant': 'full-native-task-progress',
            'generated_utc': datetime.now(timezone.utc).isoformat(), 'run': run.name,
            'started_at': manifest['started_at'], 'completed_at': controller['ended_at'],
            'tasks': tasks, 'summary': summaries, 'episodes': rows,
            'protocol': {'benchmark': 'RoboCasa composite', 'environment_split': 'target',
                'protocol_id': 'robocasa-harness-vla-v2', 'planner': PLANNER, 'runtime': RUNTIME,
                'seeds': [1,2,3,4,5], 'vla': 'RLDX-1-FT-RC365', 'memory_profile': 'local',
                'memory_version': memory['version'], 'geometry': 'Original simulator depth and world maps',
                'removed_vla_result_fields': list(REMOVED), 'removed_progress_fields_by_task': {},
                'filtered_tasks': 0, 'filtered_task_field_pairs': 0,
                'retained_skill_feedback': manifest['retained_vla_fields'],
                'task_progress': 'All native task progress retained, including contact-derived predicates',
                'success': 'Native, visible to Agent', 'native_success_and_vla_early_stop': 'Retained',
                'read_text_file': 'Baseline permissions and scoring-source access retained',
                'prompt_changes': 'None', 'vlm_enabled': False},
            'feedback_audit': dict(audit), 'observed_progress_fields_by_task': {t: sorted(v) for t,v in progress.items()},
            'initial_state_audit': {'pairs_checked_for_task_language': 160,
                'task_language_differences': sum(not r['initial_task_language_equal'] for r in rows),
                'robot_state_comparison': 'not_audited', 'full_scene_comparison': 'not_audited',
                'scope': 'Task language from published E01 details and current step 0. Baseline raw robot/object states were not available; do not reuse the old E04 initial-state audit.'},
            'memory_audit': {'episodes_ok': 160, 'matching_launch_sha256_files': len(memory['files']),
                'unique_selected_files': len(selected), 'selected_file_sha256': {n: memory['files'][n] for n in sorted(selected)},
                'memory_revision': memory['revision'], 'reference_selection_comparison': 'not_reaudited'},
            'validation': {'valid_episodes':160, 'native_final_state_matches':160, 'exit_zero':160,
                'frozen_source_files_verified': len(manifest['source_files_sha256']),
                'runtime_guard_logs_checked':160, 'runtime_guard_alerts':[], 'final_protocol_check':'passed',
                'baseline_reference':'Published E01 export and per-episode source hashes; raw E01 logs not reaudited'},
            'sources': {'baseline': {'run': 'composite_main_astra_rerun_20261101T150450Z',
                    'revision':BASE, 'export_sha256':sha(refdir/'data.json')},
                'nocontact': {'run':run.name, 'revision':COMMIT, 'base_revision':BASE, 'branch':'no_contact_gt',
                    'source_files_sha256':manifest['source_files_sha256'],
                    'manifest_sha256':sha(run/'manifest.json'), 'controller_sha256':sha(run/'dynamic-control/state.json')}},
            'comparison_limits': ['One batch per condition; task/seed alignment does not establish identical scenes.',
                'VLA action sampling was not fixed across independent runs.',
                'This result removes only explicit VLA grasp/contact reports; full native progress remains.']}


def pct(a, n):
    return str((Decimal(a)*100/Decimal(n)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def report(data):
    lines = ['# E04：移除 VLA 接触反馈，保留完整 task progress', '',
        '2026-11-14 完成；32 个任务 × seeds 1–5，共 160 个有效 episode。', '',
        '| 分组 | E01 baseline | 新版 E04 | 成功率差 |', '|---|---:|---:|---:|']
    for s, label in [('seen','Seen'),('unseen','Unseen'),('all','总计')]:
        r=data['summary'][s]; n=r['total']; b=r['baseline_success']; c=r['nocontact_success']
        lines.append(f'| {label} | {b}/{n} · {pct(b,n)}% | {c}/{n} · {pct(c,n)}% | {pct(c-b,n)} pp |')
    a=data['summary']['all']; audit=data['feedback_audit']
    lines += ['', f"双方成功 {a['both_success']} 局；仅 baseline 成功 {a['baseline_only']} 局；仅新版 E04 成功 {a['nocontact_only']} 局；双方失败 {a['neither']} 局。", '',
        '## 实验范围', '',
        '仅从 rldx_skill / rldx_arm 返回中移除 grasp_contact、grasp_obj、grasped、grasp_detected，并停止对应的封装接触查询。', '',
        '**完整保留所有原生 task_progress，包括接触派生条件。** 保留 held_apart、gripper_qpos、peak_lift、执行状态、几何查询、原版记忆、评分源码访问、simulator success 和 VLA 原生成功早停。无 VLM；提示词与控制预算保留原版设置。', '',
        'GPT-6-Astra / xhigh；100 个模型响应、3600 秒每局；RLDX-1-FT-RC365，每次最多 40 chunks × 8 steps。', '',
        '## 核验与限制', '',
        f"160 个结果逐一匹配末条原生 success；160 个进程退出码为 0；最终协议校验通过。扫描 {audit['observations']} 条观测、{audit['vla_action_records']} 条 VLA 动作记录，四个移除字段零命中。日志监控未记录显存不足或崩溃告警。", '',
        f"493 个源码文件哈希和 148 个原版记忆文件哈希通过核验；160 局 memory audit 均通过，涉及 {data['memory_audit']['unique_selected_files']} 个选中记忆文件。", '',
        f"E01 对照来自已发布的逐局导出；本次没有重新审计 E01 原始日志。任务文本有 {data['initial_state_audit']['task_language_differences']} 对不同；未核对初始机器人及全部物体状态，不能沿用旧 E04 的初态检查数字。", '',
        '单批差值不建立统计显著性或逐局因果关系。同 task/seed 不保证初态相同，VLA 动作采样也未固定。', '',
        '## 版本与历史', '',
        f"评测提交：`{COMMIT}`；分支 `no_contact_gt`；批次 `{data['run']}`。", '',
        '本页 E04 已替换为保留完整进度的 44/160。旧 46/160 批次还过滤了 25 个任务、60 项接触派生进度，作为历史归档保存，不混入当前 160 局。', '',
        '## 重新导出', '',
        '`python extract.py --run RUN --site SITE_CHECKOUT --output OUTPUT`', '',
        'RUN 需含原始 manifest、dynamic-control、results、冻结 source，且 manifest 指向原记忆审计文件。公开 ZIP 提供逐局结果、原生状态、记忆审计、生产源码和本报告；不包含模型原始对话、运行配置或凭据。', '']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True); p.add_argument('--site',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); data=build(args.run,args.site); args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    with (args.output/'episodes.csv').open('w',newline='') as f:
        fields=[k for k in data['episodes'][0] if k!='nocontact_progress_keys']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); w.writeheader(); w.writerows(data['episodes'])
    (args.output/'report.md').write_text(report(data))
    print(json.dumps({'summary':data['summary'],'feedback_audit':data['feedback_audit'],
                      'initial_state_audit':data['initial_state_audit']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
