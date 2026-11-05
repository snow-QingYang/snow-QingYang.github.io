"""Build the public NoContactGT comparison from two completed canonical runs.

Inputs are local paths supplied on the command line. Exports contain run names,
selected outcomes, aggregate action counts and SHA-256 hashes, not absolute
paths, model messages, prompts, raw trajectories, credentials or image data.
The script performs no simulator, model, network or Git operations.
"""

import argparse
import ast
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


SPLITS = ("seen", "unseen")
SEEDS = (1, 2, 3, 4, 5)
BASE_REVISION = "a744bd5f128ebef3cb8c6736cf7cd98adff681f1"
REMOVED = ("grasp_contact", "grasp_obj", "grasped", "grasp_detected")
VLA_ACTIONS = {"rldx_skill", "rldx_arm"}
PLANNER = {
    "backend": "codex", "model": "gpt-6-astra", "reasoning_effort": "xhigh",
    "max_turns": 100,
}
RUNTIME = {
    "cell_timeout_seconds": 3600, "rldx_max_chunks": 40,
    "rldx_settle_patience": 999, "rldx_action_steps_per_chunk": 8,
}
ROBOT_STATE_THRESHOLD = 1e-6
CASE_CELLS = (
    ("unseen", "WeighIngredients", 5),
    ("unseen", "MakeIceLemonade", 3),
    ("seen", "PackIdenticalLunches", 4),
    ("unseen", "PanTransfer", 3),
)
CSV_FIELDS = (
    "split", "task", "seed", "baseline_success", "nocontact_success",
    "baseline_elapsed_s", "nocontact_elapsed_s", "baseline_termination_reason",
    "nocontact_termination_reason", "baseline_final_native_success",
    "nocontact_final_native_success", "baseline_final_terminated",
    "nocontact_final_terminated", "baseline_result_sha256", "nocontact_result_sha256",
    "baseline_states_sha256", "nocontact_states_sha256",
    "initial_robot_state_max_abs_diff", "initial_robot_state_exact_equal",
    "initial_task_language_equal",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_relative(name):
    path = Path(name)
    require(isinstance(name, str) and not path.is_absolute() and ".." not in path.parts,
            "Expected a relative source or memory filename")
    return path


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
    expected = {f"composite_{s}/{t}_s{seed}"
                for s in SPLITS for t in tasks[s] for seed in SEEDS}
    actual = {str(p.parent.relative_to(root))
              for p in root.glob("composite_*/*/result.json")}
    require(actual == expected,
            f"{root.name}: canonical cells differ; missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}")


def progress_filter(source_repo, tasks):
    """Read the published filter declaration without importing simulator code."""
    tree = ast.parse((source_repo / "robots/robocasa/primitives.py").read_text())
    declaration = next((n.value for n in tree.body if isinstance(n, ast.AnnAssign)
                        and isinstance(n.target, ast.Name)
                        and n.target.id == "_CONTACT_PROGRESS_FIELDS"), None)
    require(isinstance(declaration, ast.Dict), "Missing contact-progress filter")
    result = {}
    for key, value in zip(declaration.keys, declaration.values):
        require(isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                and value.func.id == "frozenset" and len(value.args) == 1,
                "Unexpected filter declaration")
        task, fields = ast.literal_eval(key), ast.literal_eval(value.args[0])
        require(isinstance(fields, set) and all(isinstance(f, str) for f in fields),
                "Invalid contact-progress field set")
        result[task] = fields
    require(set(result) <= set(tasks["seen"] + tasks["unseen"]), "Unexpected filtered task")
    require(len(result) == 25 and sum(map(len, result.values())) == 60,
            "Contact-progress scope differs from the reviewed experiment")
    return result


def dictionary_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from dictionary_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionary_keys(child)


def read_episode(root, split, task, seed, protocol_id, filters=None):
    cell = root / f"composite_{split}" / f"{task}_s{seed}"
    result_path, states_path = cell / "result.json", cell / "states.json"
    result, document = read_json(result_path), read_json(states_path)
    label = f"{root.name}: {split}/{task}_s{seed}"
    require(result["valid"] is True, f"{label}: invalid result")
    require(type(result["success"]) is bool, f"{label}: success must be boolean")
    require(result["task_name"] == task and type(result["seed"]) is int
            and result["seed"] == seed, f"{label}: task or seed mismatch")
    require(result["evaluation_split"] == f"composite_{split}", f"{label}: split mismatch")
    require(result["environment_split"] == "target", f"{label}: environment mismatch")
    require(result["protocol_id"] == protocol_id, f"{label}: protocol mismatch")
    require(result["success_source"] == "state.success", f"{label}: success source mismatch")
    require(result["termination_reason"] in {"completed", "planner_timeout"},
            f"{label}: unexpected termination reason")
    require(all(result["planner"].get(k) == v for k, v in PLANNER.items()),
            f"{label}: planner configuration mismatch")
    require(all(result["runtime"].get(k) == v for k, v in RUNTIME.items()),
            f"{label}: runtime configuration mismatch")
    memory = result["memory"]
    require(memory["profile"] == "local" and memory["policy"] == "task-global"
            and memory["audit_status"] == "ok", f"{label}: memory configuration/audit mismatch")
    require(len(memory["selected_files"]) == len(set(memory["selected_files"])),
            f"{label}: duplicate memory file selection")
    steps = document["steps"]
    require(steps and [s["step_idx"] for s in steps] == list(range(len(steps))),
            f"{label}: missing or noncontiguous observation history")
    require(all(type(s.get("extras", {}).get("success")) is bool for s in steps),
            f"{label}: missing native success signals")
    final = steps[-1]
    require(type(final["terminated"]) is bool, f"{label}: invalid terminated flag")
    require(final["extras"]["success"] == result["success"],
            f"{label}: final native success disagrees with result")
    require(any(s["extras"]["success"] for s in steps) == result["success"],
            f"{label}: transient native success disagrees with final result")
    elapsed = result["elapsed_s"]
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0,
            f"{label}: invalid duration")
    audit = Counter(observations=len(steps))
    actions = Counter()
    for step in steps:
        action = step.get("command", {}).get("action")
        output = step.get("result", {})
        progress = step["extras"].get("task_progress", {})
        require(isinstance(progress, dict), f"{label}: task progress is not an object")
        if action:
            require(bool(re.fullmatch(r"[a-z_]+", action)), f"{label}: invalid action name")
            actions[action] += 1
        if filters is not None:
            require(not set(REMOVED).intersection(dictionary_keys(output)),
                    f"{label}, step {step['step_idx']}: forbidden VLA result field")
            require(not filters.get(task, set()).intersection(progress),
                    f"{label}, step {step['step_idx']}: forbidden progress field")
            audit["observations_with_nonempty_progress"] += bool(progress)
            if action in VLA_ACTIONS:
                audit["vla_action_records"] += 1
                audit["vla_records_with_held_apart"] += "held_apart" in output
                audit["interrupted_vla_records"] += output.get("interrupted") is True
    first = next((s for s in steps if s["extras"]["success"]), None)
    return {
        "success": result["success"], "elapsed_s": elapsed,
        "termination_reason": result["termination_reason"],
        "final_native_success": final["extras"]["success"],
        "final_terminated": final["terminated"],
        "result_sha256": file_sha256(result_path), "states_sha256": file_sha256(states_path),
        "memory_files": memory["selected_files"], "initial": steps[0],
        "feedback_audit": audit,
        "case": {
            "success": result["success"], "elapsed_s": elapsed,
            "action_records": sum(actions.values()), "actions": dict(actions),
            "vla_action_records": sum(actions.get(a, 0) for a in VLA_ACTIONS),
            "other_action_records": sum(n for a, n in actions.items() if a not in VLA_ACTIONS),
            "first_native_success": None if first is None else {
                "step": first["step_idx"], "action": first.get("command", {}).get("action"),
                "action_ok": first.get("result", {}).get("ok"),
            },
            "final_progress_keys": sorted(final["extras"].get("task_progress", {})),
        },
    }


