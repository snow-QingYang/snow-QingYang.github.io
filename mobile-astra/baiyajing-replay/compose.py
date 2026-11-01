"""Assemble recorded VLA clips and explicitly labelled still/log cards.

Pillow and ffmpeg are required. Each inserted card lasts four presentation
seconds; its duration never represents planner latency or unrecorded motion.
"""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FPS = 10
CARD_FRAMES = 40


def card(case, item, out, path):
    im = Image.new("RGB", (512, 256), "#17232d")
    draw = ImageDraw.Draw(im)
    fonts = {n: ImageFont.truetype(FONT, n, index=2) for n in (11, 13, 16, 22)}
    draw.rectangle((0, 0, 512, 42), fill="#22323f")
    if item["type"] == "plan":
        title = f'计划 #{item["ref"]} · Planner 输入观测（静态图）'
    elif item["type"] == "result":
        title = f'最终环境：{"成功" if case["success"] else "未成功"} · 静态观测图'
    else:
        step = next(s for s in case["trace"] if s["index"] == item["ref"])
        title = f'步骤 #{step["index"]} · {step["command"]["op"]} · 执行日志'
    draw.text((14, 10), title, font=fonts[16], fill="#edf3f7")
    if item["media"]:
        original = Image.open(out / item["media"][0]["src"]).convert("RGB")
        image = ImageOps.contain(original, (512, 170), Image.Resampling.LANCZOS)
        im.paste(image, ((512-image.width)//2, 42+(170-image.height)//2))
    else:
        draw.text((143, 76), "未录制动作视频", font=fonts[22], fill="#f2d5b5")
        result = step["summary"].get("result", {})
        values = [f"{k}={str(result[k]).lower()}" for k in ("still_grasped", "released", "obj_height") if k in result]
        draw.text((30, 126), " · ".join(values), font=fonts[16], fill="#e7edf2")
        draw.text((30, 158), "参数与执行结果见右侧对应记录", font=fonts[13], fill="#b9c8d4")
    draw.rectangle((0, 212, 512, 256), fill="#22323f")
    draw.text((14, 218), "说明画面固定展示 4 秒，不代表实际耗时或连续动作", font=fonts[11], fill="#cad6df")
    if item["type"] == "result":
        footer = f'result.success={str(case["success"]).lower()} · {case["stop"]}'
    elif item["type"] == "plan":
        plan = next(p for p in case["plans"] if p["index"] == item["ref"])
        footer = ("unrecoverable=true · steps=[]" if plan["program"].get("unrecoverable") else
                  " → ".join(s["op"] for s in plan["program"]["steps"]))
    else:
        footer = f'子步骤 ok={str(step["summary"]["ok"]).lower()} · 无连续录像'
    draw.text((14, 235), footer, font=fonts[11], fill="#f0f4f7")
    im.save(path)


def compose(case, out, skip_video=False):
    frame = 0
    segments = []
    target = out / case["key"] / "episode.mp4"
    with tempfile.TemporaryDirectory(prefix="baiyajing-replay-") as temp:
        temp = Path(temp)
        clips = []
        for item in case["items"]:
            item["videoStart"] = frame / FPS
            videos = [m for m in item["media"] if m["type"] == "video"]
            if videos:
                for m in videos:
                    start = frame / FPS
                    frame += m["frames"]
                    m.update(videoStart=start, videoEnd=frame/FPS)
                    segments.append({"item": item["id"], "type": "video", "attempt": m["attempt"],
                                     "start": start, "end": frame/FPS, "source": m["src"]})
                    clips.append(out / m["src"])
            else:
                start = frame / FPS
                frame += CARD_FRAMES
                segments.append({"item": item["id"], "type": "card", "start": start, "end": frame/FPS,
                                 "source": item["media"][0]["src"] if item["media"] else None})
                clip = temp / f'{item["id"]}.mp4'
                if not skip_video:
                    still = temp / f'{item["id"]}.png'
                    card(case, item, out, still)
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS),
                                    "-i", str(still), "-frames:v", str(CARD_FRAMES), "-an", "-c:v", "libx264",
                                    "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(clip)], check=True)
                clips.append(clip)
            item["videoEnd"] = frame / FPS
        if not skip_video:
            listing = temp / "clips.txt"
            listing.write_text("".join("file '" + str(p.resolve()).replace("'", "'\\''") + "'\n" for p in clips))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                            "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)], check=True)
    stream = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=nb_frames,r_frame_rate,duration", "-of", "json", str(target)]))["streams"][0]
    assert int(stream["nb_frames"]) == frame
    assert stream["r_frame_rate"] == "10/1"
    assert abs(float(stream["duration"]) - frame/FPS) < .001
    case["replay"] = {"src": f'{case["key"]}/episode.mp4', "duration": frame/FPS,
                      "frames": frame, "fps": FPS, "segments": segments,
                      "card_seconds": CARD_FRAMES/FPS,
                      "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
