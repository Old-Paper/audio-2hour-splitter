# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


SEGMENT_SECONDS = 7200
SUPPORTED_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".wav"}


class FriendlyError(Exception):
    """An error that can be shown directly to non-technical users."""


def setup_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def clean_path_text(text: str) -> str:
    text = (text or "").strip().strip("\ufeff")

    if text.startswith("&"):
        text = text[1:].lstrip()

    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        text = text[1:-1]

    if text.lower().startswith("file://"):
        parsed = urlparse(text)
        text = unquote(parsed.path)
        if re.match(r"^/[a-zA-Z]:/", text):
            text = text[1:]
        text = text.replace("/", "\\")

    return text.strip()


def get_audio_path() -> Path:
    args = sys.argv[1:]

    if len(args) == 1:
        raw_path = args[0]
    elif len(args) > 1:
        maybe_files = [Path(clean_path_text(item)) for item in args]
        if all(item.exists() and item.is_file() for item in maybe_files):
            raise FriendlyError("一次只能处理一个音频文件。请只拖入或粘贴一个文件。")
        raw_path = " ".join(args)
    else:
        print("请把音频文件拖到这个窗口里，或粘贴完整路径，然后按 Enter。")
        raw_path = input("音频文件路径: ")

    cleaned_path = clean_path_text(raw_path)
    if not cleaned_path:
        raise FriendlyError("没有输入文件路径。")

    audio_path = Path(cleaned_path).expanduser()

    if not audio_path.exists():
        raise FriendlyError(f"找不到这个文件：\n{audio_path}")

    if not audio_path.is_file():
        raise FriendlyError(f"这不是一个音频文件：\n{audio_path}")

    extension = audio_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = "、".join(sorted(SUPPORTED_EXTENSIONS))
        raise FriendlyError(
            f"暂时只支持这些格式：{supported}\n"
            f"当前文件后缀是：{audio_path.suffix or '无后缀'}"
        )

    return audio_path.resolve()


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg.exe") or shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    raise FriendlyError(
        "没有找到 FFmpeg。\n"
        "请先安装 FFmpeg，并确保在命令行里可以直接运行 ffmpeg。\n"
        "安装方法请看 README.md 里的“安装 FFmpeg”。"
    )


def make_output_dir(audio_path: Path) -> Path:
    base_dir = audio_path.parent / f"{audio_path.stem}_split"
    if not base_dir.exists():
        base_dir.mkdir()
        return base_dir

    for index in range(2, 1000):
        candidate = audio_path.parent / f"{audio_path.stem}_split_{index:02d}"
        if not candidate.exists():
            candidate.mkdir()
            return candidate

    raise FriendlyError("无法创建输出文件夹：同名文件夹太多了。请先整理旧的切割结果。")


def explain_ffmpeg_error(log_text: str) -> str:
    lower_log = log_text.lower()

    if "stream map '0:a:0' matches no streams" in lower_log or "matches no streams" in lower_log:
        return "文件里没有找到可切割的音频流。请确认拖入的是音频文件。"

    if "invalid data found" in lower_log:
        return "文件格式不正确，或音频文件可能已经损坏。"

    if "no such file or directory" in lower_log:
        return "FFmpeg 找不到输入文件或输出路径。请检查文件是否还存在。"

    if "permission denied" in lower_log:
        return "没有读写权限。请关闭正在占用这个文件的软件，或换到有权限的文件夹再试。"

    if "no space left" in lower_log:
        return "磁盘空间不足。请清理空间后再试。"

    if "could not write header" in lower_log or "muxer does not support" in lower_log:
        return "这个音频不能直接用复制模式切割。可以先转换成常见格式后再试。"

    if "non monoton" in lower_log or "timestamp" in lower_log:
        return "音频时间戳异常，FFmpeg 无法直接复制切割。可以先转换一次音频后再试。"

    return "FFmpeg 切割时返回了错误。"


def format_log_tail(lines: list[str]) -> str:
    useful_lines = [line.strip() for line in lines if line.strip()]
    tail = "\n".join(useful_lines[-12:])
    if len(tail) > 3000:
        tail = tail[-3000:]
    return tail


def run_ffmpeg_segment(ffmpeg: str, audio_path: Path, output_dir: Path) -> None:
    output_pattern = output_dir / f"{audio_path.stem}_part_%03d{audio_path.suffix.lower()}"

    command = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-i",
        str(audio_path),
        "-map",
        "0:a:0",
        "-c:a",
        "copy",
        "-f",
        "segment",
        "-segment_time",
        str(SEGMENT_SECONDS),
        "-segment_start_number",
        "1",
        "-reset_timestamps",
        "1",
        str(output_pattern),
    ]

    print("\n开始切割，请等待。")
    print(f"每段最长：{SEGMENT_SECONDS} 秒")
    print(f"输出文件夹：{output_dir}")
    print("模式：不重新编码，速度优先\n")

    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stderr_lines: list[str] = []
    last_time = None

    assert process.stderr is not None
    for line in process.stderr:
        stderr_lines.append(line)
        match = re.search(r"time=(\d+:\d+:\d+(?:\.\d+)?)", line)
        if match:
            last_time = match.group(1)
            print(f"\r处理中，已到音频时间：{last_time}", end="", flush=True)

    return_code = process.wait()
    if last_time:
        print()

    if return_code != 0:
        log_tail = format_log_tail(stderr_lines)
        reason = explain_ffmpeg_error("\n".join(stderr_lines))
        raise FriendlyError(f"{reason}\n\nFFmpeg 日志最后几行：\n{log_tail}")


def remove_empty_output_dir(output_dir: Path) -> None:
    if output_dir.exists() and not any(output_dir.iterdir()):
        try:
            output_dir.rmdir()
        except Exception:
            pass


def main() -> None:
    setup_console_encoding()

    print("Windows 长录音自动切割工具")
    print("--------------------------")

    audio_path = get_audio_path()
    ffmpeg = find_ffmpeg()
    output_dir = make_output_dir(audio_path)

    try:
        run_ffmpeg_segment(ffmpeg, audio_path, output_dir)
    except Exception:
        remove_empty_output_dir(output_dir)
        raise

    parts = sorted(output_dir.glob(f"{audio_path.stem}_part_*{audio_path.suffix.lower()}"))
    if not parts:
        raise FriendlyError("FFmpeg 已结束，但没有生成任何片段。请检查原音频是否为空。")

    print("\n完成。")
    print(f"生成片段数量：{len(parts)}")
    print(f"输出位置：{output_dir}")


if __name__ == "__main__":
    try:
        main()
    except FriendlyError as error:
        print("\n失败：")
        print(error)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已取消。")
        sys.exit(1)
    except Exception as error:
        print("\n发生未预期错误：")
        print(error)
        sys.exit(1)