def compare_initial(baseline, nocontact):
    a, b = baseline["initial"], nocontact["initial"]
    require(a["state"].keys() == b["state"].keys(), "Initial robot-state fields differ")
    differences = []
    for key in a["state"]:
        x, y = a["state"][key], b["state"][key]
        require(isinstance(x, list) and isinstance(y, list) and len(x) == len(y),
                f"Initial robot-state shape differs: {key}")
        require(all(type(v) in (int, float) and math.isfinite(v) for v in x + y),
                f"Invalid initial robot-state value: {key}")
        differences.extend(abs(xi - yi) for xi, yi in zip(x, y))
    require(bool(differences), "Empty initial robot state")
    require(isinstance(a["extras"]["task_language"], str)
            and isinstance(b["extras"]["task_language"], str), "Invalid task language")
    return {
        "initial_robot_state_max_abs_diff": max(differences),
        "initial_robot_state_exact_equal": a["state"] == b["state"],
        "initial_task_language_equal": a["extras"]["task_language"] == b["extras"]["task_language"],
    }


def public_sources(args):
    baseline = read_json(args.baseline_run / "run-info.json")
    nocontact = read_json(args.nocontact_run / "run_manifest.json")
    require(baseline["repository_revision"] == nocontact["git_head"] == BASE_REVISION,
            "Unexpected official experiment base")
    require(nocontact["status"] == "completed", "NoContactGT suite is not completed")
    for info in (baseline, nocontact):
        require(info["model"] == PLANNER["model"]
                and info["reasoning_effort"] == PLANNER["reasoning_effort"],
                "Planner source metadata differs")
    require(baseline["memory_version"] == Path(nocontact["memory_dir"]).name
            == "GPT_6_astra_high", "Memory versions differ")
    require(nocontact["geometry"] == "original simulator world maps; no DA3",
            "Unexpected NoContactGT geometry")
    require(nocontact["task_progress"]
            == "contact-derived fields removed for reviewed 32 tasks; other progress retained",
            "Unexpected task-progress configuration")
    require(nocontact["success_and_terminated"] == "retained", "Unexpected success configuration")
    require(nocontact["read_text_file"]
            == "baseline behavior; static scoring rules and historical memory retained",
            "Unexpected file-reading configuration")
    require(set(nocontact["removed_vla_result_fields"]) == set(REMOVED),
            "Unexpected removed VLA result fields")
    source_hashes = {}
    for name, expected in nocontact["source_sha256"].items():
        if name.startswith("robots/"):
            path = safe_relative(name)
            actual = file_sha256(args.source_repo / path)
            require(actual == expected, f"Source differs from launch snapshot: {name}")
            source_hashes[name] = actual
    require(len(source_hashes) == 7, "Incomplete runtime source snapshot")
    sources = {}
    for name, root, metadata in (
        ("baseline", args.baseline_run, "run-info.json"),
        ("nocontact", args.nocontact_run, "run_manifest.json"),
    ):
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]+", root.name)), "Invalid public run name")
        sources[name] = {
            "run": root.name, "revision": BASE_REVISION,
            "metadata_file": metadata, "metadata_sha256": file_sha256(root / metadata),
        }
    sources["nocontact"].update({
        "revision_scope": "Official base with the local contact-feedback ablation",
        "source_files_sha256": source_hashes,
        "finished_at": nocontact["finished_at"],
    })
    return sources, nocontact


