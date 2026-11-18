# Copyright 2026 The RPent Authors.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0

"""Run the 32 x 5 pure-VLA matrix on idle GPUs, after a bounded smoke episode."""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from robots.robocasa.eval.pure_vla import atomic_json
from robots.robocasa.eval.summarize_pure_vla import (
    DEFAULT_MANIFEST,
    load_manifest,
    manifest_sha256,
    summarize_results,
    validate_cell_result,
)
from rpent.utils.logging import get_logger

logger = get_logger("pure_vla_suite")
REPO = Path(__file__).resolve().parents[3]


def cells(manifest: dict) -> list[tuple[str, str, int]]:
    """Require exactly one episode for each task and each explicit seed 1–5."""
    result = []
    for group, split in manifest["splits"].items():
        if split["seeds"] != [1, 2, 3, 4, 5] or len(split["tasks"]) != 16:
            raise ValueError("Suite requires 16 tasks per group and seeds 1–5")
        result.extend(
            (group, task, seed) for task in split["tasks"] for seed in split["seeds"]
        )
    if len(result) != 160 or len(set(result)) != 160:
        raise ValueError("Suite must contain 160 unique task/seed cells")
    return result


def gpu_status() -> dict[int, dict[str, Any]]:
    """Read GPU load and compute process IDs; query failure stops dispatch."""

    def query(kind, fields):
        output = subprocess.check_output(
            ["nvidia-smi", f"--query-{kind}={fields}", "--format=csv,noheader,nounits"],
            text=True,
            timeout=20,
        )
        return [
            [part.strip() for part in row]
            for row in csv.reader(output.splitlines())
            if row
        ]

    devices = {
        int(index): {
            "uuid": uuid,
            "memory_mib": int(memory),
            "utilization": int(util),
            "pids": [],
        }
        for index, uuid, memory, util in query(
            "gpu", "index,uuid,memory.used,utilization.gpu"
        )
    }
    by_uuid = {gpu["uuid"]: gpu for gpu in devices.values()}
    for uuid, pid in query("compute-apps", "gpu_uuid,pid"):
        if uuid in by_uuid:
            by_uuid[uuid]["pids"].append(int(pid))
    return devices


def idle(gpu: dict, memory_limit: int) -> bool:
    return (
        not gpu["pids"] and gpu["memory_mib"] < memory_limit and gpu["utilization"] < 5
    )


def foreign_processes(pids: list[int], process_group: int) -> list[int]:
    """Only the launched child's process group belongs to this episode."""
    foreign = []
    for pid in pids:
        try:
            if os.getpgid(pid) != process_group:
                foreign.append(pid)
        except ProcessLookupError:
            continue
        except PermissionError:
            foreign.append(pid)
    return foreign


def stop_process(child: subprocess.Popen) -> None:
    """Stop only this runner's episode and its descendants."""
    try:
        os.killpg(child.pid, signal.SIGTERM)
        child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=15)
    except ProcessLookupError:
        child.wait()


def completed(path: Path, cell: tuple, manifest: dict, *, smoke: bool = False) -> bool:
    return not validate_cell_result(
        path / "result.json",
        manifest=manifest,
        expected_task=cell[1],
        expected_seed=cell[2],
        allow_smoke=smoke,
    )


def episode_command(args, cell, path, *, smoke=False) -> list[str]:
    command = [
        str(args.python),
        "-m",
        "robots.robocasa.eval.pure_vla",
        "--task-name",
        cell[1],
        "--seed",
        str(cell[2]),
        "--checkpoint",
        str(args.checkpoint),
        "--cuda-device",
        "0",
        "--manifest",
        str(args.output / "manifest.json"),
        "--output-dir",
        str(path),
    ]
    if smoke:
        command += ["--smoke-max-native-steps", "32"]
    return command


@dataclass
class Running:
    child: subprocess.Popen
    cell: tuple[str, str, int]
    path: Path
    gpu: int
    started: float
    log: Any
    lock: Any
    smoke: bool


