"""Build the public NoGeomTools comparison from two completed canonical runs.

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
REMOVED = ("back_project_batch", "query_world_map")
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
CSV_FIELDS = (
    "split", "task", "seed", "baseline_success", "nogeom_success",
    "baseline_elapsed_s", "nogeom_elapsed_s", "baseline_termination_reason",
    "nogeom_termination_reason", "baseline_final_native_success",
    "nogeom_final_native_success", "baseline_final_terminated",
    "nogeom_final_terminated", "baseline_result_sha256", "nogeom_result_sha256",
    "baseline_states_sha256", "nogeom_states_sha256",
    "initial_robot_state_max_abs_diff", "initial_robot_state_exact_equal",
    "initial_task_language_equal",
    "baseline_action_records", "baseline_vla_action_records", "baseline_other_action_records",
    "nogeom_action_records", "nogeom_vla_action_records", "nogeom_other_action_records",
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


def source_scope(source_repo):
    """Check the registered-tool filter without importing the simulator."""
    source = (source_repo / "robots/robocasa/toolkit.py").read_text()
    tree = ast.parse(source)
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                  and n.name == "_register_robocasa_tools")
    matched = False
    for node in ast.walk(method):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            comp = node.test
            if (isinstance(comp.left, ast.Attribute) and comp.left.attr == "name"
                    and len(comp.ops) == 1 and isinstance(comp.ops[0], ast.In)
                    and isinstance(comp.comparators[0], ast.Set)
                    and ast.literal_eval(comp.comparators[0]) == set(REMOVED)
                    and any(isinstance(n, ast.Continue) for n in node.body)):
                matched = True
    require(matched, "Missing geometry-tool registration filter")
    prompt = (source_repo / "robots/robocasa/prompts/evaluate.py").read_text()
    require(not any(name in prompt for name in REMOVED),
            "Evaluation prompt still advertises removed geometry tools")
    return True





def read_episode(root, split, task, seed, protocol_id):
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
        audit["observations_with_nonempty_progress"] += bool(progress)
        if action in VLA_ACTIONS:
            audit["vla_action_records"] += 1
            audit["vla_records_with_grasp_contact"] += "grasp_contact" in output
            audit["vla_records_with_grasp_obj"] += "grasp_obj" in output
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


def compare_initial(baseline, nogeom):
    a, b = baseline["initial"], nogeom["initial"]
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
    nogeom = read_json(args.nogeom_run / "run_manifest.json")
    launch_path = args.nogeom_run / "preflight/queue_config.json"
    launch = read_json(launch_path)
    require(baseline["repository_revision"] == nogeom["git_head"] == launch["git_head"]
            == BASE_REVISION, "Unexpected official experiment base")
    require(nogeom["status"] == "finished" and nogeom["valid"] == 160,
            "NoGeomTools suite is not finished")
    for info in (baseline, nogeom):
        require(info["model"] == PLANNER["model"]
                and info["reasoning_effort"] == PLANNER["reasoning_effort"],
                "Planner source metadata differs")
    require(baseline["memory_version"] == Path(launch["memory_dir"]).name
            == "GPT_6_astra_high", "Memory versions differ")
    require(set(nogeom["removed_tools"]) == set(REMOVED), "Removed tools differ")
    source_hashes = {}
    for name, expected in launch["source_sha256"].items():
        if name.startswith(("robots/", "rpent/")):
            actual = file_sha256(args.source_repo / safe_relative(name))
            require(actual == expected, f"Source differs from launch snapshot: {name}")
            source_hashes[name] = actual
    require(len(source_hashes) == 12, "Incomplete runtime source snapshot")
    source_scope(args.source_repo)
    sources = {}
    for name, root, metadata in (("baseline", args.baseline_run, "run-info.json"),
                                 ("nogeom", args.nogeom_run, "run_manifest.json")):
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]+", root.name)), "Invalid public run name")
        sources[name] = {"run": root.name, "revision": BASE_REVISION,
                         "metadata_file": metadata,
                         "metadata_sha256": file_sha256(root / metadata)}
    sources["nogeom"].update({
        "revision_scope": "Official base with local active geometry-tool removal",
        "source_files_sha256": source_hashes,
        "launch_snapshot_sha256": file_sha256(launch_path),
        "finished_at": nogeom["finished_at"],
        "started_at": nogeom["started_at"],
        "scheduler": "Started with six GPU workers; resumed remaining 16 episodes on an eight-GPU shared queue after 144 valid results were preserved",
    })
    return sources, launch



def audit_memory(args, nogeom_manifest, selected_files, pairs):
    baseline_path = args.baseline_run / "memory_sha256.json"
    baseline = read_json(baseline_path)
    launch = nogeom_manifest["memory_sha256"]
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
        "hash_reference": "Baseline memory_sha256.json and NoGeomTools preflight/queue_config.json",
        "baseline_hash_manifest_sha256": file_sha256(baseline_path),
        "selected_file_sha256": hashes,
        "scope": "Launch corpus and selected files; actual reading order is not constrained to match",
    }


def summarize(episodes):
    result = {
        "total": len(episodes),
        "baseline_success": sum(e["baseline_success"] for e in episodes),
        "nogeom_success": sum(e["nogeom_success"] for e in episodes),
        "both_success": sum(e["baseline_success"] and e["nogeom_success"] for e in episodes),
        "baseline_only": sum(e["baseline_success"] and not e["nogeom_success"] for e in episodes),
        "nogeom_only": sum(not e["baseline_success"] and e["nogeom_success"] for e in episodes),
        "neither": sum(not e["baseline_success"] and not e["nogeom_success"] for e in episodes),
    }
    return result


def percentage(numerator, denominator, signed=False):
    value = (Decimal(numerator) * 100 / Decimal(denominator)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{value:+.2f}" if signed else f"{value:.2f}"


def report_text(data):
    lines = ["# RoboCasa composite：移除主动几何查询", "",
             "官方 RPent · GPT-6-Astra / xhigh · RLDX-1-FT-RC365。"
             "32 个任务 × seeds 1–5；两组各 160 个有效 episode。", "",
             "| 任务组 | Baseline | NoGeomTools | 成功率差 |", "|---|---:|---:|---:|"]
    for split, label in (("seen", "Seen"), ("unseen", "Unseen"), ("all", "总计")):
        s = data["summary"][split]
        n, b, c = s["total"], s["baseline_success"], s["nogeom_success"]
        lines.append(f"| {label} | {b}/{n} · {percentage(b,n)}% | "
                     f"{c}/{n} · {percentage(c,n)}% | {percentage(c-b,n,True)} pp |")
    lines += ["", "| 配对结果 | Seen | Unseen | 总计 |", "|---|---:|---:|---:|"]
    for key, label in (("both_success", "双方成功"), ("baseline_only", "仅 baseline 成功"),
                       ("nogeom_only", "仅 NoGeomTools 成功"), ("neither", "双方失败")):
        lines.append("| " + label + " | " + " | ".join(
            str(data["summary"][s][key]) for s in ("seen", "unseen", "all")) + " |")
    a, m, f = data["initial_state_audit"], data["memory_audit"], data["feedback_audit"]
    g = data["geometry_access_audit"]
    lines += ["", "## 实验范围", "",
        "移除 Planner 工具注册表中的 `back_project_batch` 与 `query_world_map`，"
        "并删除评测 prompt 对这两个工具的说明、示例与调用要求；同步调整观测工具说明。", "",
        "这两个工具原本分别返回指定像素对应的世界坐标，以及按高度／区域查询的世界坐标聚类。"
        "本实验不删除模拟器内部深度或世界坐标图，也不接入 DA3。", "",
        "原版 `task_progress`（可能包含距离）、success、接触反馈、本体状态、相机标定、"
        "评分规则访问、历史记忆、VLA 输入／权重和动作控制均保留。"
        "move_to、scripted_grasp、navigate_to、move_delta 仍可接收 Agent 提供的位置或位移。"
        "这是一项主动几何查询工具的消融，不是完全无几何真值或文件／RPC 隔离。", "",
        "## 数据核验", "",
        "两组 320 个 canonical 结果均有效，末条观测的原生 success 与结果逐局一致；"
        "NoGeomTools 160 局均正常结束，任务失败也保留在分母中。归档和中断重试不重复统计。", "",
        f"检查 NoGeomTools 的 {f['observations']} 条保存观测；"
        f"其中 {f['observations_with_nonempty_progress']} 条仍有非空任务进度。"
        f"{f['vla_records_with_grasp_contact']} 条 VLA 动作结果仍含 grasp_contact，符合保留接触反馈的设置。", "",
        f"检查 {g['streams_checked']} 局的流式记录，共 {g['recorded_mcp_calls']} 个去重 MCP 调用；"
        f"两个移除工具的调用数为 {g['removed_tool_calls']}。"
        f"另检查 {g['native_command_items']} 个原生命令记录；读取几何文件或通过原生命令访问几何的"
        f"模式命中共 {g['geometry_artifact_read_attempts'] + g['native_geometry_access_attempts'] + g['geometry_image_access_attempts']} 次。"
        "检查范围限于已记录工具名、文件参数和命令文本；不能覆盖间接路径、外部脚本、历史记忆或未记录执行。", "",
        f"两组 {m['matching_launch_sha256_files']} 个启动记忆文件的 SHA-256 相同；"
        f"160 对结果选择的记忆文件一致，涉及 {m['unique_selected_files']} 个唯一文件，当前哈希也一致。"
        "读取顺序不要求相同。", "",
        f"初始机器人状态最大绝对差 >1e-6 的有 {a['robot_state_differences']} 对，"
        f"逐值不完全相同的有 {a['exact_robot_state_differences']} 对；"
        f"任务文本不同的有 {a['task_language_differences']} 对。未检查全部场景物体。", "",
        "每个任务仅 5 个 seed，每种设置只运行一轮。VLA 动作采样未随场景 seed 固定，"
        "同任务同 seed 的结果变化不能直接解释为移除工具的稳定因果效应。", "",
        "## 代表轨迹的动作数量", "",
        "下表是 states.json 动作记录，不包括读图、读文件等只读调用；不据此判断失败原因。", "",
        "| 任务 / seed | Baseline | NoGeomTools | Baseline 动作 | NoGeomTools 动作 |", "|---|---|---|---|---|"]
    for c in data["cases"]:
        b, n = c["baseline"], c["nogeom"]
        lines.append(f"| {c['task']} s{c['seed']} | {'成功' if b['success'] else '失败'} | "
                     f"{'成功' if n['success'] else '失败'} | {b['vla_action_records']} VLA + "
                     f"{b['other_action_records']} 其他 | {n['vla_action_records']} VLA + {n['other_action_records']} 其他 |")
    lines += ["", "## 逐任务与 seed", "", "每个 seed 为 Baseline/NoGeomTools；1 为原生成功，0 为失败。", "",
              "| 分组 | 任务 | Baseline | NoGeomTools | s1 | s2 | s3 | s4 | s5 |",
              "|---|---|---:|---:|---|---|---|---|---|"]
    for split in SPLITS:
        for task in data["tasks"][split]:
            rows = [e for e in data["episodes"] if e["split"] == split and e["task"] == task]
            cells = [f"{int(e['baseline_success'])}/{int(e['nogeom_success'])}" for e in rows]
            lines.append(f"| {split.title()} | {task} | {sum(e['baseline_success'] for e in rows)}/5 | "
                         f"{sum(e['nogeom_success'] for e in rows)}/5 | " + " | ".join(cells) + " |")
    lines += ["", "## 数据来源与重建", ""]
    for label in ("baseline", "nogeom"):
        source = data["sources"][label]
        lines.append(f"{label}：`{source['run']}`；官方基线 `{source['revision']}`。")
    lines += ["", "JSON / CSV 保存逐局 result.json 与 states.json 的 SHA-256；JSON 另含启动元数据、"
              "实际源文件、任务清单、记忆和本脚本的 SHA-256。原始运行文件不随网页发布。", "",
              "```sh", "python extract.py --baseline-run BASELINE_RUN --nogeom-run NOGEOM_RUN "
              "--manifest TARGET50_JSON --source-repo NOGEOM_SOURCE "
              "--memory-dir MEMORY_DIR --output OUTPUT_DIR", "```", ""]
    return "\n".join(lines)



def stream_audit(root, tasks):
    """Inspect recorded tool names and native command text; not a sandbox proof."""
    geometry_artifact = re.compile(r"(?:[^\s'\"/]*_(?:world|depth)[^\s'\"/]*\.npz|navview_floor(?:\.[a-z0-9*]+)?)", re.I)
    geometry_call = re.compile(r"\b(?:back_project_batch|query_world_map|world_map)\s*\(")
    sim_import = re.compile(r"\b(?:from|import)\s+(?:robocasa|robosuite|mujoco|robots\.robocasa)\b")
    sim_position = re.compile(r"\b(?:body_xpos|geom_xpos|site_xpos|get_body_xpos|get_site_xpos|get_geom_xpos|obj_pos|object_pos)\b|\bsim\.data\b")
    counts, tools, kinds = Counter(), Counter(), Counter()
    flagged, hashes = [], {}
    for split in SPLITS:
        for task in tasks[split]:
            for seed in SEEDS:
                cell = root / f"composite_{split}" / f"{task}_s{seed}"
                streams = sorted(cell.glob("*.stream.jsonl"))
                require(len(streams) == 1, f"Expected one canonical stream: {cell.name}")
                stream = streams[0]
                hashes[f"{split}/{task}_s{seed}"] = file_sha256(stream)
                items = {}
                with stream.open() as handle:
                    for line_number, line in enumerate(handle, 1):
                        event = json.loads(line)
                        method = event.get("method", event.get("type", ""))
                        if method not in {"item/started", "item/completed", "item.started", "item.completed"}:
                            continue
                        payload = event.get("payload", event)
                        item = payload.get("item", {})
                        kind = item.get("type", "")
                        if kind in {"agentMessage", "reasoning", "userMessage"}:
                            continue
                        # Exclude output blocks so images and model messages are never exported.
                        fields = {k: item.get(k) for k in ("type", "tool", "name", "arguments", "command", "path", "image_path", "file_path", "status")}
                        fields["completed"] = method in {"item/completed", "item.completed"}
                        items[str(item.get("id", f"line-{line_number}"))] = fields
                counts["streams_checked"] += 1
                for item in items.values():
                    kind = item["type"]
                    kinds[kind] += 1
                    reasons = []
                    if kind in {"mcpToolCall", "mcp_tool_call"}:
                        name = str(item["tool"] or item["name"] or "").split("__")[-1].split("/")[-1]
                        require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+", name)), "Unexpected tool name")
                        tools[name] += 1
                        counts["recorded_mcp_calls"] += 1
                        if name in REMOVED:
                            counts["removed_tool_calls"] += 1
                            reasons.append("removed geometry tool called")
                        text = json.dumps(item["arguments"], ensure_ascii=False)
                        if name in {"read_text_file", "read_image", "view_image", "open_image"} and geometry_artifact.search(text):
                            counts["geometry_artifact_read_attempts"] += 1
                            reasons.append("read tool references a geometry artifact")
                        if name in {"exec", "exec_command", "python", "run_code"} and (geometry_artifact.search(text) or geometry_call.search(text) or (sim_import.search(text) and sim_position.search(text))):
                            counts["native_geometry_access_attempts"] += 1
                            reasons.append("code tool references geometry artifact or simulator positions")
                    elif kind in {"commandExecution", "command_execution"}:
                        counts["native_command_items"] += 1
                        command = item["command"] or ""
                        text = command if isinstance(command, str) else json.dumps(command)
                        if geometry_artifact.search(text) or geometry_call.search(text) or (sim_import.search(text) and sim_position.search(text)):
                            counts["native_geometry_access_attempts"] += 1
                            reasons.append("native command references geometry artifact or simulator positions")
                    elif kind in {"imageView", "image_view"}:
                        if any(geometry_artifact.search(str(item[k] or "")) for k in ("path", "image_path", "file_path")):
                            counts["geometry_image_access_attempts"] += 1
                            reasons.append("native image read references geometry artifact")
                    if reasons:
                        flagged.append({"split": split, "task": task, "seed": seed, "reasons": reasons})
    return {**{key: counts[key] for key in ("streams_checked", "recorded_mcp_calls", "removed_tool_calls", "geometry_artifact_read_attempts", "native_command_items", "native_geometry_access_attempts", "geometry_image_access_attempts")},
            "recorded_tool_counts": dict(sorted(tools.items())), "item_types": dict(sorted(kinds.items())),
            "flagged_calls": flagged, "stream_sha256": hashes,
            "scope": "Recorded MCP tool names, geometry filenames in read arguments, and geometry references in native command text; indirect paths, external scripts, historical memory and unlogged execution are not covered"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline-run", "nogeom-run", "manifest", "source-repo", "memory-dir", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    manifest = read_json(args.manifest)
    tasks = task_matrix(manifest)
    sources, launch = public_sources(args)
    for root in (args.baseline_run, args.nogeom_run):
        check_cells(root, tasks)
    episodes, cases, selected_files, feedback = [], [], set(), Counter()
    for split in SPLITS:
        for task in tasks[split]:
            for seed in SEEDS:
                baseline = read_episode(args.baseline_run, split, task, seed, manifest["protocol_id"])
                nogeom = read_episode(args.nogeom_run, split, task, seed, manifest["protocol_id"])
                require(baseline["memory_files"] == nogeom["memory_files"],
                        f"{split}/{task}_s{seed}: selected memory files differ")
                selected_files.update(nogeom["memory_files"])
                row = {"split": split, "task": task, "seed": seed, **compare_initial(baseline, nogeom)}
                for label, value in (("baseline", baseline), ("nogeom", nogeom)):
                    for key in ("success", "elapsed_s", "termination_reason", "final_native_success",
                                "final_terminated", "result_sha256", "states_sha256"):
                        row[f"{label}_{key}"] = value[key]
                episodes.append(row)
                feedback.update(nogeom["feedback_audit"])
                cases.append({"split": split, "task": task, "seed": seed,
                              "baseline": baseline["case"], "nogeom": nogeom["case"]})
                for label, value in (("baseline", baseline), ("nogeom", nogeom)):
                    for key in ("action_records", "vla_action_records", "other_action_records"):
                        row[f"{label}_{key}"] = value["case"][key]
    selected = []
    for split, task, gain in (("seen", "RinseSinkBasin", False),
                              ("seen", "StoreLeftoversInBowl", True),
                              ("unseen", "GarnishPancake", True),
                              ("unseen", "WashFruitColander", False)):
        candidates = [c for c in cases if c["split"] == split and c["task"] == task
                      and c["baseline"]["success"] != c["nogeom"]["success"]
                      and c["nogeom"]["success"] == gain]
        require(candidates, f"Missing representative outcome: {task}")
        selected.append(candidates[0])
    cases = selected
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
            "da3": False, "notaskgt": False, "nocontactgt": False,
            "removed_tools": list(REMOVED),
            "retained_skill_feedback": ["grasp_contact", "grasp_obj", "grasped", "grasp_detected", "held_apart", "gripper_qpos", "peak_lift", "status"],
            "task_progress": "Baseline task_progress including distances retained",
            "read_text_file": "Baseline permissions; static scoring rules and historical memory retained",
            "prompt_changes": "Removed instructions and examples for the two unavailable geometry tools; updated view_env_state method description", "success": "Retained", "robocasa_terminated": "Retained",
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
        "geometry_access_audit": stream_audit(args.nogeom_run, tasks),
        "feedback_audit": {
            **feedback, "episodes_checked": len(episodes), "contact_feedback_retained": True,
            "scope": "Saved action results and task_progress counts; not a guarantee that all geometry sources are inaccessible",
        },
        "validation": {
            "canonical_results_checked": 320, "all_results_valid": True,
            "final_native_success_matches": 320, "any_recorded_success_matches": 320,
            "archived_attempts_included": False, "source_snapshot_matches": True,
            "extractor_sha256": file_sha256(Path(__file__)),
            "termination_reasons": {label: dict(Counter(e[f"{label}_termination_reason"]
                                                        for e in episodes))
                                    for label in ("baseline", "nogeom")},
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
                      "feedback_audit": data["feedback_audit"],
                      "geometry_access_audit": {k:v for k,v in data["geometry_access_audit"].items() if k != "stream_sha256"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
