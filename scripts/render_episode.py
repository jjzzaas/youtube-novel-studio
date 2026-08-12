import asyncio
import re
import subprocess
import sys
from pathlib import Path

import edge_tts


def clean_markdown(text: str) -> str:
    text = re.sub(r"^---.*?---\s*", "", text, flags=re.S)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"[*_`>#-]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def pick_korean_voice() -> str:
    voices = await edge_tts.list_voices()
    korean = [v for v in voices if v.get("Locale") == "ko-KR"]
    if not korean:
        raise RuntimeError("No Korean voice found")
    female = [v for v in korean if v.get("Gender") == "Female"]
    return (female or korean)[0]["ShortName"]


async def synthesize(text: str, mp3_path: Path, srt_path: Path) -> str:
    voice = await pick_korean_voice()
    communicate = edge_tts.Communicate(text, voice, rate="-5%")
    submaker = edge_tts.SubMaker()
    with mp3_path.open("wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)
    srt_path.write_text(submaker.get_srt(), encoding="utf-8")
    return voice


def probe_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def render_video(audio_path: Path, srt_path: Path, output_path: Path, title: str) -> None:
    safe_title = title.replace("'", "’").replace(":", "：")
    vf = (
        "drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:"
        f"text='{safe_title}':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=100,"
        f"subtitles='{srt_path.as_posix()}':"
        "force_style='FontName=Noto Sans CJK KR,FontSize=18,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=70'"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=0x111111:s=1920x1080:r=30",
            "-i", str(audio_path),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
            "-c:a", "aac", "-b:a", "160k",
            "-shortest", str(output_path),
        ],
        check=True,
    )


async def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/render_episode.py episodes/<project>/epXXX.md")

    script_path = Path(sys.argv[1])
    raw = script_path.read_text(encoding="utf-8")
    text = clean_markdown(raw)
    if len(text) < 300:
        raise RuntimeError("Episode text is too short for rendering")

    project = script_path.parent.name
    episode = script_path.stem
    title = f"{project} {episode}"

    out_dir = Path("output") / project / episode
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = out_dir / f"{episode}.mp3"
    srt_path = out_dir / f"{episode}.srt"
    mp4_path = out_dir / f"{episode}.mp4"

    voice = await synthesize(text, mp3_path, srt_path)
    duration = probe_duration(mp3_path)
    render_video(mp3_path, srt_path, mp4_path, title)

    report = (
        f"project={project}\n"
        f"episode={episode}\n"
        f"characters={len(text)}\n"
        f"voice={voice}\n"
        f"duration_seconds={duration:.2f}\n"
        f"duration_minutes={duration / 60:.2f}\n"
    )
    (out_dir / "report.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
