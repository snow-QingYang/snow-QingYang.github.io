"""Export the completed pure-VLA suite using its frozen result validator.

Run with --run RUN_DIRECTORY. The run must contain manifest.json, summary.json,
source/summarize_pure_vla.py and all 160 canonical result.json files. The adjacent
E01 baseline export supplies descriptive reference scores. Only selected result
fields and file hashes are published; machine paths and raw logs stay local.
"""

import argparse
import csv
import hashlib
import html
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp(seconds):
    return datetime.fromtimestamp(seconds, ZoneInfo("Asia/Hong_Kong")).isoformat(timespec="seconds")


def export(run, output, published_at):
    validator_path = run / "source/summarize_pure_vla.py"
    spec = importlib.util.spec_from_file_location("frozen_pure_vla_validator", validator_path)
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    manifest = validator.load_manifest(run / "manifest.json")
    summary, errors = validator.summarize_results(run, manifest=manifest)
    if errors or not summary["complete"] or summary["overall"]["valid"] != 160:
        raise ValueError("Publication requires all 160 results to pass the frozen validator")
    if summary != read(run / "summary.json"):
        raise ValueError("Stored and independently recomputed summaries differ")
    smoke_path = run / "smoke/result.json"
    smoke = read(smoke_path)
    smoke_errors = validator.validate_cell_result(
        smoke_path, manifest=manifest, expected_task="ScrubCuttingBoard",
        expected_seed=1, allow_smoke=True,
    )
    if smoke_errors or smoke["native_steps"] != 32 or not smoke["is_smoke"]:
        raise ValueError("The required 32-step smoke must validate")
    baseline_path = output.parent / "baseline/analysis/data.json"
    baseline = {
        (episode["split"], episode["task"], episode["seed"]): episode["success"]
        for episode in read(baseline_path)["episodes"] if episode["model"] == "astra"
    }
    episodes = []
    policy_settings = []
    for group, split in manifest["splits"].items():
        if len(split["tasks"]) != 16 or split["seeds"] != [1, 2, 3, 4, 5]:
            raise ValueError("Expected 16 tasks per split and explicit environment seeds 1–5")
        for task in split["tasks"]:
            for seed in split["seeds"]:
                cell = run / group / f"{task}_s{seed}"
                result = read(cell / "result.json")
                seed_protocol = result["seed_protocol"]
                expected = {
                    "constructor_seed": seed, "global_environment_rng_seed": seed,
                    "native_reset_calls": 1, "reset_seed": None,
                    "video_reset_seed_override": False,
                    "first_reset_reuses_constructor_observation": True,
                }
                if any(seed_protocol.get(key) != value for key, value in expected.items()):
                    raise ValueError(f"Unexpected environment seed protocol: {task}/{seed}")
                policy = {key: value for key, value in result["policy"].items() if key != "checkpoint"}
                policy_settings.append(policy)
                split_name = group.removeprefix("composite_")
                episodes.append({
                    "split": split_name, "task": task, "seed": seed, "status": "valid",
                    **{key: result[key] for key in (
                        "any_success", "final_state_success", "first_success_native_step",
                        "native_steps", "policy_calls", "official_horizon", "elapsed_s",
                        "termination_reason", "policy_seed",
                    )},
                    "completed_at": timestamp(result["completed_at"]),
                    "seed_protocol": seed_protocol,
                    "input_audit_status": result["input_audit"]["status"],
                    "baseline_success": baseline[split_name, task, seed],
                    "runtime_base_commit": result["source"]["git_commit"],
                    "result_sha256": digest(cell / "result.json"),
                    "native_steps_sha256": digest(cell / "native_steps.jsonl"),
                    "policy_calls_sha256": digest(cell / "policy_calls.jsonl"),
                })
    if any(policy != policy_settings[0] for policy in policy_settings):
        raise ValueError("Policy settings differ across episodes")
    if len(baseline) != 160 or len({(row["split"], row["task"], row["seed"]) for row in episodes}) != 160:
        raise ValueError("Expected 160 unique task/seed cells in each comparison")
    summaries = {}
    for split_name in ("seen", "unseen", "all"):
        selected = [row for row in episodes if split_name == "all" or row["split"] == split_name]
        successes = sum(row["any_success"] for row in selected)
        final_successes = sum(row["final_state_success"] for row in selected)
        summaries[split_name] = {
            "planned": len(selected), "completed": len(selected), "pending": 0,
            "success": successes, "failure": len(selected) - successes,
            "success_rate_percent": 100 * successes / len(selected),
            "final_state_success": final_successes,
            "final_state_success_rate_percent": 100 * final_successes / len(selected),
            "baseline_success": sum(row["baseline_success"] for row in selected),
            "native_steps": sum(row["native_steps"] for row in selected),
            "policy_calls": sum(row["policy_calls"] for row in selected),
            "elapsed_s": round(sum(row["elapsed_s"] for row in selected), 3),
        }
    source_names = ("pure_vla.py", "run_pure_vla_suite.py", "summarize_pure_vla.py")
    data = {
        "schema_version": 1, "experiment": "E12", "name": "Pure RLDX-1 / no Planner",
        "status": "complete", "published_at": published_at,
        "completed_at": max(row["completed_at"] for row in episodes), "run": run.name,
        "summary": summaries, "protocol_sha256": validator.manifest_sha256(manifest),
        "protocol": manifest, "actual_policy": policy_settings[0],
        "validation": {
            "valid_cells": 160, "missing": [], "rejected": [], "errors": [],
            "environment_seed_audit": "160/160 passed", "smoke_native_steps": 32,
            "smoke_result_sha256": digest(smoke_path),
        },
        "source": {
            "repository": "https://github.com/snow-QingYang/RPent", "branch": "pure_vla",
            "runtime_base_commits": sorted({row["runtime_base_commit"] for row in episodes}),
            "evaluation_relationship": "Base commit plus frozen local source files and manifest; the branch alone is not the evaluated snapshot.",
            "files": {name: digest(run / "source" / name) for name in source_names},
            "manifest_file_sha256": digest(run / "manifest.json"),
            "summary_file_sha256": digest(run / "summary.json"),
        },
        "references": {"baseline_export_sha256": digest(baseline_path), "baseline_path": "../baseline/analysis/data.json"},
        "episodes": episodes,
        "limitations": manifest["comparison_limits"],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    columns = [key for key in episodes[0] if key != "seed_protocol"]
    with (output / "episodes.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(episodes)
    for name in ("manifest.json", "summary.json"):
        shutil.copyfile(run / name, output / name)
    (output / "source").mkdir(exist_ok=True)
    for name in source_names:
        shutil.copyfile(run / "source" / name, output / "source" / name)
    (output / "index.html").write_text(render(data), encoding="utf-8")
    return data


def table(headers, rows, label):
    heading = "".join(f'<th scope="col">{html.escape(header)}</th>' for header in headers)
    body = "".join(
        "<tr>" + "".join(f'<td data-label="{html.escape(header)}">{value}</td>' for header, value in zip(headers, row)) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap stack-small"><table aria-label="{html.escape(label)}"><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table></div>'


def rate(successes, total):
    percentage = f"{100 * successes / total:.3f}".rstrip("0").rstrip(".")
    return f"{successes} / {total} · {percentage}%"


def render(data):
    summaries = data["summary"]
    overall = summaries["all"]
    result_rows = []
    comparison_rows = []
    for split, title in (("seen", "Seen"), ("unseen", "Unseen"), ("all", "合计")):
        stats = summaries[split]
        total = stats["completed"]
        result_rows.append([title, f"{total} / {stats['planned']}", rate(stats["success"], total), str(stats["failure"])])
        comparison_rows.append([title, rate(stats["baseline_success"], total), rate(stats["success"], total)])
    results = table(["任务组", "完成 / 计划", "成功 / 成功率", "有效失败"], result_rows, "Pure VLA results by split")
    comparison = table(["任务组", "E01 · Planner 原版", "E12 · Pure VLA"], comparison_rows, "Descriptive baseline comparison with different budgets and scoring")
    matrices = []
    for split, title in (("seen", "Seen"), ("unseen", "Unseen")):
        rows = []
        for task in data["protocol"]["splits"]["composite_" + split]["tasks"]:
            cells = [row for row in data["episodes"] if row["split"] == split and row["task"] == task]
            outcomes = []
            for cell in cells:
                if cell["any_success"]:
                    symbol = "✓ 成功"
                    badge = "complete"
                else:
                    symbol, badge = "✕ 失败", "failure"
                outcomes.append(f'<span class="badge {badge}">{symbol}</span>')
            rows.append([html.escape(task), *outcomes, f"{sum(cell['any_success'] for cell in cells)} / 5", str(cells[0]["official_horizon"])])
        matrices.append(f'<h3>{title}</h3>' + table(["任务", "Seed 1", "Seed 2", "Seed 3", "Seed 4", "Seed 5", "成功 / 已评测", "动作预算"], rows, title + " task and seed outcomes"))
    final_state_differences = [row for row in data["episodes"] if row["any_success"] and not row["final_state_success"]]
    differences = "".join(
        f'<li><code>{html.escape(row["task"])} / seed {row["seed"]}</code>：第 {row["first_success_native_step"]} 个原生动作首次成功；第 {row["native_steps"]} 步动作块结束时终态不成功。该局按评测规则计为成功。</li>'
        for row in final_state_differences
    )
    base_commit = data["source"]["runtime_base_commits"][0]
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<meta name="description" content="E12 Pure VLA：RLDX-1 直接执行完整任务，无外层 Planner；160/160 完成，25 局成功，15.625%。"><link rel="icon" href="data:,"><link rel="stylesheet" href="../../project.css"><title>E12 · Pure VLA · Mobile Astra</title></head>
<body><header class="site-head"><div class="head-inner"><a class="brand" href="../../">Mobile Astra / 实验工作页</a><nav aria-label="项目导航"><a href="../../">项目总览</a><a href="../" aria-current="page">实验目录</a><a href="../../reference/">接口与真值</a></nav></div></header>
<main><nav class="crumbs" aria-label="当前位置"><a href="../../">项目总览</a><span>/</span><a href="../">实验目录</a><span>/</span><span aria-current="page">E12 · Pure VLA</span></nav>
<div class="hero"><p class="eyebrow">HARNESSVLA / ROBOCASA · E12</p><h1>Pure VLA · 直接执行完整任务</h1><p class="lead">冻结的 RLDX-1-FT-RC365 根据三路 RGB、本体状态和完整任务文字连续生成动作，独立完成任务。无外层 Planner、历史任务记忆或手工技能调度。</p><span class="badge complete">已完成 · 160 / 160 有效结果</span><p class="meta">评测完成：<time datetime="{data['completed_at']}">{data['completed_at']}</time> · 页面发布：{html.escape(data['published_at'])} · Planner：无</p><div class="links"><a href="#results">结果</a><a href="#scope">实验设置</a><a href="#comparison">与原版对照</a><a href="#matrix">32 × 5 明细</a><a href="#data">数据与代码</a></div></div>
<section id="results"><h2>完整结果</h2>{results}<p class="note">32 个 composite 任务，每个任务显式环境 seeds 1、2、3、4、5。Seen / Unseen 各 80 局；没有 atomic 任务。135 局有效失败均计入分母，不重试挑选最好结果；冒烟与中断尝试不计入这 160 局。</p></section>
<section id="scope"><h2>改变了什么，保留了什么</h2><div class="cards"><article class="card"><h3>完整任务直接交给 VLA</h3><p>每局使用原生完整任务指令，不由语言模型拆解或改写子任务；没有 <code>move_to</code>、<code>scripted_grasp</code> 等 Planner 调度的额外动作，也不读取跨任务 memory。</p><p>模型不接收三维查询结果、模拟器接触标签、<code>task_progress</code> 或 success 反馈来选择动作。success 仍供评测端评分与停止使用。</p></article><article class="card"><h3>模型需要的观察和控制保留</h3><p>左、右、腕部三路 256 × 256 RGB；末端与底盘位置／姿态、夹爪位置。模型可自行移动底盘。Pure VLA 仍使用本体状态。</p><p>视频历史索引 <code>[-6,-4,-2,0]</code>，state <code>[0]</code>；预测 16 步、执行前 8 步再观察，4 次去噪迭代。实际 checkpoint 配置为 <code>use_memory=false</code>、RTC 关闭；每局重置一次 policy。</p></article></div></section>
<section id="scoring"><h2>成功如何判定</h2><p><strong>本次确定成功 {overall['success']} 局，失败 {overall['failure']} 局。</strong>每个原生动作读取模拟器任务成功信号；动作块中曾出现成功就记为 <code>any_success=true</code>，在该动作块结束时自动停止并计成功。这与固定 RLDX 官方 rollout 的评分规则一致。</p><p class="note">自动停止在动作块返回边界检查，最多相隔 8 个动作；不是首次成功的单步立即打断。成功标签不进入模型观察，达到任务 horizon 时只执行剩余预算。</p><details><summary>终态诊断记录（不改变成功计数）</summary><p><code>final_state_success</code> 是 reset 前终态的额外记录，不是本实验的成绩。{overall['success']} 个成功结果中有 {len(final_state_differences)} 局在动作块内达到成功、结束时终态不成功；该局仍计成功，160 局主评分不变。</p><ul>{differences}</ul></details></section>
<section id="comparison"><h2>与 E01 原版的描述性对照</h2>{comparison}<p>两组覆盖相同的 32 个任务与 seeds 1–5，使用同一 RLDX-1-FT-RC365 checkpoint。E01 来自本网站的 <a href="../baseline/analysis/">160 局 Astra baseline</a>；其中“仅 VLA 动作成功”的轨迹分类仍有 Planner 选择与续调，不等同于本页 Pure VLA。</p><p class="note"><strong>这不是只移除 Planner 的严格单变量实验。</strong>E01 使用 Planner 轮数限制，本页使用每任务原生动作 horizon；历史 RPent 技能在 chunk 末检查当前 success，本页累计 chunk 内 success。相同 seed 未证明完整初始场景一致，VLA 采样也未配对固定。逐局 JSON 保留终态诊断，但不能消除预算和初始化差异。</p></section>
<section id="matrix"><h2>逐任务、逐 seed</h2><p class="note">✓ 成功；✕ 有效任务失败。每格均按本实验的主评分记录，各任务恰有 5 个有效结果；预算单位为原生 simulator action steps。</p>{''.join(matrices)}</section>
<section id="protocol"><h2>预算、seed 与运行核验</h2><p>每任务 horizon 固定为 1200–4350 个原生动作，来源于 <a href="https://github.com/RLWRLD/RLDX-1/blob/021f77618318b96eab3a7de2665a2e7813a1dfca/run_scripts/eval/robocasa_365/task_sets.yaml">RLWRLD/RLDX-1 固定版本的任务预算</a>。全组实际执行 <strong>{overall['native_steps']:,}</strong> 个原生动作，<strong>{overall['policy_calls']:,}</strong> 次模型调用；逐局实际耗时总和约 <strong>{overall['elapsed_s']/3600:.2f} 小时</strong>，不含队列空闲等待。</p><p>每个 task / seed 单独启动环境；构造与全局环境 RNG 显式使用 seeds 1–5；复用构造期第一次 reset 的观察。160 局均验证只有一次 native reset，没有录像 wrapper 的 seed 重写。模型采样 seed 由 task / seed 独立确定。</p><p>正式评测前，ScrubCuttingBoard seed 1 的 32 步真实模型冒烟通过。调度只在允许的空闲卡上派发；每局 7200 秒基础设施保护、最多 3 次基础设施尝试，普通任务失败不重跑。最终 160/160 结果通过冻结版本校验器，missing / rejected / errors 均为空。</p><p class="note">实际运行使用锁定的 RLinf 兼容 fork；这是固定模型、成功语义和动作预算下的复测，不宣称与原作者默认 50 局评测具有相同初态或样本量。完整版本与比较限制见 <a href="manifest.json">manifest</a>。</p></section>
<section id="data"><h2>数据与代码</h2><div class="links"><a class="button" href="episodes.csv" download>下载 160 局 CSV</a><a href="data.json">完整统计 JSON</a><a href="summary.json">原始汇总</a><a href="manifest.json" download>固定评测协议</a><a href="extract.py" download>统计与页面生成脚本</a><a href="https://github.com/snow-QingYang/RPent/tree/pure_vla">pure_vla 分支</a></div><p class="note">公开数据包含逐局任务、环境 seed、主评分及终态诊断、步数、耗时、seed 审计以及原始结果和动作记录的 SHA-256。原始轨迹、图像、日志与中断尝试保留在本地实验存档中。</p><details><summary>冻结的评测源码与版本</summary><p>运行基底为 <a href="https://github.com/snow-QingYang/RPent/commit/{base_commit}"><code>{base_commit[:8]}</code></a>，实际评测还包含本地修改；分支基底本身不代表完整评测版本。以下运行时冻结源码和 manifest 可下载，文件 SHA-256 记录在 data.json。</p><div class="links"><a href="source/pure_vla.py" download>单局评测</a><a href="source/run_pure_vla_suite.py" download>批量调度</a><a href="source/summarize_pure_vla.py" download>结果校验</a></div><p class="note">协议 SHA-256：<code>{data['protocol_sha256']}</code>。在原始结果目录可用 <code>python extract.py --run /path/to/pure_vla_official_32x5 --published-at {html.escape(data['published_at'])}</code> 重建本页；默认从同站 E01 导出读取参考分数。</p></details></section>
</main><footer class="site-foot"><span>E12 · Pure VLA · 160/160 完成 · {html.escape(data['published_at'])}</span><a href="../">实验目录</a></footer></body></html>
'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--published-at", default=datetime.now(ZoneInfo("Asia/Hong_Kong")).date().isoformat())
    arguments = parser.parse_args()
    exported = export(arguments.run, arguments.output, arguments.published_at)
    print(json.dumps(exported["summary"], ensure_ascii=False, indent=2))
