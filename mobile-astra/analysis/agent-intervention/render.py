#!/usr/bin/env python3
"""Render takeover summaries without altering existing experiment results.

Run after extract.py: python mobile-astra/analysis/agent-intervention/render.py
Only marked summary blocks and project-status metadata are updated.
"""
import json
import re
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent.parent
DATA = json.loads((HERE / 'data.json').read_text())
EXPERIMENTS = {e['id']: e for e in DATA['experiments']}
BEGIN = '<!-- agent-takeover:start -->'
END = '<!-- agent-takeover:end -->'
DEFINITION = 'VLA 执行后仍未成功，Agent 再调用非 VLA 的物理动作进行修正，之后由 VLA 或解析动作完成，且本局最终环境评分成功。'
PROXY_NOTE = '† E06 未保存逐步原生成功信号，只能统计“VLA → 解析动作介入 → 最终评分成功”；无法排除介入前已经短暂成功，与其他组口径不完全相同。'


def block(text):
    return BEGIN + text + END


def clean(text):
    return re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END), '', text, flags=re.S)


def count(e, split):
    n = e['summary'][split]['takeover_success']
    return '不适用' if n is None else str(n) + ('†' if e['status'] == 'final_score_proxy' else '')


def metric_line(e, prefix):
    url = f'{prefix}analysis/agent-intervention/?experiment={e["id"]}'
    if e['status'] == 'not_applicable':
        body = '不适用（无 Planner）'
    else:
        body = ' · '.join(f'{label} <strong>{count(e, s)}</strong>' for s, label in [('seen', 'Seen'), ('unseen', 'Unseen'), ('all', '总计')])
    return f'<p class="takeover-line"><a href="{url}">Agent 接管后成功</a>：{body}</p>'


def detail_section(e):
    title = '<section id="agent-takeover"><h2>Agent 接管后成功</h2>'
    if e['status'] == 'not_applicable':
        return title + '<p>不适用：本实验没有外层 Planner，也没有 Agent 接管执行解析动作。该项不记作 0 局。</p><p><a href="../../analysis/agent-intervention/">查看各 Planner 实验的接管统计 →</a></p></section>'
    description = PROXY_NOTE if e['status'] == 'final_score_proxy' else DEFINITION
    cards = []
    for s, label in [('seen', 'Seen'), ('unseen', 'Unseen'), ('all', '总计')]:
        v = e['summary'][s]
        cards.append(f'<div><span>{label}</span><strong>{count(e, s)} <small>局</small></strong><span>本组成功 {v["success"]} / {v["episodes"]} 局</span></div>')
    more = ''
    if e['status'] != 'final_score_proxy':
        v = e['summary']['all']
        more = f'<p>其中，<strong>{v["takeover_then_vla_success"]} 局</strong>由 Agent 修正后再调用 VLA 完成；<strong>{v["takeover_then_manual_success"]} 局</strong>由解析动作直接达到首次原生成功。</p>'
    return title + f'<p>{description}</p><div class="takeover-cards">' + ''.join(cards) + '</div>' + more + '<p class="note">只读查询、单纯续调 VLA、首次 VLA 前的准备、finish 声明不算接管。这是成功局中的路径分类，不能证明继续运行 VLA 一定会失败。</p>' + f'<p><a href="../../analysis/agent-intervention/?experiment={e["id"]}">对照所有实验，并查看逐局动作证据 →</a></p></section>'


