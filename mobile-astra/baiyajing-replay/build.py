"""Publish two recorded Baiyajing episodes; never rerun the simulator.

python build.py --run RUN_DIR --analysis REPORT_DIR --output REPLAY_DIR
Video covers VLA attempts only. Planner images and final images are identified
using the controller's single image counter, checked against every frame file.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path):
    result = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,r_frame_rate,nb_frames,duration,codec_name", "-of", "json", str(path)]))
    s = result["streams"][0]
    assert (s["codec_name"], s["width"], s["height"], s["r_frame_rate"]) == ("h264", 512, 256, "10/1")
    return {"duration": float(s["duration"]), "frames": int(s["nb_frames"]),
            "fps": 10, "width": 512, "height": 256}


NOTES = {
    5: {
        "headline": "重规划抓取后，搬运与放置成功",
        "summary": "首次整任务 VLA 停滞，Planner 把任务拆成启动烤面包机、抓取、搬运和放置。首次 pick 的最终检查失败后，Planner 重新安排抓取；随后 carry 保持持物，put_down 放下，环境判定成功。",
        "step_notes": {
            1: "完整任务 VLA 执行 45 个 chunks 后 idle。toaster_on=false，面包仍在烤面包机中；此时尚未调用 Planner。",
            2: "Planner 改写为启动手柄的子任务。6 个 chunks 后 done，toaster_on 从 false 变为 true；这里只完成了一个子目标。",
            3: "第一次 pick 有两次 attempt：budget 60 chunks、grasped 15 chunks。但抬手后的持物检查未通过，整个步骤 ok=false，队列中后续搬运 / 放置被取消。",
            4: "第二次计划再次安排 pick。39 个 chunks 后 grasped，步骤 ok=true、robot_holding=obj，toast_in_slot=false。",
            5: "Planner 安排 carry 到 dining_counter、以 plate 为参考。执行器报告 still_grasped=true、final_dist=0.024；本段没有连续录像。",
            6: "put_down 报告 released=true、obj_height=0.945。随后环境 check_success() 为 true，计划末尾额外的 VLA 入盘步骤未执行。最终图像可见面包在盘上。",
        },
        "plan_notes": {
            1: "首次 VLA 停滞后，将剩余任务拆为 5 个步骤。实际只执行前两个；pick 失败后停止原队列并重规划。",
            2: "基于 pick 失败后的观测重新规划。实际执行 pick → carry → put_down 后成功，最后一个 VLA 步骤未执行。",
        },
        "lessons": [
            "Planner 既选择子任务 prompt，也决定抓取、导航目标和放置顺序。vla 与 pick 的动作由 VLA 执行，carry / put_down 由执行器控制。",
            "attempt 的 grasped 不保证整个 pick 成功：执行器随后抬手并检查是否仍持有目标。第一次 pick 最终失败，因此触发第二次计划。",
            "最终成功发生在 put_down 步骤之后；计划中剩余的 VLA 入盘操作未执行。计划输出不能当成实际执行记录。",
        ],
    },
    3: {
        "headline": "已抓出面包，搬运后掉落，Planner 判为不可恢复",
        "summary": "初始 VLA 已启动烤面包机，但没有完成取出与送盘。Planner 安排 pick → carry → put_down；抓取最终通过，carry 后却失去目标，记录的面包高度降到 0.068 米。Planner 随后输出 unrecoverable=true，环境未成功。",
        "step_notes": {
            1: "完整任务 VLA 执行 129 个 chunks 后 idle。toaster_on=true，但 toast_in_slot=true，仍需要取出面包并送到盘子。",
            2: "Planner 的 pick 运行两次 attempt（39 + 15 chunks）。最终 ok=true、robot_holding=obj，面包已离开烤面包机。",
            3: "carry 已到达目标附近（final_dist=0.023），但 still_grasped=false。步骤后检测到 obj 丢失，高度为 0.068 米，触发 object_fell。该段没有连续录像，无法从视频定位具体掉落时刻。",
        },
        "plan_notes": {
            1: "Planner 根据已启动烤面包机的状态，安排抓取、搬运、放下及必要的 VLA 入盘。实际只执行 pick 和 carry，后两步未执行。",
            2: "收到 carry 失败与物体丢失反馈后，Planner 输出 unrecoverable=true、steps=[]。随后整局以 object_on_floor 结束。",
        },
        "lessons": [
            "路径规划成功、底盘靠近目标，不代表物体成功送达。carry 同时要求保持抓取；本例仍接近目标，但失去面包，所以 ok=false。",
            "最后一个计划明确宣告不可恢复。这是 Planner 在收到真实执行反馈后的输出，不是执行器自动生成的 fallback。",
            "两例最终的 toaster_on=true、toast_in_slot=false 相同，但只有 seed 5 环境成功。局部 progress 字段不包含全部成功条件，不能用它们替代 check_success()。",
        ],
    },
}


def build_case(seed, run, analysis, out):
    key = "success" if seed == 5 else "failure"
    detail_path = analysis / "cases" / f"GetToastedBread--{seed}.json"
    d = json.loads(detail_path.read_text())
    cell = run / f"GetToastedBread_s{seed}"
    assert d["success"] == (seed == 5) and d["llm_calls"] == 2
    assert d["fallback_steps"] == 0
    for name, digest in d["source"]["files"].items():
        assert sha(cell / name) == digest
    destination = out / key
    (destination / "videos").mkdir(parents=True, exist_ok=True)
    (destination / "frames").mkdir(exist_ok=True)
    sources = {}

    def copy(kind, name):
        src = cell / kind / name
        assert src.is_file() and Path(name).name == name
        shutil.copy2(src, destination / kind / name)
        sources[f"{kind}/{name}"] = sha(src)
        return f"{key}/{kind}/{name}"

    # Every _vla_step snapshot is aNNN.png; every planner images() call is NNN.png.
    # The same monotonically increasing counter also names the final images() call.
    frames = sorted((cell / "frames").glob("*.png"), key=lambda f: int(f.stem.lstrip("a")))
    assert [int(f.stem.lstrip("a")) for f in frames] == list(range(len(frames)))
    planner_frames = [f for f in frames if not f.stem.startswith("a")]
    assert len(planner_frames) == len(d["plans"]) + 1
    all_observations = []
    items, clip_count, clip_duration, total_frames = [], 0, 0.0, 0
    for step in d["trace"]:
        media = []
        for attempt in step["attempt_events"]:
            a = attempt["result"]
            if a.get("frame"):
                all_observations.append((step["event_start"], attempt["index"], a["frame"]))
            if a.get("video"):
                info = probe(cell / "videos" / a["video"])
                assert info["frames"] == a["chunks"] * 4
                media.append({"type": "video", "src": copy("videos", a["video"]),
                              "attempt": attempt["index"], "status": a["status"],
                              "chunks": a["chunks"], "snapshot": copy("frames", a["frame"]), **info})
                clip_count += 1
                clip_duration += info["duration"]
                total_frames += info["frames"]
        items.append({"id": f'step-{step["index"]}', "type": "step", "ref": step["index"],
                      "event_number": step["event_start"], "media": media,
                      "note": NOTES[seed]["step_notes"][step["index"]]})
    for plan, frame in zip(d["plans"], planner_frames[:-1]):
        all_observations.append((plan["event_number"], 0, frame.name))
        items.append({"id": f'plan-{plan["index"]}', "type": "plan", "ref": plan["index"],
                      "event_number": plan["event_number"],
                      "media": [{"type": "image", "src": copy("frames", frame.name), "purpose": "planner"}],
                      "note": NOTES[seed]["plan_notes"][plan["index"]]})
    observations = [name for _, _, name in sorted(all_observations)] + [planner_frames[-1].name]
    assert observations == [f.name for f in frames]
    items.sort(key=lambda item: item["event_number"])
    items.append({"id": "result", "type": "result", "ref": None,
                  "media": [{"type": "image", "src": copy("frames", planner_frames[-1].name), "purpose": "final"}],
                  "note": "环境最终 success=true，任务完成。" if d["success"] else "环境最终 success=false；终止标签 object_on_floor。"})
    assert clip_count == (5 if seed == 5 else 3)
    assert total_frames == d["vla_chunks"] * 4
    assert clip_count == len(list((cell / "videos").glob("*.mp4")))
    sources["analysis-case.json"] = sha(detail_path)
    d.update(key=key, headline=NOTES[seed]["headline"], explanation=NOTES[seed]["summary"],
             lessons=NOTES[seed]["lessons"], items=items,
             media_summary={"clips": clip_count, "duration": round(clip_duration, 2), "frames": total_frames,
                            "unrecorded_steps": [s["index"] for s in d["trace"] if s["command"]["op"] not in {"vla", "pick"}]},
             media_source=sources)
    return d


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = [build_case(seed, args.run, args.analysis, args.output) for seed in (5, 3)]
    (args.output / "data.json").write_text(json.dumps({"cases": cases}, ensure_ascii=False, indent=2) + "\n")
    for name in ("index.html", "style.css", "app.js", "build.py"):
        path = Path(__file__).parent / name
        if path.exists():
            shutil.copy2(path, args.output / name)
    print(json.dumps({c["key"]: c["media_summary"] for c in cases}))


if __name__ == "__main__":
    main()
