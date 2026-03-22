import os
import time
from urllib.parse import parse_qs, urlparse

from app.core.task_manager import task_manager

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class UserCancelledError(Exception):
    pass


AUDIO_CODEC_MAP = {
    "mp3": "mp3",
    "flac": "flac",
    "wav": "wav",
    "aac": "aac",
    "opus": "opus",
    "vorbis": "vorbis",
}

AUDIO_CONVERT_PRESETS = [
    ("Audio MP3 (192k)", "mp3"),
    ("Audio AAC (192k)", "aac"),
    ("Audio FLAC", "flac"),
]


def validate_url(url):
    if not url:
        return False
    value = url.lower()
    return "youtube.com" in value or "youtu.be" in value


def normalize_youtube_url(url, playlist_mode=False):
    raw = str(url or "").strip()
    if not raw:
        return raw
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    if "youtu.be" in host:
        video_id = parsed.path.strip("/")
        if not video_id:
            return raw
        if playlist_mode:
            return raw
        return f"https://www.youtube.com/watch?v={video_id}"
    if "youtube.com" not in host:
        return raw
    query = parse_qs(parsed.query or "")
    video_id = (query.get("v") or [None])[0]
    if playlist_mode:
        if video_id:
            playlist_id = (query.get("list") or [None])[0]
            if playlist_id:
                return f"https://www.youtube.com/watch?v={video_id}&list={playlist_id}"
            return f"https://www.youtube.com/watch?v={video_id}"
        return raw
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return raw


def proxy_string(proxy):
    proxy = proxy or {}
    ptype = str(proxy.get("type", "http")).strip().lower()
    host = str(proxy.get("host", "127.0.0.1")).strip()
    port = str(proxy.get("port", "7890")).strip()
    if ptype == "none":
        return None
    if ptype not in {"http", "socks5"}:
        raise ValueError("proxy type must be none/http/socks5")
    if not host or not port:
        raise ValueError("proxy host/port required")
    return f"{ptype}://{host}:{port}"


def format_duration(duration):
    if duration is None:
        return "unknown"
    try:
        total = int(duration)
    except (TypeError, ValueError):
        return "unknown"
    hours, remain = divmod(total, 3600)
    mins, secs = divmod(remain, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def format_size(size_bytes):
    if size_bytes is None:
        return "unknown"
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}PB"


def format_speed(bytes_per_sec):
    if not bytes_per_sec:
        return "unknown"
    return f"{format_size(bytes_per_sec)}/s"


def format_eta(seconds):
    if seconds is None:
        return "unknown"
    try:
        value = int(seconds)
    except (TypeError, ValueError):
        return "unknown"
    if value < 0:
        return "unknown"
    hours, remain = divmod(value, 3600)
    mins, secs = divmod(remain, 60)
    if hours:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def ensure_writable_download_path(path):
    target = os.path.abspath(path)
    os.makedirs(target, exist_ok=True)
    probe_name = f".ytdl_write_test_{int(time.time() * 1000)}"
    probe_path = os.path.join(target, probe_name)
    try:
        with open(probe_path, "wb") as fp:
            fp.write(b"ok")
    except OSError as exc:
        raise PermissionError(f"download path not writable: {target}, {exc}") from exc
    finally:
        try:
            if os.path.exists(probe_path):
                os.remove(probe_path)
        except OSError:
            pass


def resolve_output_template(download_path, output_template):
    template = str(output_template or "").strip() or "%(title).180B [%(id)s].%(ext)s"
    return os.path.join(download_path, template)


def language_name(language_code):
    mapping = {
        "zh": "中文",
        "zh-cn": "简体中文",
        "zh-tw": "繁體中文",
        "en": "English",
        "ja": "日本語",
        "ko": "한국어",
        "fr": "Français",
        "es": "Español",
    }
    key = str(language_code or "").strip().lower()
    return mapping.get(key, key or "unknown")


def normalize_info(info):
    if info.get("_type") == "playlist":
        entries = [entry for entry in (info.get("entries") or []) if entry]
        active = entries[0] if entries else {}
        return {
            "is_playlist": True,
            "playlist_title": info.get("title") or "unknown",
            "entry_count": len(entries),
            "active": active,
            "entries": entries,
        }
    return {
        "is_playlist": False,
        "playlist_title": "",
        "entry_count": 1,
        "active": info,
        "entries": [],
    }


