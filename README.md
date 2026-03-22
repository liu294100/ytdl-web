# ytdl-web

English | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

A Flask-based web UI for yt-dlp.  
It supports single videos and playlists, task progress tracking, proxy settings, i18n UI, and browser-side file download.

## Project Overview

- Backend: Flask + yt-dlp
- Frontend: HTML/CSS/JavaScript
- Persistent settings: SQLite
- Runtime task state: in-memory task manager
- Default web port: `8000`

## Features

- Fetch video/playlist metadata and available formats
- Select video format, audio track, subtitles, and advanced download options
- Download progress with speed, remaining size, and ETA
- Cancel task and inspect task logs
- Download generated files in browser (single/all)
- Multilingual UI (including English / Chinese / Japanese)
- Optional proxy support (`none/http/socks5`)

## Requirements

- Python 3.8+
- `pip`
- `ffmpeg` available in PATH (recommended for merge/post-processing)

## Install

```bash
pip install -r requirements.txt
```

## Run

### Option A: Smart launcher script (recommended)

Windows:

```bat
run.bat
```

- Auto-detects local Python interpreters
- Lets you choose one by number
- Starts `app.py`

You can also pass an index directly:

```bat
run.bat 1
```

Linux/macOS:

```bash
chmod +x run.sh
./run.sh
```

### Option B: Run directly

```bash
python app.py
```

## Open in Browser

After startup:

- Home: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/api/health`

## Basic Usage

1. Open the web page
2. Configure download path / proxy / language in settings
3. Paste a YouTube URL and click fetch info
4. Choose format and options
5. Start download and monitor task status
6. Download generated files to local device

## Notes

- If you see write permission errors, use a writable folder (for example `D:\Downloads\yt` on Windows).
- For very long/special titles, the app uses safer filename handling on Windows.