def integrate():
    p = SITE / 'index.html'
    text = clean(p.read_text())
    def truth(m):
        body = m.group(0)
        eid = m.group(1)
        return body[:-6] + block(metric_line(EXPERIMENTS[eid], '')) + body[-6:]
    text, n = re.subn(r'<div class="truth-setting" data-experiment="(E\d\d)">.*?</div></div>', truth, text, flags=re.S)
    assert n == 9
    section = re.search(r'<section id="completed">.*?</section>', text, re.S)
    assert section
    content = section.group(0)
    def completed_row(m):
        row = m.group(0)
        eid = re.search(r'\bE\d\d\b', row)
        if not eid:
            return row
        e = EXPERIMENTS[eid.group()]
        for s, label in [('seen', 'Seen'), ('unseen', 'Unseen'), ('all', '总计')]:
            extra = block(f'<small class="takeover-count">接管成功：<strong>{count(e, s)}</strong></small>')
            row, n = re.subn(f'(<td data-label="{label}">.*?)(</td>)', lambda c: c[1] + extra + c[2], row, count=1)
            assert n == 1
        return row
    content = re.sub(r'<tr>.*?</tr>', completed_row, content, flags=re.S)
    intro = '<p>下表每格附加的“接管成功”为本组成功局的子集：VLA 执行未完成后，Agent 调用解析动作修正，随后任务成功。首次 VLA 前的准备和单纯续调 VLA 不计入。</p><p><a class="button" href="analysis/agent-intervention/">接管成功对照表与逐局动作证据 →</a></p>'
    content = content.replace('<div class="table-wrap stack-small">', block(intro) + '<div class="table-wrap stack-small">', 1)
    content = content.replace('</section>', block(f'<p class="note">{PROXY_NOTE} E12 无 Planner，此项不适用。</p>') + '</section>', 1)
    text = text[:section.start()] + content + text[section.end():]
    truth_end = text.index('</section>', text.index('<section id="truth-list">'))
    text = text[:truth_end] + block(f'<p class="note">“接管后成功”按动作顺序统计，Seen / Unseen / 总计均为局数；<a href="analysis/agent-intervention/#definition">完整定义</a>。{PROXY_NOTE}</p>') + text[truth_end:]
    p.write_text(text)

    p = SITE / 'experiments/index.html'
    text = clean(p.read_text())
    def catalog_row(m):
        row = m.group(0)
        eid = re.search(r'\bE\d\d\b', row)
        if not eid or 'data-label="结果 / 内容"' not in row:
            return row
        return re.sub(r'(<td data-label="结果 / 内容">.*?)(</td>)', lambda c: c[1] + block(metric_line(EXPERIMENTS[eid.group()], '../')) + c[2], row, count=1)
    text = re.sub(r'<tr>.*?</tr>', catalog_row, text, flags=re.S)
    first_end = text.index('</section>')
    text = text[:first_end] + block(f'<p class="note">{DEFINITION} 首次 VLA 前的准备和单纯续调 VLA 不计入。{PROXY_NOTE}</p><p><a href="../analysis/agent-intervention/">全部接管统计与逐局证据 →</a></p>') + text[first_end:]
    p.write_text(text)

    for e in EXPERIMENTS.values():
        p = SITE / e['path'] / 'index.html'
        text = clean(p.read_text())
        end = text.index('</section>') + len('</section>')
        p.write_text(text[:end] + block(detail_section(e)) + text[end:])

    p = SITE / 'project-status.json'
    status = json.loads(p.read_text())
    for entry in status['completed_experiments']:
        e = EXPERIMENTS[entry['id']]
        entry['agent_takeover'] = {'status': e['status'], 'seen': e['summary']['seen']['takeover_success'], 'unseen': e['summary']['unseen']['takeover_success'], 'total': e['summary']['all']['takeover_success'], 'analysis_path': f'analysis/agent-intervention/?experiment={e["id"]}', 'scope_note': e['scope_note']}
    status['agent_takeover_analysis'] = {'metric_id': DATA['metric_id'], 'path': 'analysis/agent-intervention/', 'data_path': 'analysis/agent-intervention/data.json', 'coverage': DATA['coverage'], 'definition': DATA['definition'], 'limitations': DATA['limitations']}
    p.write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')


def analysis_page():
    rows = []
    for e in EXPERIMENTS.values():
        cells = []
        for s, label in [('seen', 'Seen'), ('unseen', 'Unseen'), ('all', '总计')]:
            v = e['summary'][s]
            detail = '' if e['status'] == 'not_applicable' else f'<small>全部成功：{v["success"]} / {v["episodes"]}</small>'
            url = f'?experiment={e["id"]}&amp;split={s}#cases'
            value = count(e, s)
            display = value if e['status'] == 'not_applicable' else f'<a href="{url}"><strong>{value}</strong></a>'
            cells.append(f'<td data-label="{label}">{display}{detail}</td>')
        rows.append(f'<tr data-experiment="{e["id"]}"><td data-label="实验"><a href="../../{e["path"]}">{e["id"]} · {escape(e["name"])}</a></td>' + ''.join(cells) + '</tr>')
    options = ''.join(f'<option value="{e["id"]}">{e["id"]} · {escape(e["name"])}</option>' for e in EXPERIMENTS.values())
    html = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><meta name="description" content="HarnessVLA 各实验 Agent 接管后成功的 Seen、Unseen 与总计，及逐局动作证据。">
