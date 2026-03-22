import os
import base64
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from flask import Blueprint, current_app, jsonify, request, send_file

from app.core.i18n import SUPPORTED_LANGUAGES
from app.core.task_manager import task_manager
from app.services.downloader_service import fetch_info, run_download_task, validate_url

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    return jsonify({"ok": True, "yt_dlp_installed": bool(yt_dlp)})


@api_bp.get("/languages")
def languages():
    return jsonify({"items": SUPPORTED_LANGUAGES})


@api_bp.get("/settings")
def get_settings():
    repo = current_app.config["SETTINGS_REPO"]
    return jsonify(repo.get_settings())


@api_bp.put("/settings")
def update_settings():
    repo = current_app.config["SETTINGS_REPO"]
    payload = request.get_json(silent=True) or {}
    updated = repo.update_settings(payload)
    return jsonify(updated)


@api_bp.post("/info")
def info():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    if not validate_url(url):
        return jsonify({"error": "invalid youtube url"}), 400
    try:
        result = fetch_info(
            url=url,
            playlist_mode=bool(data.get("playlist_mode", False)),
            proxy=data.get("proxy"),
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api_bp.post("/download")
def download():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    if not validate_url(url):
        return jsonify({"error": "invalid youtube url"}), 400
    task_id = task_manager.create_task()
    task_manager.submit(task_id, run_download_task, data)
    return jsonify({"task_id": task_id})


@api_bp.get("/tasks/<task_id>")
def get_task(task_id):
    task = task_manager.get(task_id)
    if not task:
        return jsonify({"error": "task not found"}), 404
    return jsonify(task)


@api_bp.post("/tasks/<task_id>/cancel")
def cancel_task(task_id):
    ok = task_manager.cancel(task_id)
    if not ok:
        return jsonify({"error": "task not found"}), 404
    task_manager.append_log(task_id, "cancel requested")
    return jsonify({"ok": True})


@api_bp.get("/tasks/<task_id>/files")
def task_files(task_id):
    task = task_manager.get(task_id)
    if not task:
        return jsonify({"error": "task not found"}), 404
    items = []
    for idx, item in enumerate(task.get("files") or []):
        file_path = item.get("path", "")
        encoded_path = base64.urlsafe_b64encode(file_path.encode('utf-8')).decode('utf-8')
        items.append({
            "index": idx,
            "name": item.get("name"),
            "size_text": item.get("size_text"),
            "download_url": f"/api/files/download?path={encoded_path}",
        })
    return jsonify({"items": items})

@api_bp.get("/files/download")
def download_file_by_path():
    encoded_path = request.args.get("path")
    if not encoded_path:
        return jsonify({"error": "path required"}), 400
    try:
        file_path = base64.urlsafe_b64decode(encoded_path.encode('utf-8')).decode('utf-8')
        if not os.path.isfile(file_path):
            return jsonify({"error": "file not found"}), 404
        download_name = os.path.basename(file_path)
        return send_file(file_path, as_attachment=True, download_name=download_name)
    except Exception as exc:
        return jsonify({"error": "invalid path"}), 400

@api_bp.get("/tasks/<task_id>/files/<int:file_index>/download")
def download_task_file(task_id, file_index):
    files = task_manager.get_files(task_id)
    if files is None:
        return jsonify({"error": "task not found"}), 404
    if file_index < 0 or file_index >= len(files):
        return jsonify({"error": "file not found"}), 404
    file_item = files[file_index]
    file_path = file_item.get("path")
    if not file_path or not os.path.isfile(file_path):
        return jsonify({"error": "file not found"}), 404
    download_name = file_item.get("name") or os.path.basename(file_path)
    return send_file(file_path, as_attachment=True, download_name=download_name)


@api_bp.get("/files/download-all")
def download_all_by_paths():
    encoded_paths = request.args.getlist("path")
    if not encoded_paths:
        return jsonify({"error": "paths required"}), 400
    valid_files = []
    try:
        for enc in encoded_paths:
            file_path = base64.urlsafe_b64decode(enc.encode('utf-8')).decode('utf-8')
            if os.path.isfile(file_path):
                valid_files.append((file_path, os.path.basename(file_path)))
        if not valid_files:
            return jsonify({"error": "no valid files found"}), 404
        stream = BytesIO()
        with ZipFile(stream, mode="w", compression=ZIP_DEFLATED) as zf:
            for file_path, name in valid_files:
                zf.write(file_path, arcname=name)
        stream.seek(0)
        return send_file(stream, as_attachment=True, download_name="download.zip", mimetype="application/zip")
    except Exception as exc:
        return jsonify({"error": "invalid path"}), 400

@api_bp.get("/tasks/<task_id>/files/download-all")
def download_all_task_files(task_id):
    files = task_manager.get_files(task_id)
    if files is None:
        return jsonify({"error": "task not found"}), 404
    valid_files = []
    for item in files:
        file_path = item.get("path")
        if file_path and os.path.isfile(file_path):
            valid_files.append((file_path, item.get("name") or os.path.basename(file_path)))
    if not valid_files:
        return jsonify({"error": "file not found"}), 404
    stream = BytesIO()
    with ZipFile(stream, mode="w", compression=ZIP_DEFLATED) as zf:
        for file_path, name in valid_files:
            zf.write(file_path, arcname=name)
    stream.seek(0)
    return send_file(stream, as_attachment=True, download_name=f"{task_id}.zip", mimetype="application/zip")
