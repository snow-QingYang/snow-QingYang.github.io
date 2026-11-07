#!/usr/bin/env python3
"""Export public E06 statistics; raw prompts, transcripts and local paths stay private.

python extract.py --run-root RUN --reference-data ../../task-progress/analysis/data.json \
  --baseline-data ../../baseline/analysis/data.json --output .
"""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def percent(successes, total):
    return (Decimal(successes) * 100 / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def summarize(rows):
    counts = {name: sum(r[f"{name}_success"] for r in rows)
              for name in ("baseline", "notask", "agent")}
    declarations = {name: {"native_success": 0, "native_failure": 0}
                    for name in ("success", "stuck", "failure", "no_finish")}
    for row in rows:
        declarations[row["declaration"]]["native_success" if row["agent_success"] else "native_failure"] += 1
    paired = {}
    for reference in ("baseline", "notask"):
        paired[reference] = {
            "both_success": sum(r[f"{reference}_success"] and r["agent_success"] for r in rows),
            "reference_only": sum(r[f"{reference}_success"] and not r["agent_success"] for r in rows),
            "agent_only": sum(not r[f"{reference}_success"] and r["agent_success"] for r in rows),
            "both_failure": sum(not r[f"{reference}_success"] and not r["agent_success"] for r in rows),
        }
    return {"total": len(rows), "success": counts, "declarations": declarations,
            "finish_called": sum(r["finish_called"] for r in rows), "paired": paired}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--reference-data", type=Path, required=True)
    parser.add_argument("--baseline-data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = read(args.reference_data)
    baseline = read(args.baseline_data)
    final_path = args.run_root / "final_summary.json"
    final = read(final_path)
    refs = {(r["split"], r["task"], r["seed"]): r for r in reference["episodes"]}
    astra = {(r["split"], r["task"], r["seed"]): r
             for r in baseline["episodes"] if r["model"] == "astra"}
    expected = {(split, task, seed) for split, tasks in reference["tasks"].items()
                for task in tasks for seed in range(1, 6)}
    require(len(expected) == 160 and set(refs) == set(astra) == expected,
            "Reference coverage must be exactly the 160 composite cells")
    require(final["validation_errors"] == [] and final["valid_cells"] == 160,
            "Final evaluator validation did not pass")
    rows = []
    paths = []
    for split, tasks in reference["tasks"].items():
        for task in tasks:
            for seed in range(1, 6):
                key = (split, task, seed)
                path = args.run_root / f"composite_{split}" / f"{task}_s{seed}" / "result.json"
                result = read(path)
                paths.append(path)
                require(result["valid"] is True and type(result["success"]) is bool,
                        f"Invalid result: {key}")
                require((result["evaluation_split"], result["task_name"], result["seed"])
                        == (f"composite_{split}", task, seed), f"Wrong cell: {key}")
                require(result["success_source"] == "env.check_success_after_planner"
                        and result["experiment_variant"] == "agent_stop", f"Wrong score source: {key}")
                require(result["environment_split"] == "target"
                        and result["planner"] == {"backend": "codex", "model": "gpt-6-astra",
                                                  "reasoning_effort": "xhigh", "max_turns": 100},
                        f"Planner configuration differs: {key}")
                require(result["runtime"] == {"cell_timeout_seconds": 3600, "rldx_max_chunks": 40,
                                              "rldx_settle_patience": 999, "rldx_action_steps_per_chunk": 8},
                        f"Runtime configuration differs: {key}")
                finish = result["agent_finish"]
                called = finish["called"]
                declaration = finish["status"] if called else "no_finish"
                require(type(called) is bool and declaration in ("success", "stuck", "failure", "no_finish"),
                        f"Unknown finish declaration: {key}")
                require(called or finish["status"] is None, f"Declaration without finish: {key}")
                require(result["termination_reason"] == ("agent_finish" if called else "agent_return_without_finish"),
                        f"Inconsistent termination: {key}")
                prior = refs[key]
                require(astra[key]["valid"] is True and astra[key]["success"] == prior["baseline_success"],
                        f"E01 reference mismatch: {key}")
                rows.append({"split": split, "task": task, "seed": seed,
                             "baseline_success": prior["baseline_success"],
                             "notask_success": prior["notask_success"],
                             "agent_success": result["success"], "valid": True,
                             "finish_called": called, "declaration": declaration,
                             "termination_reason": result["termination_reason"],
                             "elapsed_s": result["elapsed_s"],
                             "baseline_elapsed_s": prior["baseline_elapsed_s"],
                             "notask_elapsed_s": prior["notask_elapsed_s"],
                             "result_sha256": digest(path),
                             "baseline_result_sha256": prior["baseline_result_sha256"],
                             "notask_result_sha256": prior["notask_result_sha256"]})
    require(set(paths) == set(args.run_root.glob("**/result.json")), "Unexpected extra result files")
    summary = {split: summarize([r for r in rows if r["split"] == split]) for split in ("seen", "unseen")}
    summary["all"] = summarize(rows)
    require(summary["all"]["declarations"] == final["agent_declaration_vs_native"], "Declaration summary mismatch")
    require(summary["all"]["finish_called"] == final["termination_reasons"]["agent_finish"], "Finish count mismatch")
    for split in ("seen", "unseen"):
        require(summary[split]["success"]["agent"] == final["splits"][f"composite_{split}"]["successes"],
                f"Final split summary mismatch: {split}")
    source_path = args.run_root / "source_revision.json"
    source = read(source_path)
    data = {
        "schema_version": 1, "experiment": "agent_check_success",
        "generated_utc": datetime.now(timezone.utc).isoformat(), "completed_at": final["completed_at"],
        "protocol": {"model": "gpt-6-astra", "effort": "xhigh", "vla": "RLDX-1-FT-RC365",
                     "memory": "GPT_6_astra_high", "environment_split": "target", "seeds": [1, 2, 3, 4, 5],
                     "max_turns": 100, "timeout_s": 3600, "vla_max_chunks": 40,
                     "vla_action_steps_per_chunk": 8, "vla_settle_patience": 999,
                     "score_source": "env.check_success_after_planner",
                     "finish_required_by_prompt": True, "finish_enforced_by_runtime": False},
        "sources": {"agent": {"run": args.run_root.name, "base_commit": source["base_commit"],
                              "published_commit": "65f7e1b85eba219c28ccb75f94740d75071fca34",
                              "branch": "agent_check_success", "source_files": source["source_files"],
                              "final_summary_sha256": digest(final_path), "source_revision_sha256": digest(source_path)},
                    "baseline": reference["sources"]["baseline"], "notask": reference["sources"]["notask"],
                    "reference_data_sha256": digest(args.reference_data), "baseline_data_sha256": digest(args.baseline_data)},
        "comparison_limits": ["Task/seed matching; initial scene and VLA sampling equivalence not audited for E06.",
                              "Published E03 predates the later NoTaskGT revision that stopped generating success_criteria.md.",
                              "Native scoring happens after the planner returns; agent claims are reported separately.",
                              "Prompt requests finish, but the planner can return without calling it."],
        "summary": summary, "tasks": reference["tasks"], "episodes": rows,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    with (args.output / "episodes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# E06 · agent_check_success", "", "GPT-6-Astra / xhigh · RoboCasa composite · 32 tasks × seeds 1–5.", "",
             "Score: native env.check_success after the planner returns. Agent declarations are separate.", "",
             "| Split | E01 baseline | E03 NoTaskGT | E06 |", "| --- | ---: | ---: | ---: |"]
    for split, stats in summary.items():
        n = stats["total"]
        cells = [f'{stats["success"][name]}/{n} ({percent(stats["success"][name], n)}%)'
                 for name in ("baseline", "notask", "agent")]
        lines.append(f'| {split} | ' + " | ".join(cells) + " |")
    lines += ["", "## Agent declaration vs final native score", "", "| Declaration | Native success | Native failure |",
              "| --- | ---: | ---: |"]
    for name, counts in summary["all"]["declarations"].items():
        lines.append(f'| {name} | {counts["native_success"]} | {counts["native_failure"]} |')
    lines += ["", "134/160 episodes called finish; 26 returned without it. The sole native success without finish was WaffleReheat, seed 4 (Unseen).",
              "43 success claims include 15 final native failures. All 160 valid episodes remain in the denominator.", "",
              "## Settings and interpretation", "",
              "No task_progress, success or robocasa_terminated in Agent observations; no native-success early VLA stop. No success_criteria.md is generated. The prompt asks the Agent to judge completion and call finish; runtime does not enforce that call.", "",
              "Simulator geometry, camera calibration, robot state, contact feedback and selected memory remain. Private native predicate calls preserve simulator bookkeeping. Final scoring is not shown to the running Agent.", "",
              *[f"- {limit}" for limit in data["comparison_limits"]], "",
              "## Task / seed results", "", "Each seed cell is E01 / E03 / E06 followed by the E06 declaration; 1 = native success, 0 = failure.", "",
              "| Split | Task | Seed 1 | Seed 2 | Seed 3 | Seed 4 | Seed 5 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for split, tasks in data["tasks"].items():
        for task in tasks:
            cells = [f'{int(r["baseline_success"])} / {int(r["notask_success"])} / {int(r["agent_success"])} · {r["declaration"]}'
                     for r in rows if r["split"] == split and r["task"] == task]
            lines.append(f"| {split} | {task} | " + " | ".join(cells) + " |")
    lines += ["", "## Provenance", "", f'Run: `{args.run_root.name}`.', "",
              f'Published implementation: `{data["sources"]["agent"]["published_commit"]}`; branch `agent_check_success`.', "",
              "JSON and CSV contain per-result SHA-256 hashes. The extractor verifies all canonical cells, runtime/model settings, final summary and E01 reference agreement. It exports only selected structured fields; no raw transcripts or credentials.", ""]
    (args.output / "report.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
