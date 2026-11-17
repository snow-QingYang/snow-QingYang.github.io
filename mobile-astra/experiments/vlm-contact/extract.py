"""Export a partial VLM contact run; only valid episodes with complete VLM audits count.

Run with --run OUTPUT_DIR --manifest ROBOT_REPO/robots/robocasa/eval/target50.json.
Reference exports are read from the adjacent baseline and corrected E04 pages.
This writes only the E11 page, JSON and CSV; overview/status entries are maintained
separately. Credentials, raw traces, local paths and RGB are not published.
"""
import argparse
import csv
import hashlib
import html
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(run, manifest, output):
    tasks = read(manifest)['splits']
    base_file = output.parent / 'baseline/analysis/data.json'
    contact_file = output.parent / 'contact-feedback/analysis/data.json'
    baseline = {(e['split'], e['task'], e['seed']): e['success']
                for e in read(base_file)['episodes'] if e['model'] == 'astra'}
    contact = {(e['split'], e['task'], e['seed']): e['nocontact_success']
               for e in read(contact_file)['episodes']}
    rows = []
    for split in ('seen', 'unseen'):
        spec = tasks['composite_' + split]
        for task in spec['tasks']:
            for seed in spec['seeds']:
                cell = run / ('composite_' + split) / f'{task}_s{seed}'
                row = dict(split=split, task=task, seed=seed, status='pending',
                           success=None, elapsed_s=None, code_revision=None,
                           result_sha256=None, health_sha256=None,
                           vlm_judgments=0, recovered_vlm_requests=0,
                           baseline_success=baseline[split, task, seed],
                           no_contact_success=contact[split, task, seed])
                result_file, health_file = cell / 'result.json', cell / 'vlm_grasp_health.json'
                if result_file.exists():
                    result = read(result_file)
                    health = read(health_file) if health_file.exists() else {}
                    accepted = (result.get('valid') is True
                                and result.get('termination_reason') != 'infrastructure_error'
                                and not result.get('infrastructure_error')
                                and health.get('all_requests_available') is True)
                    row['status'] = 'valid' if accepted else 'infrastructure_or_audit_pending'
                    if accepted:
                        assert result['success'] in (True, False)
                        assert result['task_name'] == task and result['seed'] == seed
                        assert result['planner']['model'] == 'gpt-6-astra'
                        row.update(success=result['success'], elapsed_s=result['elapsed_s'],
                                   result_sha256=digest(result_file), health_sha256=digest(health_file),
                                   code_revision=(cell / 'code_revision.txt').read_text().strip())
                        for audit_file in (cell / 'vlm_grasp.json').glob('*.json'):
                            audit = read(audit_file)
                            assert audit['feedback']['grasp_feedback']['status'] == 'ok'
                            row['vlm_judgments'] += 1
                            row['recovered_vlm_requests'] += len(audit.get('attempts', [])) > 1
                rows.append(row)
    summaries = {}
    for split in ('seen', 'unseen', 'all'):
        planned = [r for r in rows if split == 'all' or r['split'] == split]
        valid = [r for r in planned if r['status'] == 'valid']
        successes = sum(r['success'] for r in valid)
        summaries[split] = dict(planned=len(planned), completed=len(valid), pending=len(planned)-len(valid),
                               success=successes, success_rate_percent=round(100*successes/len(valid), 2) if valid else None,
                               matched_baseline_success=sum(r['baseline_success'] for r in valid),
                               matched_no_contact_success=sum(r['no_contact_success'] for r in valid))
    snapshot = datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(timespec='seconds')
    data = dict(schema_version=1, experiment='E11', name='VLM contact feedback',
                status='partial', snapshot_at=snapshot, run=run.name, summary=summaries,
                protocol=dict(planner='gpt-6-astra', reasoning_effort='xhigh',
                              grasp_vlm='gpt-6.1-terra', grasp_effort='medium',
                              vla='RLDX-1-FT-RC365', max_turns=100, planner_timeout_s=3600,
                              max_chunks=40, actions_per_chunk=8, memory='GPT_6_astra_high',
                              cameras=['agentview_left','agentview_right','eye_in_hand'],
                              max_sampled_frames=8, max_images=24,
                              retained=['full native task_progress', 'native success and early stopping',
                                        'geometry queries', 'memory', 'robot pose', 'gripper width',
                                        'held_apart', 'success-criteria source access'],
                              replaced=['grasp_contact','grasped','grasp_detected','grasp_obj']),
                references=dict(baseline_sha256=digest(base_file), no_contact_sha256=digest(contact_file)),
                code_revisions=dict(Counter(r['code_revision'] for r in rows if r['status']=='valid')),
                vlm_audit=dict(judgments=sum(r['vlm_judgments'] for r in rows),
                               recovered_requests=sum(r['recovered_vlm_requests'] for r in rows)),
                episodes=rows,
                limitations=['Partial snapshot; pending episodes are not failures and are excluded from success-rate denominators.',
                             'Reference comparisons use only the same completed task/seed cells.',
                             'One run per setting; scene identity and VLA random samples are not controlled.',
                             'Full task_progress may still expose contact-derived predicates.',
                             'Visual grasp accuracy against simulator contact has not been measured.'])
    output.mkdir(parents=True, exist_ok=True)
    (output / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    with (output / 'episodes.csv').open('w', newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    (output / 'index.html').write_text(render(data))
    return data


def render(data):
    summary=data['summary']; all_=summary['all']; timestamp=html.escape(data['snapshot_at'])
    def table(headers, rows, label):
        head=''.join(f'<th scope="col">{h}</th>' for h in headers)
        body=''.join('<tr>'+''.join(f'<td data-label="{html.escape(h)}">{v}</td>' for h,v in zip(headers,row))+'</tr>' for row in rows)
        return f'<div class="table-wrap stack-small"><table aria-label="{label}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    def rate(success, total):return f'{success} / {total} · {100*success/total:.2f}%' if total else '—'
    result_rows=[]; comparison=[]
    for split,label in [('seen','Seen'),('unseen','Unseen'),('all','合计')]:
        s=summary[split]
        result_rows.append([label,f'{s["completed"]} / {s["planned"]}',rate(s['success'],s['completed']),str(s['pending'])])
        comparison.append([label,str(s['completed']),rate(s['matched_baseline_success'],s['completed']),rate(s['matched_no_contact_success'],s['completed']),rate(s['success'],s['completed'])])
    matrices=[]
    for split,label in [('seen','Seen'),('unseen','Unseen')]:
        split_rows=[r for r in data['episodes'] if r['split']==split]
        task_rows=[]
        for task in dict.fromkeys(r['task'] for r in split_rows):
            cells=[r for r in split_rows if r['task']==task]
            marks=[]
            for r in cells:
                if r['status']!='valid':mark='<span class="badge pending">— 待评测</span>'
                elif r['success']:mark='<span class="badge complete">✓ 成功</span>'
                else:mark='<span class="badge failure">✕ 失败</span>'
                marks.append(mark)
            n=sum(r['status']=='valid' for r in cells); k=sum(r['success'] is True for r in cells)
            task_rows.append([html.escape(task),*marks,f'{k} / {n}' if n else '—'])
        matrices.append(f'<h3>{label}</h3>'+table(['任务','Seed 1','Seed 2','Seed 3','Seed 4','Seed 5','成功 / 已评测'],task_rows,label+' task and seed outcomes'))
    result_table=table(['任务组','评测进度','成功 / 有效已评测','待评测'],result_rows,'Partial results by split')
    comparison_table=table(['任务组','配对局数','E01 · 原版','E04 · 移除接触反馈','E11 · VLM 替代'],comparison,'Matched completed task and seed comparison')
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<meta name="description" content="E11 VLM 接触与抓持反馈替代，Partial results：{all_['completed']}/160 局，{all_['success']} 局成功。"><link rel="icon" href="data:,"><link rel="stylesheet" href="../../project.css"><title>E11 · VLM 接触反馈 · Partial results · Mobile Astra</title></head>
<body><header class="site-head"><div class="head-inner"><a class="brand" href="../../">Mobile Astra / 实验工作页</a><nav aria-label="项目导航"><a href="../../">项目总览</a><a href="../" aria-current="page">实验目录</a><a href="../../reference/">接口与真值</a></nav></div></header>
<main><nav class="crumbs" aria-label="当前位置"><a href="../../">项目总览</a><span>/</span><a href="../">实验目录</a><span>/</span><span aria-current="page">E11 · VLM 接触反馈</span></nav>
<div class="hero"><p class="eyebrow">HARNESSVLA / ROBOCASA · E11</p><h1>VLM 接触与抓持反馈</h1><p class="lead">用三视角 RGB 序列判断接触与抓持，替代 VLA 返回的四个模拟器抓持字段。完整任务进度与原生成功判定保留。</p><span class="badge pending">Partial results · {all_['completed']} / 160 已评测</span><p class="meta">快照：<time datetime="{timestamp}">{timestamp}</time> · Planner: GPT-6-Astra / xhigh · 抓持 VLM: GPT-6.1-Terra / medium</p></div>
<section id="results"><h2>Partial results</h2>{result_table}<p class="note">全组尚未完成。成功率只以有效已评测局为分母；其余 {all_['pending']} 局不算失败。页面是带时间戳的静态快照，后续评测继续追加。</p></section>
<section id="scope"><h2>替代了什么，保留了什么</h2><div class="cards"><article class="card"><h3>四个 VLA 返回字段改由视觉估计</h3><ul><li><code>grasp_contact</code>：最后一帧双指是否接触同一物体或把手。</li><li><code>grasped</code>：调用结束时是否持有物体或把手。</li><li><code>grasp_detected</code>：这次调用采样的画面中是否曾持有物体。</li><li><code>grasp_obj</code>：视觉描述的物体名称，不是模拟器实例 ID。</li></ul><p>VLM 只收到 RGB、相机名称和帧序号。无法判断时返回 unknown，不回退到模拟器接触结果或夹爪开度启发式。</p></article>
<article class="card"><h3>完整保留的 baseline 信息</h3><p>完整原生 <code>task_progress</code>、simulator success、VLA 成功早停、最终原生评分、几何查询、记忆、评分源码访问、机器人位姿和夹爪开度均保留。</p><p><code>held_apart</code> 仍作为原有启发式返回，但不作为 VLM 的输入。任务进度也可能包含接触派生条件，因此本实验没有移除所有接触相关真值。</p></article></div>
<p class="note">基于修正后的 <a href="../contact-feedback/">E04（完整 task_progress）</a>添加视觉估计。它与 <a href="../vlm-progress-native-success/">E10 的 VLM 任务进度替代</a>是两组独立实验。</p></section>
<section><h2>什么时候判断</h2><p>每次 <code>rldx_skill</code> 或 <code>rldx_arm</code> 结束后，取 VLA 已使用的左／右视角及腕部 RGB；在动作 chunk 结束帧中均匀采样最多 8 个时刻，保留首尾，共最多 24 张 256×256 图像。视觉结果连同证据写入当前返回、历史观测和保存状态。</p><p>不增加机器人动作或渲染步骤。采样可能漏掉短暂抓取；目前尚未完成 VLM 判断与模拟器接触真值之间的准确率核验。</p></section>
<section id="comparison"><h2>只比较当前已评测的相同 task / seed</h2>{comparison_table}<p class="note">E01、E04 均截取与 E11 相同的已评测局；没有拿部分结果直接比较完整 160 局。这里的配对只对齐任务名与 seed，未证明完整初始场景相同，也未固定 VLA 随机采样。当前差异不单独证明视觉反馈的因果贡献。</p></section>
<section id="matrix"><h2>逐任务、逐 seed</h2><p class="note">✓ 成功；✕ 有效任务失败；— 待评测。分母为该任务已评测的有效局数。</p>{''.join(matrices)}</section>
<section id="protocol"><h2>评测与异常处理</h2><p>32 个 composite 任务 × seeds 1–5，共 160 局；Seen / Unseen 各 80 局。RLDX-1-FT-RC365；原有 GPT_6_astra_high 记忆；每局最多 100 轮、3600 秒；每次 VLA 最多 40 chunks × 8 actions。</p><p>成功以模拟器原生结果为准。502/503/530 等临时接口错误恢复后继续；无法恢复的尝试归档、该局重新排队。普通任务失败不重跑，也不会因出现过已恢复的接口错误而删掉有效结果。</p><p>本快照包含 {data['vlm_audit']['judgments']} 次可用抓持判断，其中 {data['vlm_audit']['recovered_requests']} 次通过请求重试恢复。早期提交 <code>ab24d508</code> 与增加请求重试后的 <code>97cb19bd</code> 分别记录在逐局数据中；判断模型、输入与实验设定保持一致。</p></section>
<section id="data"><h2>数据与代码</h2><div class="links"><a class="button" href="episodes.csv" download>下载 160 格状态 CSV</a><a href="data.json">快照 JSON</a><a href="extract.py" download>统计脚本</a><a href="https://github.com/snow-QingYang/RPent/tree/vlm_contact_feedback">代码分支</a><a href="https://github.com/snow-QingYang/RPent/blob/97cb19bd55399777d9868bf44378d0c226abd64e/EXPERIMENT_VLM_CONTACT.md">实验说明</a></div><p class="note">公开快照包含每局有效性、成功结果、耗时、代码版本、结果和 VLM 健康审计文件的 SHA-256；原始轨迹、图像、请求审计与中断尝试保留在实验存档中，未包含在本页下载里。</p></section>
</main><footer class="site-foot"><span>E11 · Partial results · {data['snapshot_at'][:10]}</span><a href="../">实验目录</a></footer></body></html>'''


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    data=export(args.run,args.manifest,args.output)
    print(json.dumps(data['summary'],ensure_ascii=False,indent=2))