def audit_memory(args, nocontact_manifest, selected_files, pairs):
    baseline_path = args.baseline_run / "memory_sha256.json"
    baseline = read_json(baseline_path)
    launch = nocontact_manifest["initial_memory_sha256"]
    require(baseline == launch, "Launch memory corpora differ")
    hashes = {}
    for name in sorted(selected_files):
        rel = safe_relative(name)
        require(name in baseline, f"Missing launch memory hash: {name}")
        actual = file_sha256(args.memory_dir / rel)
        require(actual == baseline[name], f"Selected memory changed since launch: {name}")
        hashes[name] = actual
    return {
        "selected_files_equal_pairs": pairs,
        "matching_launch_sha256_files": len(launch),
        "unique_selected_files": len(hashes), "matching_sha256_files": len(hashes),
        "hash_reference": "Baseline memory_sha256.json and NoContactGT run_manifest.json",
        "baseline_hash_manifest_sha256": file_sha256(baseline_path),
        "selected_file_sha256": hashes,
        "scope": "Launch corpus and selected files; actual reading order is not constrained to match",
    }


def summarize(episodes):
    result = {
        "total": len(episodes),
        "baseline_success": sum(e["baseline_success"] for e in episodes),
        "nocontact_success": sum(e["nocontact_success"] for e in episodes),
        "both_success": sum(e["baseline_success"] and e["nocontact_success"] for e in episodes),
        "baseline_only": sum(e["baseline_success"] and not e["nocontact_success"] for e in episodes),
        "nocontact_only": sum(not e["baseline_success"] and e["nocontact_success"] for e in episodes),
        "neither": sum(not e["baseline_success"] and not e["nocontact_success"] for e in episodes),
    }
    return result