def build_playlist_entries(entries):
    result = []
    for idx, item in enumerate(entries or [], start=1):
        if not item:
            continue
        result.append({
            "index": idx,
            "title": item.get("title") or f"item-{idx}",
            "duration_text": format_duration(item.get("duration")),
            "uploader": item.get("uploader") or "unknown",
        })
    return result


def build_playlist_items_option(selected_entries):
    values = []
    for item in selected_entries or []:
        try:
            index = int(item)
        except (TypeError, ValueError):
            continue
        if index > 0:
            values.append(index)
    if not values:
        return None
    values = sorted(set(values))
    return ",".join(str(x) for x in values)


def collect_recent_files(path, start_ts):
    files = []
    for root, _, names in os.walk(path):
        for name in names:
            if name.endswith((".part", ".ytdl")):
                continue
            file_path = os.path.join(root, name)
            try:
                stat = os.stat(file_path)
            except OSError:
                continue
            if stat.st_size <= 0:
                continue
            if stat.st_mtime + 0.5 < start_ts:
                continue
            files.append({
                "name": name,
                "path": os.path.abspath(file_path),
                "size_text": format_size(stat.st_size),
                "modified_at": stat.st_mtime,
            })
    files.sort(key=lambda x: x["modified_at"], reverse=False)
    return files


def build_format_options(active_info):
    options = [{
        "label": "Best Auto",
        "value": {
            "selector": "bestvideo*+bestaudio/best",
            "audio_codec": None,
            "kind": "video",
            "format_id": None,
        },
    }]
    formats = active_info.get("formats") or []
    video_formats = []
    for item in formats:
        if item.get("vcodec") == "none" or not item.get("format_id") or item.get("height") is None:
            continue
        video_formats.append(item)
    video_formats.sort(key=lambda x: (x.get("height") or 0, x.get("fps") or 0, x.get("tbr") or 0), reverse=True)
    seen = set()
    for item in video_formats:
        key = (item.get("height"), item.get("ext"), item.get("fps"), item.get("vcodec"), item.get("acodec") != "none")
        if key in seen:
            continue
        seen.add(key)
        format_id = item.get("format_id")
        has_audio = item.get("acodec") != "none"
        selector = format_id if has_audio else f"{format_id}+bestaudio/best"
        label = (
            f"{item.get('height')}p | {item.get('ext') or 'unknown'} | "
            f"{int(item.get('fps') or 0) if item.get('fps') else '-'}fps | "
            f"{'with audio' if has_audio else 'merge audio'} | "
            f"{format_size(item.get('filesize') or item.get('filesize_approx'))}"
        )
        options.append({
            "label": label,
            "value": {
                "selector": selector,
                "audio_codec": None,
                "kind": "video",
                "format_id": format_id,
            },
        })
        if len(options) >= 13:
            break
    for label, codec in AUDIO_CONVERT_PRESETS:
        options.append({
            "label": label,
            "value": {
                "selector": "bestaudio/best",
                "audio_codec": codec,
                "kind": "audio_only",
                "format_id": None,
            },
        })
    return options


def build_audio_track_options(active_info):
    options = [{"label": "Auto", "value": None}]
    seen = set()
    for item in active_info.get("formats") or []:
        if item.get("acodec") in (None, "none"):
            continue
        language = (item.get("language") or "").strip()
        acodec = item.get("acodec") or "unknown"
        abr = item.get("abr")
        format_id = item.get("format_id")
        ext = item.get("ext") or "unknown"
        if language:
            key = ("lang", language)
            if key in seen:
                continue
            seen.add(key)
            options.append({
                "label": f"{language_name(language)} ({language}) | {acodec} | {ext}",
                "value": {"mode": "language", "value": language},
            })
        elif format_id:
            key = ("id", format_id)
            if key in seen:
                continue
            seen.add(key)
            abr_text = f"{int(abr)}kbps" if abr else "unknown"
            options.append({
                "label": f"ID:{format_id} | {acodec} | {abr_text} | {ext}",
                "value": {"mode": "format_id", "value": format_id},
            })
        if len(options) >= 16:
            break
    return options


