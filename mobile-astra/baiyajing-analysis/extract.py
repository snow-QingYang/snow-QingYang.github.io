"""Extract the canonical 160-cell Baiyajing run into a sanitized static report.

python extract.py --run RUN_DIR --repo HarnessVLA-Baiyajing --output REPORT_DIR
Reads records only; does not launch or alter experiments.
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

OPS = {"vla", "pick", "carry", "put_down", "release", "goto", "retract"}
POLICY_OPS = {"vla", "pick"}
LABELS = {"initial": "初始整任务 VLA 成功", "planned": "Planner 修复 · vla/pick 程序",
          "mixed": "Planner 修复 · 含显式控制", "failure": "未成功"}


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k not in {"reasoning", "prompt_text"}}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"/(?:home|mnt|tmp)/[^\s\"'`\\]+", "[local artifact]", value)
    return value


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


def median(values):
    return round(statistics.median(values), 1) if values else None


def extract_cell(run, cell, out):
    task, seed, split = cell["task"], cell["seed"], cell["split"].replace("composite_", "")
    folder = run / f"{task}_s{seed}"
    result = read(folder / "result.json")
    events = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
    assert result["valid"] and result["task_name"] == task and result["seed"] == seed
    assert result["planner_model"] == "gpt-6-sol" and result["reasoning_effort"] == "medium"
    assert result["mode"] == "hybrid"
    trace, plans, alerts, queue = [], [], [], []
    pending = None
    initial_progress = events[0]["progress"]
    previous = initial_progress
    for event_number, event in enumerate(events, 1):
        kind = event["kind"]
        if kind in {"plan", "replan"}:
            plan = clean(event["plan"])
            plans.append({"index": len(plans)+1, "time": event["t"], "kind": kind,
                          "after_step": len(trace), "program": plan,
                          "trigger": clean(event.get("reason")), "event_number": event_number})
            queue = list(plan.get("steps") or [])
        elif kind == "step_start":
            assert pending is None
            command = clean(event["step"])
            index = len(trace) + 1
            if index == 1:
                origin = "initial"
                assert command["op"] == "vla" and command["prompt"] == result["lang"]
            elif queue:
                expected = queue.pop(0)
                assert command == expected, (folder, command, expected)
                origin = "planner"
            else:
                origin = "fallback"
            pending = {"index": index, "start": event["t"], "command": command,
                       "origin": origin, "plan_index": len(plans) if origin == "planner" else None,
                       "attempt_events": [], "event_start": event_number, "alerts": []}
        elif kind == "attempt":
            assert pending is not None
            assert clean(event["step"]) == pending["command"]
            pending["attempt_events"].append({"time": event["t"], "index": event["attempt"],
                                              "result": clean(event["result"])})
        elif kind in {"object_fell", "step_exception", "planner_error"}:
            alert = clean({k: v for k, v in event.items() if k != "trace"})
            if kind == "step_exception":
                alert["error"] = clean(event.get("trace", "").strip().splitlines()[-1])
            alert["event_number"] = event_number
            alert["step"] = pending["index"] if pending else len(trace)
            alerts.append(alert)
            if pending:
                pending["alerts"].append(alert)
            if kind == "object_fell":
                queue = []
        elif kind == "step_end":
            assert pending is not None
            summary = clean(event["summary"])
            assert summary["step"] == pending["command"]
            assert summary["step"]["op"] in OPS
            progress = summary["progress_after"]
            changes = {k: {"before": previous.get(k), "after": v} for k, v in progress.items()
                       if k not in previous or previous[k] != v}
            pending.update(end=event["t"], duration=round(event["t"]-pending["start"], 1),
                           summary=summary, changes=changes, event_end=event_number,
                           env_success_observed=any(a["result"]["status"] == "env_success"
                                                    for a in pending["attempt_events"]))
            trace.append(pending)
            previous, pending = progress, None
            if not summary["ok"]:
                queue = []
    assert pending is None
    assert len(trace) == result["steps_executed"] and len(plans) == result["llm_calls"]
    assert trace[-1]["summary"]["progress_after"] == result["final_progress"]
    attempt_events = [a for s in trace for a in s["attempt_events"]]
    assert sum(a["result"]["chunks"] for a in attempt_events) == result["vla_chunks"]
    assert (not plans) == trace[0]["summary"]["ok"]
    if not plans:
        assert result["success"] and len(trace) == 1 and trace[0]["env_success_observed"]
    if not result["success"]:
        assert not any(s["env_success_observed"] for s in trace)
    if result["termination_reason"] == "object_on_floor":
        assert plans[-1]["program"].get("unrecoverable") and any(a["kind"] == "object_fell" for a in alerts)
    methods = Counter(s["command"]["op"] for s in trace)
    explicit = sum(n for op, n in methods.items() if op not in POLICY_OPS)
    path = "initial" if not plans else "mixed" if explicit else "planned"
    category = path if result["success"] else "failure"
    item = {"id": f"{task}--{seed}", "task": task, "seed": seed, "split": split,
            "valid": True, "success": result["success"], "category": category, "path": path,
            "elapsed_s": result["elapsed_s"], "llm_calls": result["llm_calls"],
            "steps_executed": len(trace), "methods": dict(methods), "explicit_steps": explicit,
            "vla_program_steps": sum(methods[op] for op in POLICY_OPS),
            "actual_vla_attempts": sum(a["result"]["chunks"] > 0 for a in attempt_events),
            "attempt_events": len(attempt_events), "vla_chunks": result["vla_chunks"],
            "vla_env_steps": result["vla_env_steps"], "fallback_steps": sum(s["origin"] == "fallback" for s in trace),
            "initial_status": trace[0]["attempt_events"][-1]["result"]["status"],
            "initial_chunks": sum(a["result"]["chunks"] for a in trace[0]["attempt_events"]),
            "initial_max_chunks": trace[0]["command"]["max_chunks"],
            "last_op": trace[-1]["command"]["op"], "stop": result["termination_reason"],
            "fell_objects": sorted({obj for a in alerts if a["kind"] == "object_fell" for obj in a["fallen"]}),
            "task_language": result["lang"]}
    sources = [folder / "result.json", folder / "events.jsonl"]
    if (folder / "llm.jsonl").exists():
        llms = [json.loads(line) for line in (folder / "llm.jsonl").read_text().splitlines()]
        assert len(llms) == result["llm_calls"]
        sources.append(folder / "llm.jsonl")
    detail = {**item, "trace": trace, "plans": plans, "alerts": alerts,
              "initial_progress": initial_progress, "final_progress": result["final_progress"],
              "source": {"run": run.name, "cell": folder.name,
                         "files": {p.name: digest(p) for p in sources}}}
    dump(out / "cases" / f"{item['id']}.json", detail)
    return item


def aggregate(items):
    success = [e for e in items if e["success"]]
    return {"total": len(items), "success": len(success),
            "categories": dict(Counter(e["category"] for e in items)),
            "stops": dict(Counter(e["stop"] for e in items if not e["success"])),
            "repair_final": dict(Counter(e["last_op"] for e in success if e["category"] != "initial")),
            "initial_statuses": dict(Counter(e["initial_status"] for e in items)),
            "by_split": {s: {"total": sum(e["split"] == s for e in items),
                             "success": sum(e["split"] == s for e in success),
                             "categories": dict(Counter(e["category"] for e in items if e["split"] == s))}
                         for s in ("seen", "unseen")},
            "median_elapsed": {c: median([e["elapsed_s"] for e in items if e["category"] == c])
                               for c in LABELS},
            "methods": dict(Counter(op for e in items for op, n in e["methods"].items() for _ in range(n))),
            "total_steps": sum(e["steps_executed"] for e in items),
            "total_plans": sum(e["llm_calls"] for e in items),
            "actual_vla_attempts": sum(e["actual_vla_attempts"] for e in items),
            "fallback_steps": sum(e["fallback_steps"] for e in items)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    (out / "cases").mkdir(parents=True, exist_ok=True)
    config, benchmark, cells = read(args.run/"config.json"), read(args.repo/"configs/benchmark.json"), read(args.run/"cells.json")
    expected = {(task, seed, split) for split in ("composite_seen", "composite_unseen")
                for task in benchmark["splits"][split]["tasks"] for seed in range(1, 6)}
    assert len(cells) == 160 and {(c["task"], c["seed"], c["split"]) for c in cells} == expected
    items = [extract_cell(args.run, cell, out) for cell in cells]
    summary = aggregate(items)
    assert summary["categories"] == {"initial": 28, "failure": 99, "planned": 20, "mixed": 13}
    assert summary["success"] == 61 and summary["stops"] == {"budget": 57, "object_on_floor": 42}
    assert summary["by_split"]["seen"]["success"] == 39 and summary["by_split"]["unseen"]["success"] == 22
    data = {"schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
            "tasks": {s: benchmark["splits"][f"composite_{s}"]["tasks"] for s in ("seen", "unseen")},
            "labels": LABELS, "episodes": items, "summary": summary,
            "config": {"model": config["planner"]["model"], "effort": config["planner"]["reasoning_effort"],
                       "max_planner_calls": config["planner"]["max_llm_calls"], "budget_s": config["planner"]["budget_seconds"],
                       "mode": config["mode"], "implementation_commit": config["upstream"]["commit"],
                       "rpent_commit": config["rpent"]["commit"], "memory": "memory/seed0",
                       "memory_sha256": config["memory_sha256"], "gpus": len(config["gpus"]),
                       "parallel_per_gpu": config["parallel_per_gpu"], "run": args.run.name,
                       "source_files": {name: digest(args.run/name) for name in ["cells.json", "config.json"]}},
            "reference": {"seen": {"success": 39, "total": 80}, "unseen": {"success": 20, "total": 80},
                          "overall": {"success": 59, "total": 160},
                          "url": "https://github.com/Baiyajing/HarnessVLA/blob/0596036864f50a3616036fd13ae098c758ccd598/README.md#results"}}
    dump(out / "data.json", data)
    fields = ["task", "seed", "split", "success", "category", "path", "llm_calls", "steps_executed", "vla_program_steps",
              "explicit_steps", "actual_vla_attempts", "vla_chunks", "vla_env_steps", "initial_status", "initial_chunks",
              "initial_max_chunks", "last_op", "fallback_steps", "elapsed_s", "stop"]
    with (out / "episodes.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(items)
    lines = ["# Baiyajing HarnessVLA：160 次 composite 运行分析", "", "本地成功 61/160（38.1%）：Seen 39/80，Unseen 22/80。仓库 README 为 59/160（39+20），两者分开统计。", "",
             "| 成功路径 | Seen | Unseen | 总计 |", "|---|---:|---:|---:|"]
    for c in ("initial", "planned", "mixed"):
        lines.append(f'| {LABELS[c]} | {summary["by_split"]["seen"]["categories"][c]} | {summary["by_split"]["unseen"]["categories"][c]} | {summary["categories"][c]} |')
    lines += ["", "首次整任务 VLA 成功 28/160；剩下 132 个进入 Planner，33/132 成功。20 个成功程序只有 vla/pick；13 个还含显式导航/搬运/放置。",
              "pick 使用 VLA。vla/pick 内部有自动靠近目标、手臂复位、放下持物和撤离等行为，因此 20 个不能称为纯 VLA 直接成功。",
              "33 个修复成功最终程序步骤：vla 28、put_down 2、carry 2、release 1。vla 内部的撤离可能参与最后成功，不能直接把这 28 个称作纯神经策略收尾。",
              "失败终止标签：budget 57；object_on_floor 42（含地面或机器人本体上不可达的物体）。初次 VLA 的 budget 是该 attempt 的 chunk 预算，并非整局超时。",
              "7 个程序 op：vla / pick / carry / put_down / release / goto / retract。执行步骤、attempt、chunk 与 Planner 调用是不同计数单位。",
              "步骤 ok 表示子步骤检查，不等于完整任务 success；以 result.json 中的环境成功为准。程序中未执行的排队步骤不算已执行。",
              "配置：GPT-6-sol / medium；至多 32 次 Planner 调用，3600 秒预算；8 GPU、每卡 1 个 episode；seed-0 记忆；Baiyajing 0596036、RPent 72686b8。",
              "初始整任务 VLA 上限 min(600,max(250,int(1.5*horizon/8))) chunks；每 chunk 8 控制步。原子子任务通常至多 2 attempts × 80 chunks。",
              "与官方 RPent 报告的实现、Planner、记忆和 VLA 调度预算不同，不能当作只改变模型的消融。仓库说明执行器规则参考过同种子失败，不属于严格 held-out 评估。", "",
              "## 逐例分类", "", "| 任务 | seed | 组别 | 结果 / 路径 | Planner 调用 | 程序步 | 结束标签 |", "|---|---:|---|---|---:|---:|---|"]
    for e in items:
        lines.append(f'| {e["task"]} | {e["seed"]} | {e["split"]} | {LABELS[e["category"]]} | {e["llm_calls"]} | {e["steps_executed"]} | {e["stop"]} |')
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
