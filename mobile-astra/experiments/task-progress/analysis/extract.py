"""Extract the public NoTaskGT comparison from complete canonical RoboCasa runs.

Run with --baseline-run, --notask-run, --legacy-baseline-run, --manifest,
--memory-dir and --output. Inputs stay local; exported sources use run names.
Only selected outcome, timing, configuration, hashes and initial-state comparisons
are exported. No prompts, raw trajectories, images or credentials are exported.
"""

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


SPLITS = ("seen", "unseen")
SEEDS = (1, 2, 3, 4, 5)
PLANNER = {
    "backend": "codex",
    "model": "gpt-6-astra",
    "reasoning_effort": "xhigh",
    "max_turns": 100,
}
RUNTIME = {
    "cell_timeout_seconds": 3600,
    "rldx_max_chunks": 40,
    "rldx_settle_patience": 999,
    "rldx_action_steps_per_chunk": 8,
}
CSV_FIELDS = (
    "split", "task", "seed", "baseline_success", "notask_success",
    "baseline_elapsed_s", "notask_elapsed_s", "baseline_result_sha256",
    "notask_result_sha256", "baseline_states_sha256", "notask_states_sha256",
    "initial_robot_state_max_abs_diff", "initial_task_language_equal",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_matrix(manifest):
    tasks = {}
    for split in SPLITS:
        spec = manifest["splits"][f"composite_{split}"]
        names = spec["tasks"]
        require(spec["seeds"] == list(SEEDS), f"{split}: expected seeds 1–5")
        require(len(names) == len(set(names)) == 16, f"{split}: expected 16 tasks")
        require(all(re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", t) for t in names),
                f"{split}: invalid task name")
        tasks[split] = names
    require(not set(tasks["seen"]) & set(tasks["unseen"]), "Task splits overlap")
    return tasks


def check_cells(root, tasks):
    expected = {
        f"composite_{split}/{task}_s{seed}"
        for split in SPLITS for task in tasks[split] for seed in SEEDS
    }
    actual = {
        str(p.parent.relative_to(root))
        for p in root.glob("composite_*/*/result.json")
    }
    require(actual == expected,
            f"{root.name}: incorrect canonical cells; missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}")


def read_episode(root, split, task, seed, protocol_id):
    cell = root / f"composite_{split}" / f"{task}_s{seed}"
    result_path, states_path = cell / "result.json", cell / "states.json"
    result, states = read_json(result_path), read_json(states_path)
    label = f"{root.name}: {split}/{task}_s{seed}"
    require(result["valid"] is True, f"{label}: invalid result")
    require(type(result["success"]) is bool, f"{label}: success must be boolean")
    require(result["task_name"] == task and result["seed"] == seed,
            f"{label}: task or seed mismatch")
    require(result["evaluation_split"] == f"composite_{split}",
            f"{label}: evaluation split mismatch")
    require(result["environment_split"] == "target", f"{label}: environment mismatch")
    require(result["protocol_id"] == protocol_id, f"{label}: protocol mismatch")
    require(result["success_source"] == "state.success", f"{label}: success source mismatch")
    require(result["termination_reason"] == "completed", f"{label}: incomplete episode")
    require(all(result["planner"].get(k) == v for k, v in PLANNER.items()),
            f"{label}: planner configuration mismatch")
    require(all(result["runtime"].get(k) == v for k, v in RUNTIME.items()),
            f"{label}: runtime configuration mismatch")
    require(result["memory"]["profile"] == "local", f"{label}: memory profile mismatch")
    require(result["memory"]["policy"] == "task-global", f"{label}: memory policy mismatch")
    require(result["memory"]["audit_status"] == "ok", f"{label}: memory audit failed")
    require(states["steps"], f"{label}: empty state history")
    observed_success = any(s.get("extras", {}).get("success") is True
                           for s in states["steps"])
    require(observed_success == result["success"], f"{label}: states/result success mismatch")
    elapsed = result["elapsed_s"]
    require(isinstance(elapsed, (int, float)) and math.isfinite(elapsed) and elapsed >= 0,
            f"{label}: invalid duration")
    return {
        "success": result["success"],
        "elapsed_s": elapsed,
        "result_sha256": file_sha256(result_path),
        "states_sha256": file_sha256(states_path),
        "memory_files": result["memory"]["selected_files"],
        "initial": states["steps"][0],
    }


def summarize(episodes):
    return {
        "total": len(episodes),
        "baseline_success": sum(e["baseline_success"] for e in episodes),
        "notask_success": sum(e["notask_success"] for e in episodes),
        "both_success": sum(e["baseline_success"] and e["notask_success"] for e in episodes),
        "baseline_only": sum(e["baseline_success"] and not e["notask_success"] for e in episodes),
        "notask_only": sum(not e["baseline_success"] and e["notask_success"] for e in episodes),
        "neither": sum(not e["baseline_success"] and not e["notask_success"] for e in episodes),
    }


def percentage(numerator, denominator, signed=False):
    value = (Decimal(numerator) * 100 / Decimal(denominator)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{value:+.2f}" if signed else f"{value:.2f}"


def public_sources(baseline_root, notask_root, legacy_root):
    baseline = read_json(baseline_root / "run-info.json")
    notask = read_json(notask_root / "launch.json")
    legacy = read_json(legacy_root / "run-info.json")
    sources = {}
    for name, root, info, revision_key in (
        ("baseline", baseline_root, baseline, "repository_revision"),
        ("notask", notask_root, notask, "git_head"),
        ("legacy_baseline", legacy_root, legacy, "repository_revision"),
    ):
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]+", root.name)), "Invalid run name")
        require(bool(re.fullmatch(r"[a-f0-9]{40}", info[revision_key])), "Invalid revision")
        require(info["model"] == PLANNER["model"] and
                info["reasoning_effort"] == PLANNER["reasoning_effort"],
                f"{root.name}: planner metadata mismatch")
        sources[name] = {"run": root.name, "revision": info[revision_key]}
    require(baseline["memory_version"] == legacy["memory_version"] ==
            Path(notask["memory_dir"]).name == "GPT_6_astra_high", "Memory versions differ")
    require(notask["geometry"] == "official simulator world maps; no DA3",
            "Unexpected NoTaskGT geometry")
    require(notask["task_progress"] == "omitted from agent-facing observation responses",
            "Unexpected task progress setting")
    require(notask["success_and_terminated"] == "retained", "Unexpected success setting")
    require(notask["read_text_file"] == "limited to selected memory directory",
            "Unexpected read_text_file setting")
    sources["notask"]["revision_scope"] = "Official base with local task-feedback changes"
    return sources


def compare_initial(baseline, notask):
    a, b = baseline["initial"], notask["initial"]
    require(a["step_idx"] == b["step_idx"] == 0, "Missing initial step 0")
    require(a["state"].keys() == b["state"].keys(), "Initial robot-state fields differ")
    differences = []
    for key in a["state"]:
        x, y = a["state"][key], b["state"][key]
        require(len(x) == len(y), f"Initial state shape differs: {key}")
        require(all(isinstance(v, (int, float)) and math.isfinite(v) for v in x + y),
                f"Initial state contains nonfinite values: {key}")
        differences.extend(abs(xi - yi) for xi, yi in zip(x, y))
    require(bool(differences), "Empty initial robot state")
    return {
        "initial_robot_state_max_abs_diff": max(differences),
        "initial_task_language_equal": a["extras"]["task_language"] ==
                                       b["extras"]["task_language"],
    }


def audit_memory(memory_dir, baseline_root, selected_files):
    recorded = read_json(baseline_root / "memory_sha256.json")
    hashes = {}
    for name in sorted(selected_files):
        rel = Path(name)
        require(not rel.is_absolute() and ".." not in rel.parts, "Invalid memory path")
        require(name in recorded, f"Missing baseline memory hash: {name}")
        actual = file_sha256(memory_dir / rel)
        require(actual == recorded[name], f"Memory contents differ: {name}")
        hashes[name] = actual
    return {
        "selected_files_equal_pairs": 160,
        "unique_selected_files": len(hashes),
        "matching_sha256_files": len(hashes),
        "hash_reference": "Baseline launch memory_sha256.json",
        "selected_file_sha256": hashes,
        "scope": "Initial selected memory corpus; actual agent reading order may differ",
    }


def report_text(data):
    lines = [
        "# RoboCasa composite：移除任务进度反馈", "",
        "按相同任务与 seed 比较 160 局。主比较使用网站当前的 11 月 1 日 GPT-6-Astra "
        "重跑 baseline（55/160），两组均为 xhigh。", "",
        "| 分组 | Baseline | NoTaskGT | NoTaskGT − Baseline |",
        "|---|---:|---:|---:|",
    ]
    for split, label in (("seen", "Seen"), ("unseen", "Unseen"), ("all", "全部")):
        s = data["summary"][split]
        n, b, d = s["total"], s["baseline_success"], s["notask_success"]
        lines.append(f"| {label} | {b}/{n}（{percentage(b, n)}%） | "
                     f"{d}/{n}（{percentage(d, n)}%） | {percentage(d-b, n, signed=True)} pp |")
    lines += ["", "| 配对结果 | Seen | Unseen | 全部 |", "|---|---:|---:|---:|"]
    for key, label in (("both_success", "双方成功"), ("baseline_only", "仅 Baseline 成功"),
                       ("notask_only", "仅 NoTaskGT 成功"), ("neither", "双方失败")):
        lines.append("| " + label + " | " + " | ".join(
            str(data["summary"][split][key]) for split in ("seen", "unseen", "all")) + " |")
    audit, memory = data["initial_state_audit"], data["memory_audit"]
    old = data["summary"]["legacy_baseline"]
    lines += [
        "", "## 实际设置", "",
        "NoTaskGT 使用官方原始模拟器几何，未使用 DA3。`view_env_state` 及动作后的模型观测"
        "不返回 `task_progress`；`read_text_file` 限于当前允许的记忆文件，不能通过该工具读取"
        "`success_criteria.md` 或评分源码；prompt 中要求读取进度与评分规则的说明也相应修改。", "",
        "顶层 `success`、`robocasa_terminated`、原生成功判定及 VLA 成功提前停止仍保留。"
        "几何工具、接触反馈、VLA 输入与权重、动作执行流程保持官方设置。"
        "这是移除任务进度与规则读取的实验，不是完全无真值实验。"
        "内部 states.json 仍可保存模拟器进度用于记录；本报告不导出这些进度值。", "",
        "匹配配置：GPT-6-Astra / xhigh；RLDX-1-FT-RC365；Seen / Unseen 各 16 个任务、"
        "seeds 1–5；每局最多 100 个模型响应、3600 秒；每次 VLA 最多 40 chunks × 8 steps，"
        "settle patience 999。两组均使用 local / GPT_6_astra_high、同任务与全局记忆。", "",
        f"160 对结果的记忆选择完全相同；涉及 {memory['unique_selected_files']} 个唯一文件，"
        "均与 baseline 启动时保存的 SHA-256 一致。实际读取顺序由 agent 决定。", "",
        "## 初始状态与结果核对", "",
        f"初始机器人状态最大绝对差超过 1e-6 的有 {audit['robot_state_differences']} 对；"
        f"初始任务文本不同的有 {audit['task_language_differences']} 对。"
        "只比较 step 0 的 robot state 与 task_language；不比较 task_progress，"
        "也不将模型观测中缺少该字段判为场景差异。机器人状态与任务文本不能覆盖所有场景物体，"
        "这些配对只是同任务与 seed，不保证所有布局完全相同。", "",
        "主比较的 320 个 canonical result.json 均有效，并与各自 states.json 的原生成功信号核对。"
        "归档和中断尝试不计入。JSON 与 CSV 包含 160 对逐 seed 结果、耗时和两侧结果/状态文件 SHA-256；"
        "不包含原始轨迹、模型提示词或凭证。", "",
        "## 与旧 baseline 的关系", "",
        f"10 月 28 日旧 baseline 为 {old['baseline_success']}/{old['total']}（"
        f"{percentage(old['baseline_success'], old['total'])}%）；NoTaskGT 为 "
        f"{old['notask_success']}/{old['total']}，相差 {old['delta_success']} 局、"
        f"{old['delta_percentage_points']:+.2f} 个百分点。"
        "该旧批次仅作参考，页面主表与逐 seed 配对始终使用 11 月 1 日 55/160 批次。", "",
        "## 逐任务结果", "",
        "每个 seed 单元格表示 `Baseline/NoTaskGT`，1 为原生成功，0 为失败。", "",
        "| 分组 | 任务 | Baseline | NoTaskGT | s1 | s2 | s3 | s4 | s5 |",
        "|---|---|---:|---:|---|---|---|---|---|",
    ]
    for split in SPLITS:
        for task in data["tasks"][split]:
            rows = [e for e in data["episodes"] if e["split"] == split and e["task"] == task]
            cells = [f"{int(e['baseline_success'])}/{int(e['notask_success'])}" for e in rows]
            lines.append(f"| {split.title()} | {task} | {sum(e['baseline_success'] for e in rows)}/5 | "
                         f"{sum(e['notask_success'] for e in rows)}/5 | " + " | ".join(cells) + " |")
    lines += [
        "", "## 数据来源与复现", "",
        f"主 baseline：`{data['sources']['baseline']['run']}`。",
        f"NoTaskGT：`{data['sources']['notask']['run']}`。",
        f"旧 baseline：`{data['sources']['legacy_baseline']['run']}`。", "",
        "源码基线提交号分别保存在 JSON 的 sources 中；NoTaskGT 在官方基线之上包含上述本地修改。"
        "每个设置仅运行一轮，结果同时包含任务随机性与 planner 执行差异，不能把观察差值当作稳定因果效应。", "",
        "```sh",
        "python extract.py --baseline-run <11月1日baseline目录> --notask-run <NoTaskGT目录> \\",
        "  --legacy-baseline-run <10月28日baseline目录> --manifest <target50.json> \\",
        "  --memory-dir <NoTaskGT初始记忆目录> --output <输出目录>",
        "```", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline-run", "notask-run", "legacy-baseline-run", "manifest", "memory-dir", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    manifest = read_json(args.manifest)
    tasks = task_matrix(manifest)
    sources = public_sources(args.baseline_run, args.notask_run, args.legacy_baseline_run)
    for root in (args.baseline_run, args.notask_run, args.legacy_baseline_run):
        check_cells(root, tasks)
    episodes, legacy_episodes, selected_files = [], [], set()
    for split in SPLITS:
        for task in tasks[split]:
            for seed in SEEDS:
                baseline = read_episode(args.baseline_run, split, task, seed, manifest["protocol_id"])
                notask = read_episode(args.notask_run, split, task, seed, manifest["protocol_id"])
                legacy = read_episode(args.legacy_baseline_run, split, task, seed, manifest["protocol_id"])
                require(baseline["memory_files"] == notask["memory_files"] == legacy["memory_files"],
                        f"{split}/{task}_s{seed}: selected memory files differ")
                selected_files.update(notask["memory_files"])
                row = {"split": split, "task": task, "seed": seed, **compare_initial(baseline, notask)}
                for name, result in (("baseline", baseline), ("notask", notask)):
                    row.update({f"{name}_{key}": value for key, value in result.items()
                                if key not in {"memory_files", "initial"}})
                episodes.append(row)
                legacy_episodes.append({"split": split, "baseline_success": legacy["success"],
                                        "notask_success": notask["success"]})
    summary = {split: summarize([e for e in episodes if e["split"] == split]) for split in SPLITS}
    summary["all"] = summarize(episodes)
    old = summarize(legacy_episodes)
    old.update({"run": sources["legacy_baseline"]["run"],
                "delta_success": old["notask_success"] - old["baseline_success"],
                "delta_percentage_points": float(percentage(
                    old["notask_success"] - old["baseline_success"], old["total"])),
                "comparison_role": "Historical reference; not the main paired baseline"})
    summary["legacy_baseline"] = old
    data = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "benchmark": "RoboCasa composite", "environment_split": "target",
            "protocol_id": manifest["protocol_id"], "planner": PLANNER,
            "runtime": RUNTIME, "seeds": list(SEEDS), "tasks_per_split": 16,
            "memory_profile": "local", "memory_version": "GPT_6_astra_high",
            "memory_policy": "Same task and global memory, on-demand reading",
            "vla": "RLDX-1-FT-RC365", "geometry": "Official simulator depth and world maps",
            "da3": False,
            "task_progress": "Omitted from agent-facing observations; internal state records retained",
            "read_text_file": "Restricted to the selected memory directory and memory policy",
            "success_criteria": "Not readable through read_text_file",
            "prompt_changes": "Removed instructions to inspect task_progress and scoring source; completion assessed from observations",
            "success": "Retained", "robocasa_terminated": "Retained",
            "contact_feedback": "Retained", "native_success_and_vla_early_stop": "Retained",
            "success_source": "state.success", "states_crosschecked": 320,
            "legacy_states_crosschecked": 160,
            "manifest_sha256": file_sha256(args.manifest),
            "comparison": "One run per setting, paired by task and seed",
        },
        "sources": sources,
        "initial_state_audit": {
            "pairs_checked": len(episodes), "robot_state_threshold": 1e-6,
            "robot_state_differences": sum(e["initial_robot_state_max_abs_diff"] > 1e-6 for e in episodes),
            "task_language_differences": sum(not e["initial_task_language_equal"] for e in episodes),
            "task_progress_comparison": "not_applicable",
            "scope": "Step-0 robot state and task_language only; does not establish equality of all scene objects",
        },
        "memory_audit": audit_memory(args.memory_dir, args.baseline_run, selected_files),
        "summary": summary, "tasks": tasks, "episodes": episodes,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    with (args.output / "episodes.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(episodes)
    (args.output / "report.md").write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"summary": summary, "initial_state_audit": data["initial_state_audit"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
