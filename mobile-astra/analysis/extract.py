"""Build a sanitized, trace-based report from two canonical RPent run folders.

Usage: python extract.py --repo /path/to/HarnessVLA-RPent --output ./analysis
Reads manifest cells only; archived infrastructure/interrupted attempts are excluded.
"""

import argparse
import csv
import hashlib
import json
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

VLA = {"rldx_arm", "rldx_skill"}
MANUAL = {"move_to", "move_delta", "move_base", "navigate_to", "rotate_pitch",
          "set_gripper", "release", "scripted_grasp"}
LABELS = {"vla": "VLA 直接完成", "setup": "Planner 准备后 VLA 完成",
          "repair": "Planner 介入后成功", "failure": "未成功"}
MODELS = [("astra", "GPT-6-Astra", "composite_main_astra_rerun_20261101T150450Z"),
          ("sol", "GPT-5.6-Sol", "composite_main_gpt56_sol")]
RESULT_KEYS = {"ok", "status", "chunks", "steps_applied", "grasped", "grasp_detected",
               "grasp_contact", "held_apart", "grasp_obj", "gripper_qpos", "peak_lift",
               "base_clip", "base_drift", "effective_prompt", "effective_max_chunks",
               "effective_n_action_steps", "effective_settle_patience", "prompt_overridden",
               "steps", "distance", "error", "reached", "success"}


def read(path):
    return json.loads(path.read_text())


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def median(values):
    return round(statistics.median(values), 1) if values else None


def clean(text):
    # Final agent summaries occasionally mention a local audit file.
    return re.sub(r"/(?:mnt|home|tmp)/[^\s\"'`]+", "[local artifact]", text or "")


def episode(root, model, split, task, seed, out):
    folder = root / f"composite_{split}" / f"{task}_s{seed}"
    result_path = folder / "result.json"
    states_path = folder / "states.json"
    transcript_path = folder / f"transcript_{task}_target_s{seed}.json"
    result, state_log, transcript = map(read, (result_path, states_path, transcript_path))
    assert result["valid"] and result["task_name"] == task and result["seed"] == seed
    assert result["evaluation_split"] == f"composite_{split}"
    states = state_log["steps"]
    success_states = [s for s in states if s.get("extras", {}).get("success") is True]
    assert bool(success_states) == result["success"], (model, task, seed, "success mismatch")
    first_success = success_states[0]["step_idx"] if success_states else None
    assert first_success != 0, "Initial-state success needs a separate category"
    actions = [s for s in states if s.get("command")]
    attribution = [s for s in actions if first_success is None or s["step_idx"] <= first_success]
    assert all(s["command"]["action"] in VLA | MANUAL for s in actions)
    vla = [s for s in attribution if s["command"]["action"] in VLA]
    manual = [s for s in attribution if s["command"]["action"] in MANUAL]
    assert vla, "A manual-only run needs a separate category"
    post_vla = [s for s in manual if s["step_idx"] > vla[0]["step_idx"]]
    path = "repair" if post_vla else "setup" if manual else "vla"
    category = path if result["success"] else "failure"
    finish = transcript.get("finish") or {}
    stats = transcript["stats"]
    if result["success"]:
        stop = "success"
    elif finish.get("status") == "stuck":
        stop = "stuck"
    elif not finish and stats["turns_used"] >= result["planner"]["max_turns"]:
        stop = "turn_limit"
    else:
        raise AssertionError((folder, "Unclassified failure", finish, transcript.get("error")))
    tool_text = "\n".join(x.get("content", "") for x in transcript.get("messages", []))
    tool_counts = Counter(re.findall(r"\[tool<-\] ([a-z_]+):", tool_text))
    last = attribution[-1]
    item = {
        "id": f"{model}--{task}--{seed}", "model": model, "split": split, "task": task,
        "seed": seed, "success": result["success"], "valid": result["valid"],
        "category": category, "path": path, "elapsed_s": result["elapsed_s"],
        "vla_calls": len(vla), "manual_calls": len(manual),
        "vla_methods": dict(Counter(s["command"]["action"] for s in vla)),
        "manual_methods": dict(Counter(s["command"]["action"] for s in manual)),
        "total_actions": len(actions), "tool_calls": stats["tool_calls"],
        "turns": stats["turns_used"], "first_success_step": first_success,
        "first_intervention_step": post_vla[0]["step_idx"] if post_vla else None,
        "initial_vla_calls": sum(s["step_idx"] < post_vla[0]["step_idx"] for s in vla)
                             if post_vla else len(vla),
        "last_method": last["command"]["action"],
        "completion_actor": "vla" if last["command"]["action"] in VLA else "manual",
        "stop": stop, "finish_status": finish.get("status"),
        "task_language": states[0].get("extras", {}).get("task_language", ""),
        "vla_sim_steps": sum(s.get("result", {}).get("steps_applied", 0) for s in vla),
    }
    trace = []
    previous = states[0].get("extras", {}).get("task_progress", {})
    for s in actions:
        progress = s.get("extras", {}).get("task_progress", {})
        changes = {k: {"before": previous.get(k), "after": v}
                   for k, v in progress.items() if k not in previous or previous[k] != v}
        trace.append({
            "step": s["step_idx"], "method": s["command"]["action"],
            "kind": "vla" if s["command"]["action"] in VLA else "manual",
            "args": {k: v for k, v in s["command"].items() if k != "action"},
            "elapsed_s": s.get("elapsed_s"),
            "result": {k: clean(v) if isinstance(v, str) else v
                       for k, v in s.get("result", {}).items() if k in RESULT_KEYS},
            "success": s.get("extras", {}).get("success", False),
            "progress": progress, "changes": changes,
        })
        previous = progress
    detail = {**item, "trace": trace, "initial_progress": states[0].get("extras", {}).get("task_progress", {}),
              "final_progress": states[-1].get("extras", {}).get("task_progress", {}),
              "finish_summary": clean(finish.get("summary")), "tool_counts": dict(tool_counts),
              "termination_reason": result["termination_reason"],
              "source": {"run": root.name, "cell": f"composite_{split}/{task}_s{seed}",
                         "files": {p.name: digest(p) for p in (result_path, states_path, transcript_path)}}}
    dump(out / "cases" / f"{item['id']}.json", detail)
    return item