def run(args) -> int:
    manifest = load_manifest(args.manifest)
    matrix = cells(manifest)
    if args.dry_run:
        print(json.dumps({"total": len(matrix), "cells": matrix}, indent=2))
        return 0
    args.output.mkdir(parents=True, exist_ok=True)
    batch_lock = (args.output / ".lock").open("a")
    fcntl.flock(batch_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    frozen = args.output / "manifest.json"
    if frozen.exists() and manifest_sha256(frozen) != manifest_sha256(manifest):
        raise ValueError(
            "Output belongs to a different protocol; use a new output directory"
        )
    atomic_json(frozen, manifest)
    atomic_json(args.output / "matrix.json", {"cells": matrix, "count": 160})
    (args.output / "source.patch").write_bytes(
        subprocess.check_output(["git", "diff", "HEAD"], cwd=REPO)
    )
    source_snapshot = args.output / "source"
    source_snapshot.mkdir(exist_ok=True)
    for name in ("run_pure_vla_suite.py", "pure_vla.py", "summarize_pure_vla.py"):
        (source_snapshot / name).write_bytes(
            Path(__file__).with_name(name).read_bytes()
        )
    atomic_json(
        args.output / "launch.json",
        {
            "pid": os.getpid(),
            "started_at": time.time(),
            "gpus": args.gpus,
            "python": str(args.python),
            "checkpoint": str(args.checkpoint),
            "git_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
            ).strip(),
            "protocol_sha256": manifest_sha256(manifest),
        },
    )
    env = dict(os.environ)
    for key in ("RLDX_RESET_SEED", "PYTHONPATH", "TRANSFORMERS_CACHE"):
        env.pop(key, None)
    env.update(
        MUJOCO_GL="egl",
        PYOPENGL_PLATFORM="egl",
        NO_ALBUMENTATIONS_UPDATE="1",
        PYTHONHASHSEED="0",
        PYTHONNOUSERSITE="1",
        RLDX_ATTN_IMPL="sdpa",
        OMP_NUM_THREADS="4",
        OPENBLAS_NUM_THREADS="1",
    )
    max_attempts = manifest["retry_policy"]["max_infrastructure_attempts"]
    timeout = manifest["runtime"]["watchdog_timeout_s"]
    smoke_cell = ("composite_seen", "ScrubCuttingBoard", 1)
    smoke_path = args.output / "smoke"
    active: dict[int, Running] = {}
    stable_idle = dict.fromkeys(args.gpus, 0)
    blocked = []
    locks = Path.home() / ".local/state/rpent-gpu-locks"
    locks.mkdir(parents=True, exist_ok=True)

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGHUP, interrupt)

    def archive(path):
        parent = args.output / "attempts" / path.relative_to(args.output)
        parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.rename(parent / str(time.time_ns()))
        return len(list(parent.iterdir()))

    try:
        while True:
            devices = gpu_status()
            if not set(args.gpus) <= set(devices):
                raise ValueError("Requested GPU index does not exist")
            for gpu, job in list(active.items()):
                reason = None
                if foreign_processes(devices[gpu]["pids"], job.child.pid):
                    reason = "foreign_gpu_process"
                elif time.monotonic() - job.started > timeout:
                    reason = "watchdog_timeout"
                if reason and job.child.poll() is None:
                    stop_process(job.child)
                code = job.child.poll()
                if code is None:
                    continue
                job.log.close()
                job.lock.close()
                atomic_json(
                    job.path / "attempt.json",
                    {"returncode": code, "reason": reason, "gpu": gpu},
                )
                valid = (
                    code == 0
                    and not reason
                    and completed(job.path, job.cell, manifest, smoke=job.smoke)
                )
                if valid and job.smoke:
                    outcome = json.loads((job.path / "result.json").read_text())
                    valid = outcome["is_smoke"] and (
                        outcome["native_steps"] == 32 or outcome["any_success"]
                    )
                if valid:
                    logger.info(
                        "Finished %s seed=%s smoke=%s",
                        job.cell[1],
                        job.cell[2],
                        job.smoke,
                    )
                else:
                    attempts = archive(job.path)
                    logger.error(
                        "Infrastructure attempt failed: %s seed=%s (%s), attempt %s/%s",
                        job.cell[1],
                        job.cell[2],
                        reason or code,
                        attempts,
                        max_attempts,
                    )
                    if attempts >= max_attempts:
                        blocked.append(job.cell)
                        if job.smoke:
                            raise RuntimeError(
                                "Smoke failed three times; formal evaluation was not started"
                            )
                del active[gpu]
                stable_idle[gpu] = 0

            smoke_ok = completed(smoke_path, smoke_cell, manifest, smoke=True)
            summary, _ = summarize_results(args.output, manifest=manifest)
            atomic_json(args.output / "summary.json", summary)
            pending = [
                cell
                for cell in matrix
                if cell not in blocked
                and not any(
                    job.cell == cell and not job.smoke for job in active.values()
                )
                and not completed(
                    args.output / cell[0] / f"{cell[1]}_s{cell[2]}", cell, manifest
                )
            ]
            if smoke_ok and not pending and not active:
                atomic_json(
                    args.output / "queue.json",
                    {
                        "phase": "complete" if summary["complete"] else "blocked",
                        "blocked": blocked,
                        "active": [],
                        "updated_at": time.time(),
                    },
                )
                return 0 if summary["complete"] else 1
            for gpu in args.gpus:
                if gpu in active:
                    continue
                stable_idle[gpu] = (
                    stable_idle[gpu] + 1
                    if idle(devices[gpu], args.idle_memory_mib)
                    else 0
                )
                if stable_idle[gpu] < 2:
                    continue
                if not smoke_ok:
                    if active:
                        break
                    cell, path, smoke = smoke_cell, smoke_path, True
                elif pending:
                    cell = pending.pop(0)
                    path = args.output / cell[0] / f"{cell[1]}_s{cell[2]}"
                    smoke = False
                else:
                    break
                attempts = archive(path)
                if attempts >= max_attempts:
                    if smoke:
                        raise RuntimeError(
                            "Smoke exhausted its infrastructure attempts"
                        )
                    blocked.append(cell)
                    continue
                gpu_lock = (locks / f"gpu-{devices[gpu]['uuid']}.lock").open("a")
                try:
                    fcntl.flock(gpu_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    gpu_lock.close()
                    continue
                if not idle(gpu_status()[gpu], args.idle_memory_mib):
                    gpu_lock.close()
                    stable_idle[gpu] = 0
                    continue
                path.mkdir(parents=True, exist_ok=True)
                child_env = dict(
                    env, CUDA_VISIBLE_DEVICES=str(gpu), MUJOCO_EGL_DEVICE_ID=str(gpu)
                )
                log = (path / "run.log").open("w")
                command = episode_command(args, cell, path, smoke=smoke)
                atomic_json(
                    path / "launch.json",
                    {"command": command, "gpu": gpu, "started_at": time.time()},
                )
                child = subprocess.Popen(
                    command,
                    cwd=REPO,
                    env=child_env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                active[gpu] = Running(
                    child, cell, path, gpu, time.monotonic(), log, gpu_lock, smoke
                )
                logger.info(
                    "Started GPU %s: %s seed=%s smoke=%s", gpu, cell[1], cell[2], smoke
                )
            atomic_json(
                args.output / "queue.json",
                {
                    "phase": "running" if active else "waiting_for_idle_gpu",
                    "smoke_passed": smoke_ok,
                    "pending": len(pending),
                    "blocked": blocked,
                    "active": [
                        {
                            "gpu": gpu,
                            "pid": job.child.pid,
                            "task": job.cell[1],
                            "seed": job.cell[2],
                            "smoke": job.smoke,
                        }
                        for gpu, job in active.items()
                    ],
                    "gpu_status": devices,
                    "updated_at": time.time(),
                },
            )
            time.sleep(args.poll_seconds)
    except BaseException as exc:
        atomic_json(
            args.output / "queue.json",
            {
                "phase": "stopped" if isinstance(exc, KeyboardInterrupt) else "error",
                "error": str(exc),
                "active": [],
                "blocked": blocked,
                "updated_at": time.time(),
            },
        )
        raise
    finally:
        for job in active.values():
            stop_process(job.child)
            job.log.close()
            job.lock.close()
        batch_lock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--gpus", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--idle-memory-mib", type=int, default=1024)
    parser.add_argument("--poll-seconds", type=float, default=15)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    # Resolving a venv's Python symlink bypasses pyvenv.cfg and its packages.
    args.python = args.python.expanduser().absolute()
    for name in ("checkpoint", "output", "manifest"):
        setattr(args, name, getattr(args, name).expanduser().resolve())
    if (
        args.poll_seconds <= 0
        or args.idle_memory_mib <= 0
        or len(set(args.gpus)) != len(args.gpus)
    ):
        parser.error("Polling/memory limits must be positive and GPU indexes unique")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
