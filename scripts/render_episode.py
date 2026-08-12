import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

import edge_tts

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
VOICE_STYLES = {
    "narrator": {"voice": "ko-KR-SunHiNeural", "rate": "-8%", "pitch": "+0Hz"},
    "male": {"voice": "ko-KR-InJoonNeural", "rate": "-4%", "pitch": "-2Hz"},
    "female": {"voice": "ko-KR-SunHiNeural", "rate": "-2%", "pitch": "+2Hz"},
    "soft_female": {"voice": "ko-KR-SunHiNeural", "rate": "-8%", "pitch": "+5Hz"},
    "mature_female": {"voice": "ko-KR-SunHiNeural", "rate": "-6%", "pitch": "-3Hz"},
}


def run(cmd):
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], check=True, capture_output=True, text=True)
    return float(r.stdout.strip())


def srt_time(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000); m, rem = divmod(rem, 60_000); s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def ffpath(path: Path) -> str:
    return path.resolve().as_posix().replace(":", "\\:").replace("'", "\\'")


def clean_markdown(text: str) -> str:
    text = re.sub(r"^---.*?---\s*", "", text, flags=re.S)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"[*_`>#-]", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def markdown_to_episode(path: Path):
    text = clean_markdown(path.read_text(encoding="utf-8"))
    return {"title": f"{path.parent.name} {path.stem}", "segments": [{"speaker": "narrator", "text": text, "pause_after": 0.4, "mood": "neutral"}]}


def load_episode(path: Path):
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        segments = []
        for scene in data.get("scenes", []):
            for item in scene.get("segments", []):
                x = dict(item)
                x.setdefault("mood", scene.get("mood", "neutral"))
                x.setdefault("scene", scene.get("title", ""))
                segments.append(x)
        if not segments:
            segments = data.get("segments", [])
        return {"title": data.get("title", f"{path.parent.name} {path.stem}"), "segments": segments, "metadata": data}
    return markdown_to_episode(path)


def silence(path: Path, seconds: float):
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{seconds:.3f}", "-q:a", "9", "-acodec", "libmp3lame", str(path)])


async def tts(text: str, path: Path, style_name: str):
    style = VOICE_STYLES.get(style_name, VOICE_STYLES["narrator"])
    c = edge_tts.Communicate(text, style["voice"], rate=style["rate"], pitch=style["pitch"])
    await c.save(str(path))
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"TTS failed: {style_name}")
    return style


def write_srt(entries, path: Path):
    lines = []
    for i, e in enumerate(entries, 1):
        label = f"{e['speaker']}: " if e["speaker"] not in ("narrator", "") else ""
        lines.append(f"{i}\n{srt_time(e['start'])} --> {srt_time(e['end'])}\n{label}{e['text']}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def mood_color(mood: str):
    return {
        "calm": "0x18202a", "mystery": "0x15131f", "tension": "0x211619",
        "battle": "0x251313", "warm": "0x221d16", "sad": "0x171b22",
    }.get(mood, "0x111111")


def render_video(audio: Path, srt: Path, output: Path, title: str, mood: str):
    safe = title.replace("'", "’").replace(":", "：")
    sub = ffpath(srt)
    vf = (
        f"drawtext=fontfile={FONT}:text='{safe}':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=95,"
        "drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:text='YouTube Novel Studio':fontcolor=white@0.35:fontsize=24:x=(w-text_w)/2:y=h-55,"
        f"subtitles=filename='{sub}':force_style='FontName=Noto Sans CJK KR,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2,MarginV=95'"
    )
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={mood_color(mood)}:s=1920x1080:r=30", "-i", str(audio), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-c:a", "aac", "-b:a", "160k", "-shortest", str(output)])


async def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/render_episode.py episodes/<project>/epXXX.(md|json)")
    src = Path(sys.argv[1])
    episode = load_episode(src)
    segments = episode.get("segments", [])
    if not segments:
        raise RuntimeError("No episode segments")

    project, ep = src.parent.name, src.stem
    out = Path("output") / project / ep
    tmp = out / "parts"
    tmp.mkdir(parents=True, exist_ok=True)

    concat_lines, subs, voice_report = [], [], []
    cursor = 0.0
    char_count = 0
    first_mood = "neutral"

    for idx, seg in enumerate(segments):
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        char_count += len(text)
        speaker = seg.get("speaker", "narrator")
        style = seg.get("voice_style", speaker if speaker in VOICE_STYLES else "narrator")
        mood = seg.get("mood", "neutral")
        if idx == 0:
            first_mood = mood
        part = tmp / f"{idx:04d}.mp3"
        style_used = await tts(text, part, style)
        dur = probe_duration(part)
        concat_lines.append(f"file '{part.resolve().as_posix()}'")
        subs.append({"speaker": speaker, "text": text, "start": cursor, "end": cursor + dur})
        cursor += dur
        voice_report.append(f"{idx}:{speaker}:{style_used['voice']}:{style_used['rate']}:{style_used['pitch']}")
        pause = float(seg.get("pause_after", 0) or 0)
        if pause > 0:
            p = tmp / f"{idx:04d}_pause.mp3"
            silence(p, pause)
            concat_lines.append(f"file '{p.resolve().as_posix()}'")
            cursor += pause

    concat_file = tmp / "concat.txt"
    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")
    audio = out / f"{ep}.mp3"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c:a", "libmp3lame", "-b:a", "96k", str(audio)])
    final_duration = probe_duration(audio)
    srt = out / f"{ep}.srt"
    write_srt(subs, srt)
    video = out / f"{ep}.mp4"
    render_video(audio, srt, video, episode["title"], first_mood)

    min_sec, max_sec = 8 * 60, 15 * 60
    qc = "PASS" if min_sec <= final_duration <= max_sec else "WARN_DURATION"
    report = {
        "project": project, "episode": ep, "title": episode["title"], "characters": char_count,
        "segments": len(subs), "duration_seconds": round(final_duration, 2), "duration_minutes": round(final_duration / 60, 2),
        "qc": qc, "voices": voice_report, "bgm_hook": True, "sfx_hook": True,
        "youtube_visibility_target": "private"
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