<link rel="icon" href="data:,"><link rel="stylesheet" href="../../project.css"><title>Agent 接管后成功 · Mobile Astra</title><script defer src="app.js"></script></head>
<body><header class="site-head"><div class="head-inner"><a class="brand" href="../../">Mobile Astra / 实验工作页</a><nav aria-label="项目导航"><a href="../../">项目总览</a><a href="../../experiments/">实验目录</a><a href="#cases">逐局证据</a></nav></div></header>
<main><div class="hero"><p class="eyebrow">HARNESSVLA / SUCCESS PATHS</p><h1>VLA 执行后，Agent 接管成功了多少局？</h1><p class="lead">统计 VLA 尝试未完成后，Agent 用解析动作修正并最终成功的数量。按 Seen、Unseen 和总计展示，并保留每局的动作顺序。</p><p class="meta">10 组 Planner 实验 · 1600 局已核对 · 每组 Seen / Unseen 各 80 局</p></div>
<section id="summary"><h2>接管后成功局数</h2><p>粗体数字为接管后成功局数；下方是本实验的全部成功数。接管成功是全部成功的子集。</p><div class="table-wrap stack-small"><table aria-label="Agent 接管后成功：Seen、Unseen 与总计"><thead><tr><th scope="col">实验</th><th scope="col">Seen</th><th scope="col">Unseen</th><th scope="col">总计</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table></div><p class="note">''' + PROXY_NOTE + ''' E12 没有 Planner，接管指标不适用。</p></section>
<section id="definition"><h2>如何统计</h2><p>''' + DEFINITION + ''' 只分析截至首次原生成功的动作，避免把成功后的整理动作算作接管。</p><ol><li>已执行过 <code>rldx_skill</code> 或 <code>rldx_arm</code>，此时尚无原生成功记录。</li><li>之后 Agent 调用了非 VLA 物理动作：<code>move_to</code>、<code>move_delta</code>、<code>move_base</code>、<code>navigate_to</code>、<code>rotate_pitch</code>、<code>set_gripper</code>、<code>release</code>、<code>scripted_grasp</code> 或 <code>execute_action</code>。</li><li>随后观测到原生成功，且本局最终评分成功。修正后再由 VLA 完成，以及解析动作直接完成，均计入。</li></ol><p>只读查询、文件和 memory 操作、<code>finish</code> 声明、单纯续调 VLA 都不算物理接管。仅在首次 VLA 前采取动作属于“准备后 VLA 完成”。</p><p class="note">这是实际执行路径的分类，不能证明没有 Agent 接管就一定会失败。不同批次的初始状态和 VLA 随机采样未完全固定；“仅调用 VLA”仍包含 Planner 对 VLA 的调度，不等同于 E12 Pure VLA。</p><p class="note">''' + PROXY_NOTE + '''</p></section>
<section id="cases"><h2>逐局动作证据</h2><p>默认只显示接管后成功的 episode。可切换到其他成功路径，或查看所有 episode。</p>
<form class="takeover-filters" id="filters"><label>实验<select id="experiment"><option value="all">全部实验</option>''' + options + '''</select></label><label>任务组<select id="split"><option value="all">Seen + Unseen</option><option value="seen">Seen</option><option value="unseen">Unseen</option></select></label><label>成功路径<select id="path"><option value="takeover_success">接管后成功</option><option value="vla_only_success">仅调用 VLA 后成功</option><option value="setup_success">准备后 VLA 完成</option><option value="takeover_failure">接管后未成功</option><option value="all">所有 episode</option></select></label><label>任务名<input id="task" type="search" placeholder="例如 PanTransfer" autocomplete="off"></label></form>
<p id="filter-count" role="status" aria-live="polite">正在加载逐局记录…</p><p id="filter-note" class="note"></p>
<div class="table-wrap stack-small"><table class="takeover-episodes" aria-label="筛选后的逐局动作记录"><thead><tr><th scope="col">实验 / 任务 / seed</th><th scope="col">结果与路径</th><th scope="col">首次 VLA → 接管 → 成功</th><th scope="col">完成动作 / 证据</th></tr></thead><tbody id="case-rows"></tbody></table></div>
<div class="takeover-pagination"><button type="button" id="previous" disabled>上一页</button><span id="page-status"></span><button type="button" id="next" disabled>下一页</button></div><noscript><p>逐局筛选需要 JavaScript；可直接下载下面的 CSV 查看全部记录。</p></noscript></section>
<section id="data"><h2>数据与复核</h2><p>每组 160 个 task / seed 与已发布结果逐一核对。E01 使用已复核的动作轨迹；其他组读取冻结的 states / result，匹配来源哈希。E04、E10 的公开 ZIP 仅存在 JSON 排版差异，重建原排版后的哈希一致。E06 没有逐步成功时间线，单独标注。</p><div class="links"><a href="summary.csv" download>汇总 CSV</a><a href="episodes.csv" download>1600 局 CSV</a><a href="data.json" download>动作序列与哈希 JSON</a><a href="extract.py" download>统计脚本</a><a href="README.md">字段与复核说明</a></div></section></main><footer class="site-foot"><span>基于已完成实验的日志统计 · 2026-11-18</span><a href="../../">返回项目总览</a></footer></body></html>
'''
    (HERE / 'index.html').write_text(html)


if __name__ == '__main__':
    integrate()
    analysis_page()
    print('Updated homepage, catalog, 11 experiment pages, status, and takeover analysis.')