def build_subtitle_options(active_info):
    options = [{"label": "Off", "value": None}]
    subtitles = active_info.get("subtitles") or {}
    for lang, tracks in subtitles.items():
        if tracks:
            options.append({"label": f"{lang} (manual)", "value": {"lang": lang, "auto": False}})
    automatic = active_info.get("automatic_captions") or {}
    for lang, tracks in automatic.items():
        exists = any(opt["value"] and opt["value"].get("lang") == lang for opt in options)
        if tracks and not exists:
            options.append({"label": f"{lang} (auto)", "value": {"lang": lang, "auto": True}})
    return options


def build_audio_selector(audio_track_config):
    if not audio_track_config:
        return "bestaudio/best"
    mode = audio_track_config.get("mode")
    value = audio_track_config.get("value")
    if mode == "language" and value:
        return f"bestaudio[language={value}]/bestaudio/best"
    if mode == "format_id" and value:
        return f"{value}/bestaudio/best"
    return "bestaudio/best"


def build_download_selector(format_config, audio_track_config):
    format_config = format_config or {}
    base_selector = format_config.get("selector", "bestvideo*+bestaudio/best")
    if not audio_track_config:
        return base_selector
    audio_selector = build_audio_selector(audio_track_config)
    if format_config.get("kind") == "audio_only":
        return audio_selector
    format_id = format_config.get("format_id")
    if format_id:
        mode = audio_track_config.get("mode")
        value = audio_track_config.get("value")
        if mode == "language" and value:
            return f"{format_id}+bestaudio[language={value}]/{format_id}+bestaudio/{base_selector}"
        if mode == "format_id" and value:
            return f"{format_id}+{value}/{base_selector}"
        return f"{format_id}+{audio_selector}/{base_selector}"
    return f"bestvideo*+{audio_selector}/{base_selector}"


class YDLTaskLogger:
    def __init__(self, task_id, scene):
        self.task_id = task_id
        self.scene = scene

    def _emit(self, level, message):
        text = str(message or "").replace("\r", "").strip()
        if text:
            task_manager.append_log(self.task_id, f"[{self.scene}/{level}] {text}")

    def debug(self, msg):
        self._emit("debug", msg)

    def warning(self, msg):
        self._emit("warning", msg)

    def error(self, msg):
        self._emit("error", msg)


def fetch_info(url, playlist_mode=False, proxy=None):
    if not yt_dlp:
        raise RuntimeError("yt-dlp is not installed")
    ydl_opts = {
        "ignoreconfig": True,
        "noplaylist": not playlist_mode,
        "extract_flat": False,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
    }
    if not playlist_mode:
        ydl_opts["playlistend"] = 1
    proxy_value = proxy_string(proxy)
    if proxy_value:
        ydl_opts["proxy"] = proxy_value
    normalized_url = normalize_youtube_url(url, playlist_mode=playlist_mode)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(normalized_url, download=False)
    normalized = normalize_info(info)
    active = normalized["active"] or {}
    return {
        "title": active.get("title", "unknown"),
        "duration_text": format_duration(active.get("duration")),
        "uploader": active.get("uploader") or "unknown",
        "is_playlist": normalized["is_playlist"],
        "playlist_title": normalized["playlist_title"],
        "entry_count": normalized["entry_count"],
        "playlist_entries": build_playlist_entries(normalized["entries"]),
        "format_options": build_format_options(active),
        "audio_track_options": build_audio_track_options(active),
        "subtitle_options": build_subtitle_options(active),
    }


