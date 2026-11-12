"""Export reviewed E08 outcomes without private paths, prompts or raw trajectories.

Usage: python extract.py --combined RUN --geometry RUN --baseline RUN --output DIR
Only local JSON is read. This does not run a simulator, model or network request.
The completed audit files under the combined run are required inputs.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


VLA = {"rldx_skill", "rldx_arm"}
MANUAL = {"move_to", "move_delta", "move_base", "navigate_to", "rotate_pitch",
          "set_gripper", "release", "scripted_grasp", "execute_action"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def episode(root, cell):
    directory = root / cell
    result = load(directory / "result.json")
    steps = load(directory / "states.json")["steps"]
    require(result["valid"] is True, f"Invalid episode: {cell}")
    require(result["success"] == steps[-1]["extras"]["success"], f"Score mismatch: {cell}")
    require(result["planner"]["model"] == "gpt-6-astra", f"Unexpected planner: {cell}")
    actions = [s for s in steps if (s.get("command") or {}).get("action") in VLA | MANUAL]
    counts = Counter(s["command"]["action"] for s in actions)
    first_success = next((s for s in steps if s["extras"].get("success")), None)
    terminal_action = (first_success.get("command") or {}).get("action") if first_success else None
    vla_count = sum(counts[k] for k in VLA)
    manual_count = sum(counts[k] for k in MANUAL)
    if not result["success"]:
        path = "unsuccessful"
    elif manual_count == 0:
        path = "vla_only"
    elif terminal_action in VLA:
        path = "manual_then_vla_finish"
    elif terminal_action in MANUAL:
        path = "manual_finish"
    else:
        raise ValueError(f"Unclassified success: {cell}")
    return {
        "success": result["success"], "valid": True,
        "elapsed_s": result.get("elapsed_s"),
        "termination_reason": result["termination_reason"],
        "final_native_success": steps[-1]["extras"]["success"],
        "final_terminated": steps[-1]["terminated"],
        "success_path": path, "vla_calls": vla_count, "manual_calls": manual_count,
        "action_counts": dict(sorted(counts.items())),
        "first_success_step": first_success["step_idx"] if first_success else None,
        "first_success_action": terminal_action,
        "result_sha256": sha(directory / "result.json"),
        "states_sha256": sha(directory / "states.json"),
    }


def paired(rows, reference):
    return {
        "both_success": sum(r["combined"]["success"] and r[reference]["success"] for r in rows),
        "combined_only": sum(r["combined"]["success"] and not r[reference]["success"] for r in rows),
        "reference_only": sum(not r["combined"]["success"] and r[reference]["success"] for r in rows),
        "both_failure": sum(not r["combined"]["success"] and not r[reference]["success"] for r in rows),
    }


def initial_row(row):
    return {
        "strict_equal": row["state_equal"] and row["task_language_equal"]
        and all(row["rgb_equal"].values()) and all(row["metadata_equal"].values()),
        "robot_state_exact_equal": row["state_equal"],
        "robot_state_max_abs_diff": max(row["state_max_abs_diff"].values()),
        "task_language_equal": row["task_language_equal"],
        "rgb_exact_equal": row["rgb_equal"],
        "camera_metadata_equal": row["metadata_equal"],
    }


def build(combined, geometry, baseline):
    roots = {"combined": combined, "geometry": geometry, "baseline": baseline}
    manifest = load(combined / "manifest.json")
    source = load(combined / "source_revision.json")
    audit = load(combined / "audit/completed_context_audit.json")
    initials = load(combined / "analysis_geometry_comparison/initial_conditions_audit.json")
    score_check = load(combined / "analysis_geometry_comparison/scoring_crosscheck.json")
    completion = load(combined / "completion_summary.json")
    initial_maps = {
        reference: {r["cell"]: r for r in initials["comparisons"][f"combined_vs_{reference}"]["rows"]}
        for reference in ("geometry", "baseline")
    }
    tasks = {split: manifest["splits"]["composite_" + split]["tasks"] for split in ("seen", "unseen")}
    rows = []
    for split, names in tasks.items():
        require(len(names) == 16, "Expected 16 tasks per split")
        for task in names:
            for seed in range(1, 6):
                cell = f"composite_{split}/{task}_s{seed}"
                row = {"split": split, "task": task, "seed": seed}
                for label, root in roots.items():
                    row[label] = episode(root, cell)
                row["initial_conditions"] = {ref: initial_row(m[cell]) for ref, m in initial_maps.items()}
                row["initial_sha256"] = {}
                for label in roots:
                    original = initials["initial_artifact_evidence"][label][cell]
                    row["initial_sha256"][label] = {
                        "robot_state": original["state_sha256"],
                        "task_language": hashlib.sha256(original["task_language"].encode()).hexdigest(),
                        "rgb": {cam: item["sha256"] for cam, item in original["rgb"].items()},
                        "camera_metadata": {cam: item["sha256"] for cam, item in original["camera_metadata"].items()},
                    }
                rows.append(row)
    require(len(rows) == 160, "Expected 160 episodes")
    summary = {}
    for split in ("seen", "unseen", "all"):
        selected = [r for r in rows if split == "all" or r["split"] == split]
        summary[split] = {
            "total": len(selected),
            "successes": {label: sum(r[label]["success"] for r in selected) for label in roots},
            "paired_geometry": paired(selected, "geometry"),
            "paired_baseline": paired(selected, "baseline"),
            "combined_success_paths": dict(Counter(r["combined"]["success_path"] for r in selected if r["combined"]["success"])),
        }
    require(summary["seen"]["successes"] == {"combined": 27, "geometry": 22, "baseline": 34}, "Seen totals changed")
    require(summary["unseen"]["successes"] == {"combined": 14, "geometry": 17, "baseline": 21}, "Unseen totals changed")
    require(summary["all"]["combined_success_paths"] == {"vla_only": 22, "manual_then_vla_finish": 13, "manual_finish": 6}, "Path totals changed")
    strict = [r for r in rows if r["initial_conditions"]["geometry"]["strict_equal"]]
    require(len(strict) == 132, "Strict initial subset changed")
    require(score_check["checked"] == 160 and not score_check["mismatches"], "Scoring cross-check failed")
    require(not audit["hidden_structured_fields"] and not audit["parse_errors"], "Context audit failed")
    files = ["manifest.json", "source_revision.json", "completion_summary.json", "validation.json",
             "audit/completed_context_audit.json", "analysis_geometry_comparison/initial_conditions_audit.json",
             "analysis_geometry_comparison/comparison.json", "analysis_geometry_comparison/scoring_crosscheck.json",
             "analysis_geometry_comparison/manual_success_explanation.json"]
    source_files = source["source_files"]
    require(all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in source_files), "Unsafe source path")
    return {
        "schema_version": "1.0", "experiment_id": "E08",
        "name": "组合信息移除（保留 success）",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "completed_local": completion["finish_local"],
        "runs": {label: root.name for label, root in roots.items()},
        "code": {"branch": "no_privileged_info_with_planner_pose", "commit": source["commit"], "base_commit": source["base_commit"],
                 "publication_status": "本地已记录，待发布"},
        "protocol": {"model": "gpt-6-astra", "reasoning_effort": "xhigh", "vla": "RLDX-1-FT-RC365",
                     "environment_split": "target", "seeds": [1, 2, 3, 4, 5], "planner_max_turns": 100,
                     "timeout_seconds": 3600, "vla_max_chunks": 40, "vla_actions_per_chunk": 8,
                     "settle_patience": 999, "success_source": "state.success", "native_success_early_stop": True},
        "tasks": tasks, "summary": summary, "episodes": rows,
        "context_audit": {
            "episodes": 160, "completed_tool_returns": audit["item_type_counts"]["mcpToolCall"],
            "forbidden_field_hits": len(audit["hidden_structured_fields"]),
            "geometry_tool_calls": len(audit["geometry_tool_calls"]),
            "file_read_calls": len(audit["file_calls"]), "native_shell_calls": len(audit["native_commands"]),
            "memory_contract_ok": audit["counts"]["memory_contract_ok"],
            "saved_state_check": audit["saved_state_check"], "scoring_mismatches": len(score_check["mismatches"]),
            "scope": "Recorded Agent context only; not operating-system isolation.",
        },
        "initial_comparison": {
            "strict_equal_count": len(strict),
            "strict_subset_successes": {label: sum(r[label]["success"] for r in strict) for label in ("combined", "geometry")},
            "strict_subset_paired": paired(strict, "geometry"),
            "robot_state_exact_equal": sum(r["initial_conditions"]["geometry"]["robot_state_exact_equal"] for r in rows),
            "robot_state_difference_over_1e_6": sum(r["initial_conditions"]["geometry"]["robot_state_max_abs_diff"] > 1e-6 for r in rows),
            "task_language_different": sum(not r["initial_conditions"]["geometry"]["task_language_equal"] for r in rows),
            "scope": "Post-hoc diagnostic subset; not the full benchmark or a causal estimate.",
        },
        "evidence_sha256": {name: sha(combined / name) for name in files},
        "source_files_sha256": source_files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for label in ("combined", "geometry", "baseline", "output"):
        parser.add_argument("--" + label, type=Path, required=True)
    args = parser.parse_args()
    data = build(args.combined, args.geometry, args.baseline)
    args.output.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    require(not any(token in text for token in ("/home/", "/mnt/", "sk-", "Bearer ")), "Private data in export")
    (args.output / "data.json").write_text(text, encoding="utf-8")
    flat = []
    for row in data["episodes"]:
        item = {k: row[k] for k in ("split", "task", "seed")}
        for label in ("baseline", "geometry", "combined"):
            for key in ("success", "valid", "elapsed_s", "termination_reason", "final_native_success", "success_path",
                        "vla_calls", "manual_calls", "first_success_step", "first_success_action", "result_sha256", "states_sha256"):
                item[f"{label}_{key}"] = row[label][key]
        for ref in ("geometry", "baseline"):
            for key in ("strict_equal", "robot_state_exact_equal", "robot_state_max_abs_diff", "task_language_equal"):
                item[f"initial_vs_{ref}_{key}"] = row["initial_conditions"][ref][key]
        flat.append(item)
    with (args.output / "episodes.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(flat)
    print(json.dumps({"episodes": len(flat), "summary": data["summary"], "initial_comparison": data["initial_comparison"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
