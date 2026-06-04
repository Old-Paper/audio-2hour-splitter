# audio-2hour-splitter
Split long audio files into segments no longer than 2 hours.

# Audio 2-Hour Splitter

一个简单的长录音自动切割工具，可以把超长音频文件自动切割成多个片段，每个片段最长不超过 2 小时。

A simple tool for splitting long audio files into segments no longer than 2 hours.

## 功能特点

- 支持 mp3、m4a、wav、aac、flac 等常见音频格式
- 自动按 7200 秒，也就是 2 小时切割
- 自动创建输出文件夹
- 支持中文路径和空格路径
- 使用 FFmpeg 进行高速切割
- 优先不重新编码，尽量保持原始音质

## 适合谁使用

这个工具适合需要处理长录音的人，例如：

- 视频创作者
- 播客作者
- 课程录音整理
- 会议录音整理
- 字幕、转写、上传平台前的音频拆分

## 使用前准备

你需要先安装：

1. Python 3
2. FFmpeg

请确保在命令行中输入下面命令可以正常显示版本信息：

```bash
python --version
ffmpeg -version
