"""Extract a public paired report from two complete RoboCasa composite runs.

Example from a workspace containing both repositories:
    python extract.py \
        --baseline-run HarnessVLA-RPent/runs/composite_main_astra_rerun_20261101T150450Z \
        --da3-run HarnessVLA-RPent-NoGeomGT/runs/composite_da3_astra_20261103 \
        --manifest HarnessVLA-RPent/robots/robocasa/eval/target50.json \
        --output geometry-da3

Only canonical result.json and states.json files are read for episode outcomes.
Archived attempts, prompts, images, credentials, and session logs are not exported.
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
    "split", "task", "seed", "baseline_success", "da3_success",
    "baseline_elapsed_s", "da3_elapsed_s", "baseline_result_sha256",
    "da3_result_sha256", "baseline_states_sha256", "da3_states_sha256",
    "initial_robot_state_max_abs_diff", "initial_task_language_equal",
    "initial_task_progress_equal",
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
        "da3_success": sum(e["da3_success"] for e in episodes),
        "both_success": sum(e["baseline_success"] and e["da3_success"] for e in episodes),
        "baseline_only": sum(e["baseline_success"] and not e["da3_success"] for e in episodes),
        "da3_only": sum(not e["baseline_success"] and e["da3_success"] for e in episodes),
        "neither": sum(not e["baseline_success"] and not e["da3_success"] for e in episodes),
    }


def public_sources(baseline_root, da3_root):
    baseline = read_json(baseline_root / "run-info.json")
    da3 = read_json(da3_root / "run_manifest.json")
    require(baseline["repository_revision"] == da3["base_commit"], "Base revisions differ")
    revision = baseline["repository_revision"]
    require(bool(re.fullmatch(r"[a-f0-9]{40}", revision)), "Invalid source revision")
    require(baseline["memory_version"] == Path(da3["memory_dir"]).name == "GPT_6_astra_high",
            "Memory versions differ")
    require("DA3METRIC-LARGE" in da3["geometry"], "Unexpected depth model")
    for root, info in ((baseline_root, baseline), (da3_root, da3)):
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]+", root.name)), "Invalid public run name")
        require(info["model"] == PLANNER["model"] and
                info["reasoning_effort"] == PLANNER["reasoning_effort"],
                f"{root.name}: run metadata planner mismatch")
    return {
        "baseline": {"run": baseline_root.name, "revision": revision},
        "da3": {
            "run": da3_root.name, "revision": revision,
            "revision_scope": "Base revision with local DA3 geometry changes",
        },
    }


def percentage(numerator, denominator, signed=False):
    value = (Decimal(numerator) * 100 / Decimal(denominator)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{value:+.2f}" if signed else f"{value:.2f}"


def report_text(data):
    lines = [
        "# RoboCasa composite：模拟器深度与 DA3 深度", "",
        "按任务、seed 对齐比较 160 局。Baseline 为 11 月 1–2 日 Astra 重跑批次；"
        "两组均为 GPT-6-Astra / xhigh。", "",
        "| 分组 | Baseline | DA3 | DA3 − Baseline |",
        "|---|---:|---:|---:|",
    ]
    for split, label in (("seen", "Seen"), ("unseen", "Unseen"), ("all", "全部")):
        s = data["summary"][split]
        n, b, d = s["total"], s["baseline_success"], s["da3_success"]
        lines.append(f"| {label} | {b}/{n}（{percentage(b, n)}%） | "
                     f"{d}/{n}（{percentage(d, n)}%） | {percentage(d-b, n, signed=True)} pp |")
    s = data["summary"]["all"]
    lines += [
        "", f"配对结果：双方成功 {s['both_success']} 局，仅 Baseline 成功 {s['baseline_only']} 局，"
        f"仅 DA3 成功 {s['da3_only']} 局，双方失败 {s['neither']} 局。", "",
        f"Baseline 批次：`{data['sources']['baseline']['run']}`；DA3 批次：`{data['sources']['da3']['run']}`。",
        f"初始状态核对：{data['initial_state_audit']['robot_state_differences']} 对机器人状态最大绝对差超过 1e-6；"
        f"{data['initial_state_audit']['task_language_differences']} 对任务文本不同，"
        f"{data['initial_state_audit']['task_progress_differences']} 对初始任务进度不同。"
        "这些检查不覆盖全部场景物体；相同 seed 不保证场景完全一致，不能将全部差异归因于深度替换。", "",
        "本实验仅将 `back_project_batch` 与 `query_world_map` 的几何来源替换为 "
        "DA3METRIC-LARGE 从 RGB 估计的米制深度。相机内参 K 与相机位姿仍为已知的模拟器数据；"
        "其他真值接口、任务进度与成功反馈、VLA 输入和权重、记忆、提示词与控制流程保留 baseline 设置。"
        "因此这是深度来源替换实验，并非完全无真值实验。", "",
        "配置：Seen / Unseen 各 16 个任务，seeds 1–5；相同的 GPT_6_astra_high 初始记忆；"
        "每局最多 100 个模型响应、3600 秒；RLDX 每次最多 40 chunks × 8 steps，settle patience 999。", "",
        "成功来自环境 `state.success`。320 个 canonical result.json 均有效，并与各自 states.json "
        "交叉核对；归档、中断尝试不计入。CSV 与 JSON 包含 160 条配对记录及源文件 SHA-256。", "",
        "每个设置仅运行一轮。上述差异是这两批相同任务与种子的观察结果，不能据此认定稳定收益或显著退化。", "",
        "复现：运行 `extract.py --baseline-run <baseline目录> --da3-run <DA3目录> "
        "--manifest <target50.json> --output <输出目录>`。", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", type=Path, required=True)
    parser.add_argument("--da3-run", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = read_json(args.manifest)
    tasks = task_matrix(manifest)
    sources = public_sources(args.baseline_run, args.da3_run)
    for root in (args.baseline_run, args.da3_run):
        check_cells(root, tasks)
    episodes = []
    for split in SPLITS:
        for task in tasks[split]:
            for seed in SEEDS:
                baseline = read_episode(args.baseline_run, split, task, seed, manifest["protocol_id"])
                da3 = read_episode(args.da3_run, split, task, seed, manifest["protocol_id"])
                require(baseline["memory_files"] == da3["memory_files"],
                        f"{split}/{task}_s{seed}: selected memory files differ")
                row = {"split": split, "task": task, "seed": seed}
                ai, bi = baseline["initial"], da3["initial"]
                row["initial_robot_state_max_abs_diff"] = max(
                    abs(x-y) for k in ai["state"] for x, y in zip(ai["state"][k], bi["state"][k]))
                row["initial_task_language_equal"] = ai["extras"]["task_language"] == bi["extras"]["task_language"]
                row["initial_task_progress_equal"] = ai["extras"]["task_progress"] == bi["extras"]["task_progress"]
                for name, result in (("baseline", baseline), ("da3", da3)):
                    row.update({f"{name}_{key}": value for key, value in result.items()
                                if key not in {"memory_files", "initial"}})
                episodes.append(row)
    data = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "benchmark": "RoboCasa composite", "environment_split": "target",
            "protocol_id": manifest["protocol_id"], "planner": PLANNER,
            "runtime": RUNTIME, "seeds": list(SEEDS), "tasks_per_split": 16,
            "memory_profile": "local", "memory_version": "GPT_6_astra_high",
            "vla": "RLDX-1-FT-RC365", "depth_model": "depth-anything/DA3METRIC-LARGE",
            "replaced_geometry_tools": ["back_project_batch", "query_world_map"],
            "camera_intrinsics": "Known simulator calibration",
            "camera_pose": "Known simulator camera-to-world transform",
            "other_simulator_information": "Retained, including task progress and success",
            "success_source": "state.success", "states_crosschecked": 320,
            "manifest_sha256": file_sha256(args.manifest),
            "comparison": "One run per setting, paired by task and seed",
        },
        "sources": sources,
        "initial_state_audit": {
            "robot_state_threshold": 1e-6,
            "robot_state_differences": sum(e["initial_robot_state_max_abs_diff"] > 1e-6 for e in episodes),
            "task_language_differences": sum(not e["initial_task_language_equal"] for e in episodes),
            "task_progress_differences": sum(not e["initial_task_progress_equal"] for e in episodes),
        },
        "summary": {split: summarize([e for e in episodes if e["split"] == split])
                    for split in SPLITS},
        "tasks": tasks,
        "episodes": episodes,
    }
    data["summary"]["all"] = summarize(episodes)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    with (args.output / "episodes.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(episodes)
    (args.output / "report.md").write_text(report_text(data), encoding="utf-8")
    print(json.dumps(data["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