def run_download_task(task_id, payload):
    try:
        if not yt_dlp:
            raise RuntimeError("yt-dlp is not installed")
        url = str(payload.get("url", "")).strip()
        if not validate_url(url):
            raise ValueError("invalid youtube url")
        url = normalize_youtube_url(url, playlist_mode=bool(payload.get("playlist_mode", False)))
        path = str(payload.get("download_path", "")).strip()
        if not path:
            raise ValueError("download path required")
        ensure_writable_download_path(path)
        task_manager.update(task_id, status="running", status_text="running")
        task_manager.append_log(task_id, f"start: {url}")
        format_config = payload.get("selected_format")
        audio_track_config = payload.get("selected_audio_track")
        subtitle_config = payload.get("selected_subtitle")
        advanced = payload.get("advanced") or {}
        selected_entries = payload.get("selected_entries") or []
        selector = build_download_selector(format_config, audio_track_config)
        ydl_opts = {
            "ignoreconfig": True,
            "outtmpl": resolve_output_template(path, advanced.get("output_template")),
            "noplaylist": not bool(payload.get("playlist_mode", False)),
            "concurrent_fragment_downloads": int(advanced.get("concurrent_fragments") or 8),
            "socket_timeout": 20,
            "retries": int(advanced.get("retries") or 5),
            "format": selector,
            "merge_output_format": "mp4",
            "logger": YDLTaskLogger(task_id, "download"),
            "progress_with_newline": True,
            "windowsfilenames": os.name == "nt",
            "trim_file_name": 180,
            "writethumbnail": bool(advanced.get("write_thumbnail", False)),
            "writedescription": bool(advanced.get("write_description", False)),
            "writeinfojson": bool(advanced.get("write_infojson", False)),
        }
        rate_limit = str(advanced.get("rate_limit") or "").strip()
        if rate_limit:
            ydl_opts["ratelimit"] = rate_limit
        proxy_value = proxy_string(payload.get("proxy"))
        if proxy_value:
            ydl_opts["proxy"] = proxy_value
        postprocessors = []
        audio_codec = (format_config or {}).get("audio_codec")
        if audio_codec:
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": AUDIO_CODEC_MAP.get(audio_codec, audio_codec),
                "preferredquality": "192",
            })
        if bool(advanced.get("embed_metadata", False)):
            postprocessors.append({"key": "FFmpegMetadata"})
        if postprocessors:
            ydl_opts["postprocessors"] = postprocessors
        if subtitle_config:
            ydl_opts["writesubtitles"] = not subtitle_config.get("auto", False)
            ydl_opts["writeautomaticsub"] = subtitle_config.get("auto", False)
            ydl_opts["subtitleslangs"] = [subtitle_config["lang"]]
            ydl_opts["subtitlesformat"] = "best"
        playlist_items = build_playlist_items_option(selected_entries)
        if bool(payload.get("playlist_mode", False)) and playlist_items:
            ydl_opts["playlist_items"] = playlist_items
            task_manager.append_log(task_id, f"playlist items: {playlist_items}")

        def progress_hook(data):
            if task_manager.is_cancel_requested(task_id):
                raise UserCancelledError("cancelled")
            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                downloaded = data.get("downloaded_bytes") or 0
                speed = data.get("speed")
                eta = data.get("eta")
                percent = 0.0 if total <= 0 else max(0.0, min(100.0, downloaded * 100.0 / total))
                info = data.get("info_dict") or {}
                playlist_index = info.get("playlist_index")
                playlist_total = info.get("n_entries") or info.get("playlist_count") or info.get("playlist_size")
                try:
                    playlist_index = int(playlist_index) if playlist_index is not None else None
                except (TypeError, ValueError):
                    playlist_index = None
                try:
                    playlist_total = int(playlist_total) if playlist_total is not None else None
                except (TypeError, ValueError):
                    playlist_total = None
                ui_progress = percent
                prefix = ""
                if playlist_index and playlist_total:
                    ui_progress = ((playlist_index - 1) + (percent / 100.0)) / max(playlist_total, 1) * 100.0
                    ui_progress = max(0.0, min(100.0, ui_progress))
                    prefix = f"[{playlist_index}/{playlist_total}] "
                
                remaining_bytes = total - downloaded if total > 0 else 0
                status_text = (
                    f"{prefix}{percent:.1f}% | "
                    f"速度: {format_speed(speed)} | "
                    f"剩余: {format_size(remaining_bytes) if total > 0 else '未知'} | "
                    f"预估: {format_eta(eta)}"
                )
                task_manager.update(task_id, progress=ui_progress, status_text=status_text)
            elif status == "finished":
                task_manager.update(task_id, status_text="post-processing")
                task_manager.append_log(task_id, "download finished, post-processing")

        ydl_opts["progress_hooks"] = [progress_hook]
        start_ts = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if task_manager.is_cancel_requested(task_id):
            task_manager.update(task_id, status="cancelled", progress=0.0, status_text="cancelled")
            task_manager.append_log(task_id, "task cancelled")
            return
        files = collect_recent_files(path, start_ts)
        task_manager.update(task_id, status="success", progress=100.0, status_text="success", files=files)
        task_manager.append_log(task_id, f"task success, files: {len(files)}")
    except UserCancelledError:
        task_manager.update(task_id, status="cancelled", progress=0.0, status_text="cancelled")
        task_manager.append_log(task_id, "task cancelled")
    except Exception as exc:
        task_manager.update(task_id, status="error", status_text="error", error=str(exc))
        task_manager.append_log(task_id, f"task error: {exc}")