def summarize(episodes):
    successes = [e for e in episodes if e["success"]]
    repairs = [e for e in successes if e["category"] == "repair"]
    return {
        "total": len(episodes), "success": len(successes),
        "by_split": {s: {"total": sum(e["split"] == s for e in episodes),
                         "success": sum(e["split"] == s for e in successes),
                         "categories": dict(Counter(e["category"] for e in successes if e["split"] == s))}
                     for s in ("seen", "unseen")},
        "categories": dict(Counter(e["category"] for e in episodes)),
        "repair_final": dict(Counter(e["completion_actor"] for e in repairs)),
        "repair_attempted": sum(e["path"] == "repair" for e in episodes),
        "stops": dict(Counter(e["stop"] for e in episodes if not e["success"])),
        "first_call_success": sum(e["success"] and e["total_actions"] == 1 and e["category"] == "vla" for e in episodes),
        "median_success_s": median([e["elapsed_s"] for e in successes]),
        "median_by_category": {c: median([e["elapsed_s"] for e in successes if e["category"] == c])
                               for c in ("vla", "setup", "repair")},
        "manual_success_methods": dict(Counter(m for e in repairs for m, n in e["manual_methods"].items() for _ in range(n))),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--astra-run", default=MODELS[0][2])
    args = parser.parse_args()
    out = args.output
    (out / "cases").mkdir(parents=True, exist_ok=True)
    manifest = read(args.repo / "robots/robocasa/eval/target50.json")
    data = {"schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
            "tasks": {s: manifest["splits"][f"composite_{s}"]["tasks"] for s in ("seen", "unseen")},
            "models": {}, "episodes": [], "labels": LABELS}
    for model, name, run in MODELS:
        if model == "astra":
            run = args.astra_run
        root = args.repo / "runs" / run
        info = read(root / "run-info.json")
        items = [episode(root, model, split, task, seed, out)
                 for split in ("seen", "unseen") for task in data["tasks"][split] for seed in range(1, 6)]
        data["episodes"].extend(items)
        data["models"][model] = {"name": name, "model": info["model"], "effort": info["reasoning_effort"],
                                 "memory": info["memory_version"], "memory_revision": info["memory_revision"],
                                 "repository_revision": info["repository_revision"],
                                 "run": run, "summary": summarize(items)}
    assert len(data["episodes"]) == 320
    assert len({e["id"] for e in data["episodes"]}) == 320
    astra = [e for e in data["episodes"] if e["model"] == "astra"]
    sol = [e for e in data["episodes"] if e["model"] == "sol"]
    paired = Counter()
    for a, b in zip(astra, sol):
        assert (a["task"], a["seed"]) == (b["task"], b["seed"])
        key = "both" if a["success"] and b["success"] else "astra_only" if a["success"] else "sol_only" if b["success"] else "neither"
        paired[key] += 1
        a["paired"] = b["paired"] = key
    data["paired"] = dict(paired)
    dump(out / "data.json", data)
    fields = ["model", "split", "task", "seed", "success", "category", "path", "paired", "vla_calls",
              "manual_calls", "first_intervention_step", "first_success_step", "last_method",
              "completion_actor", "tool_calls", "turns", "elapsed_s", "stop"]
    with (out / "episodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(data["episodes"])
    lines = ["# RoboCasa composite：Astra 与 5.6-Sol", "", "320 个有效 episode；32 个任务 × seeds 1–5 × 2 模型。", "",
             f"Astra 批次：`{args.astra_run}`；Sol 批次：`{MODELS[1][2]}`。", ""]
    for split in ("seen", "unseen"):
        lines += [f"## {split.title()}", "", "| 模型 | 成功数 / 80 | 成功率 | VLA 直接 | 准备后 VLA | Planner 介入后 |", "|---|---:|---:|---:|---:|---:|"]
        for m in data["models"].values():
            s = m["summary"]["by_split"][split]; c = s["categories"]
            lines.append(f'| {m["name"]} | {s["success"]}/80 | {s["success"]/80*100:.2f}% | {c.get("vla",0)} | {c.get("setup",0)} | {c.get("repair",0)} |')
        lines.append("")
    a = data["models"]["astra"]["summary"]
    b = data["models"]["sol"]["summary"]
    lines += ["", "分类按 states.json 的实际动作顺序，截止首次 success=true。VLA 包括 rldx_arm/rldx_skill，连续续跑仍属于 VLA 直接完成。只读感知和记忆调用不算控制介入。",
              "准备类：非 VLA 动作只出现在首次 VLA 前。修复/介入类：首次 VLA 之后有非 VLA 动作，最后任务成功；并非因果消融结论。两批无纯解析动作成功案例，也无单次 VLA 调用直接成功案例。",
              f"Astra 的 {a['categories']['repair']} 个介入成功中，{a['repair_final']['vla']} 个最后由 VLA 完成，{a['repair_final']['manual']} 个最后由解析动作完成；Sol 的 {b['categories']['repair']} 个分别为 {b['repair_final']['vla']} 和 {b['repair_final']['manual']}。",
              f"Astra 共有 {a['repair_attempted']} 个 episode 出现 VLA 后介入，{a['categories']['repair']} 个成功；Sol {b['repair_attempted']} 个中 {b['categories']['repair']} 个成功。这是实际介入病例的观察比例，不是随机化修复实验。",
              f"失败停止方式：Astra finish=stuck {a['stops']['stuck']} 个，无 finish 且到达 100 responses 上限 {a['stops']['turn_limit']} 个；Sol 分别 {b['stops']['stuck']}、{b['stops']['turn_limit']}。completed 仅表示运行结束，不表示任务成功。",
              f"配对：双方成功 {paired['both']}、仅 Astra 成功 {paired['astra_only']}、仅 Sol 成功 {paired['sol_only']}、双方失败 {paired['neither']}。按 task 与 seed 对齐不保证初始场景完全一致。", "",
              "配置：官方 RLinf/RPent a744bd5；xhigh；最多 100 个模型响应（并非 100 个工具调用），3600s/episode；RLDX-1-FT-RC365，每次最多 40 chunks × 8 steps=320 仿真步。",
              "Astra 记忆 GPT_6_astra_high，Sol 记忆 GPT_5.5_xhigh；不是单一模型变量的公平消融。种子0任务记忆可用，感知、地图与解析控制可用。",
              "报告采用 target50 manifest 中的 320 个 canonical result.json；排除归档和中断的尝试。成功来自环境 state.success，与 320 份 states.json 交叉核对。逐例 JSON 附源文件 SHA-256。", ""]
    for model, _, _ in MODELS:
        lines += [f'## {data["models"][model]["name"]} 成功案例', "", "| 任务 | seed | 类别 | VLA / 解析动作 | 首次成功动作 |", "|---|---|---|---|---|"]
        for e in data["episodes"]:
            if e["model"] == model and e["success"]:
                lines.append(f'| {e["task"]} | {e["seed"]} | {LABELS[e["category"]]} | {e["vla_calls"]} / {e["manual_calls"]} | #{e["first_success_step"]} {e["last_method"]} |')
        lines.append("")
    (out / "report.md").write_text("\n".join(lines))
    print(json.dumps({m: x["summary"] for m, x in data["models"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