def percentage(numerator, denominator, signed=False):
    value = (Decimal(numerator) * 100 / Decimal(denominator)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{value:+.2f}" if signed else f"{value:.2f}"


def report_text(data):
    lines = [
        "# RoboCasa composite：接触反馈移除对照", "",
        "官方 RPent · GPT-6-Astra / xhigh · RLDX-1-FT-RC365。"
        "主对照为网站 E01 的 11 月 1 日 baseline 重跑；两组各 160 个有效 episode。", "",
        "| 任务组 | Baseline | NoContactGT | 成功率差 |",
        "|---|---:|---:|---:|",
    ]
    for split, label in (("seen", "Seen"), ("unseen", "Unseen"), ("all", "总计")):
        s = data["summary"][split]
        n, b, c = s["total"], s["baseline_success"], s["nocontact_success"]
        lines.append(f"| {label} | {b}/{n} · {percentage(b, n)}% | "
                     f"{c}/{n} · {percentage(c, n)}% | {percentage(c-b, n, True)} pp |")
    lines += ["", "| 配对结果 | Seen | Unseen | 总计 |", "|---|---:|---:|---:|"]
    for key, label in (("both_success", "双方成功"), ("baseline_only", "仅 baseline 成功"),
                       ("nocontact_only", "仅 NoContactGT 成功"), ("neither", "双方失败")):
        lines.append("| " + label + " | " + " | ".join(
            str(data["summary"][s][key]) for s in ("seen", "unseen", "all")) + " |")
    audit, memory, feedback = data["initial_state_audit"], data["memory_audit"], data["feedback_audit"]
    lines += [
        "", "## 实际移除与保留", "",
        "两个 RLDX 技能不再返回 `grasp_contact`、`grasp_obj`、`grasped`、`grasp_detected`，"
        "执行封装也不再为这些字段查询模拟器接触。`task_progress` 按任务过滤接触派生标量："
        "25 个任务、60 个任务—字段条目。过滤发生在保存状态之前，其他进度保留。", "",
        "保留 `held_apart`（闭合命令与夹爪开度启发式）、`gripper_qpos`、末端高度变化 `peak_lift`，"
        "以及原版模拟器深度和世界坐标图、相机标定、本体状态、顶层成功与终止信号、"
        "评分规则访问和历史记忆。Prompt、VLA 输入与权重、动作转换、历史连续性和预算不变。"
        "没有叠加 DA3 或 NoTaskGT。", "",
        "`PrepareCoffee.contact_check` 是几何距离判据，因此仍保留。相反，"
        "`ScrubCuttingBoard.sweep_range` 来自接触位置，因此被过滤。过滤按已审核来源，"
        "不按字段名是否含 contact。完整任务—字段表保存在 JSON 的 protocol 中。", "",
        "顶层成功仍可能依赖接触；评分源码、历史记忆、原生 Planner 能力仍保留。"
        "这是显式接触反馈的消融，不是完全无真值或文件／RPC 隔离。", "",
        "## 数据与比较核验", "",
        f"320 个结果均有效，逐一与末条保存观测的原生 success 核对一致。NoContactGT 有 159 局"
        "正常完成及 1 局有效超时失败（PortionHotDogs seed 2，3631.6 秒）；超时局保留在分母中。"
        "只统计 canonical 目录，归档与中断重试不重复计入。", "",
        f"检查 NoContactGT 的 {feedback['observations']} 条保存观测，未发现上述 4 个结果字段，"
        "也未发现各任务应过滤的实时进度字段。此检查不覆盖历史记忆内容或所有原生 Planner 通道。", "",
        f"两组的 {memory['matching_launch_sha256_files']} 个启动记忆文件 SHA-256 一致；160 对结果的"
        f"记忆选择相同，涉及 {memory['unique_selected_files']} 个唯一文件，其当前 SHA-256 也一致。"
        "实际读取顺序可以不同。", "",
        f"初始机器人状态最大绝对差 >1e-6 的有 {audit['robot_state_differences']} 对，"
        f"任务文本不同的有 {audit['task_language_differences']} 对。逐值完全相等口径下有 "
        f"{audit['exact_robot_state_differences']} 对机器人状态不同，其中部分差异低于阈值。"
        "检查仅覆盖 step 0 的本体状态和任务文本，未覆盖所有物体；不比较按实验设置过滤的进度。", "",
        "每个任务只有 5 个 seed，每种设置只运行一轮；VLA 动作采样未随场景 seed 固定。"
        "这些同任务、同 seed 的结果变化不等于"
        "稳定的因果效应；不能从单个失败反推某条被移除信息必不可少。", "",
        "## 代表案例", "",
        "以下动作数来自 states.json 的动作记录，不包括读图、读文件等只读工具调用。"
        "[六个新增成功的动作过程与图片](../cases/)。", "",
        "| 任务 / seed | Baseline | NoContactGT | NoContactGT 动作 | 首次原生成功 |",
        "|---|---|---|---|---|",
    ]
    for case in data["cases"]:
        b, c = case["baseline"], case["nocontact"]
        first = c["first_native_success"]
        location = "未成功" if first is None else f"step {first['step']} / {first['action']}"
        lines.append(f"| {case['task']} s{case['seed']} | {'成功' if b['success'] else '失败'}，"
                     f"{b['elapsed_s']} s | {'成功' if c['success'] else '失败'}，{c['elapsed_s']} s | "
                     f"{c['vla_action_records']} VLA + {c['other_action_records']} 其他动作 | {location} |")
    lines += [
        "", "最后完成的 WeighIngredients seed 5：9 次 rldx_arm 加 3 次 move_to 后原生任务成功，"
        "随后 Agent 调用 finish(success)。最后一次 move_to 的 ok=false，只代表没有达到该动作的"
        "位置容差；它不覆盖环境任务的成功判定。该局不返回 packaged_food_on_digital_scale，"
        "仍返回 gripper_obj_far、obj_upright、cabinet_closed。", "",
        "PackIdenticalLunches seed 4：baseline 用 6 次 VLA 完成；NoContactGT 的进度为空，"
        "16 次 VLA 与 39 次其他动作后仍失败。这是轨迹差异，不能单独证明缺少进度导致失败。", "",
        "## 逐任务与 seed", "",
        "每个 seed 为 `Baseline/NoContactGT`，1 表示原生成功，0 表示失败。", "",
        "| 分组 | 任务 | Baseline | NoContactGT | s1 | s2 | s3 | s4 | s5 |",
        "|---|---|---:|---:|---|---|---|---|---|",
    ]
    for split in SPLITS:
        for task in data["tasks"][split]:
            rows = [e for e in data["episodes"] if e["split"] == split and e["task"] == task]
            cells = [f"{int(e['baseline_success'])}/{int(e['nocontact_success'])}" for e in rows]
            lines.append(f"| {split.title()} | {task} | {sum(e['baseline_success'] for e in rows)}/5 | "
                         f"{sum(e['nocontact_success'] for e in rows)}/5 | " + " | ".join(cells) + " |")
    lines += ["", "## 数据来源与重建", ""]
    for label in ("baseline", "nocontact"):
        source = data["sources"][label]
        lines.append(f"{label}：`{source['run']}`；官方基线 `{source['revision']}`。")
    lines += [
        "", "JSON / CSV 保存逐局 result.json 与 states.json 的 SHA-256；JSON 另含启动元数据、"
        "实际源文件、任务清单、记忆和本统计脚本的 SHA-256。NoContactGT 的 revision 表示官方"
        "基线，具体本地修改由 source_files_sha256 标识。原始运行文件不随网页发布。", "",
        "```sh", "python extract.py --baseline-run <baseline目录> --nocontact-run <NoContactGT目录> \\",
        "  --manifest <target50.json> --source-repo <NoContactGT源码目录> \\",
        "  --memory-dir <原任务记忆目录> --output <本分析输出目录>", "```", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline-run", "nocontact-run", "manifest", "source-repo", "memory-dir", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    manifest = read_json(args.manifest)
    tasks = task_matrix(manifest)
    sources, launch = public_sources(args)
    filters = progress_filter(args.source_repo, tasks)
    for root in (args.baseline_run, args.nocontact_run):
        check_cells(root, tasks)
    episodes, cases, selected_files, feedback = [], [], set(), Counter()
    for split in SPLITS:
        for task in tasks[split]:
            for seed in SEEDS:
                baseline = read_episode(args.baseline_run, split, task, seed, manifest["protocol_id"])
                nocontact = read_episode(args.nocontact_run, split, task, seed, manifest["protocol_id"], filters)
                require(baseline["memory_files"] == nocontact["memory_files"],
                        f"{split}/{task}_s{seed}: selected memory files differ")
                selected_files.update(nocontact["memory_files"])
                row = {"split": split, "task": task, "seed": seed, **compare_initial(baseline, nocontact)}
                for label, value in (("baseline", baseline), ("nocontact", nocontact)):
                    for key in ("success", "elapsed_s", "termination_reason", "final_native_success",
                                "final_terminated", "result_sha256", "states_sha256"):
                        row[f"{label}_{key}"] = value[key]
                episodes.append(row)
                feedback.update(nocontact["feedback_audit"])
                if (split, task, seed) in CASE_CELLS:
                    cases.append({"split": split, "task": task, "seed": seed,
                                  "baseline": baseline["case"], "nocontact": nocontact["case"]})
    cases.sort(key=lambda c: CASE_CELLS.index((c["split"], c["task"], c["seed"])))
    summary = {s: summarize([e for e in episodes if e["split"] == s]) for s in SPLITS}
    summary["all"] = summarize(episodes)
    data = {
        "schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "benchmark": "RoboCasa composite", "environment_split": "target",
            "protocol_id": manifest["protocol_id"], "planner": PLANNER, "runtime": RUNTIME,
            "seeds": list(SEEDS), "tasks_per_split": 16, "vla": "RLDX-1-FT-RC365",
            "memory_profile": "local", "memory_version": "GPT_6_astra_high",
            "geometry": "Original simulator depth and world maps; known camera calibration retained",
            "da3": False, "notaskgt": False,
            "removed_vla_result_fields": list(REMOVED),
            "removed_progress_fields_by_task": {t: sorted(fs) for t, fs in sorted(filters.items())},
            "filtered_tasks": len(filters), "filtered_task_field_pairs": sum(map(len, filters.values())),
            "retained_skill_feedback": ["held_apart", "gripper_qpos", "peak_lift", "status"],
            "task_progress": "Reviewed contact-derived fields removed before persistence; other progress retained",
            "read_text_file": "Baseline permissions; static scoring rules and historical memory retained",
            "prompt_changes": "None", "success": "Retained", "robocasa_terminated": "Retained",
            "native_success_and_vla_early_stop": "Retained", "success_source": "state.success",
            "states_crosschecked": 320, "manifest_sha256": file_sha256(args.manifest),
            "comparison": "One run per setting, paired by task and seed; not full-scene equivalence",
        },
        "sources": sources,
        "initial_state_audit": {
            "pairs_checked": len(episodes), "robot_state_threshold": ROBOT_STATE_THRESHOLD,
            "robot_state_differences": sum(e["initial_robot_state_max_abs_diff"] > ROBOT_STATE_THRESHOLD for e in episodes),
            "exact_robot_state_differences": sum(not e["initial_robot_state_exact_equal"] for e in episodes),
            "task_language_differences": sum(not e["initial_task_language_equal"] for e in episodes),
            "scope": "Step-0 robot state and task_language; task_progress excluded, full object state not checked",
        },
        "memory_audit": audit_memory(args, launch, selected_files, len(episodes)),
        "feedback_audit": {
            **feedback, "episodes_checked": len(episodes), "forbidden_vla_result_fields_found": 0,
            "forbidden_progress_fields_found": 0,
            "scope": "Saved current action results and task_progress; not historical memory or all native planner channels",
        },
        "validation": {
            "canonical_results_checked": 320, "all_results_valid": True,
            "final_native_success_matches": 320, "any_recorded_success_matches": 320,
            "archived_attempts_included": False, "source_snapshot_matches": True,
            "extractor_sha256": file_sha256(Path(__file__)),
            "termination_reasons": {label: dict(Counter(e[f"{label}_termination_reason"]
                                                        for e in episodes))
                                    for label in ("baseline", "nocontact")},
        },
        "summary": summary, "tasks": tasks, "episodes": episodes, "cases": cases,
    }
    serialized = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    report = report_text(data)
    for content in (serialized, report):
        require(not re.search(r"/(?:home|mnt)/|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}", content),
                "Private path or credential-like text in public output")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "data.json").write_text(serialized, encoding="utf-8")
    with (args.output / "episodes.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(episodes)
    (args.output / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"summary": summary, "initial_state_audit": data["initial_state_audit"],
                      "feedback_audit": data["feedback_audit"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
