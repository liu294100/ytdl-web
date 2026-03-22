const state = {
  settings: null,
  info: null,
  taskId: null,
  timer: null,
  language: "zh-CN",
  playlistEntries: [],
  selectedEntries: [],
  files: []
};

const $ = (id) => document.getElementById(id);

function bind(id, event, handler) {
  const el = $(id);
  if (el) el.addEventListener(event, handler);
}

function t(key, fallback = "") {
  const dict = window.I18N_MAP[state.language] || window.I18N_MAP["zh-CN"] || {};
  return dict[key] || fallback || key;
}

function toast(message) {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  $("toastBox").appendChild(node);
  setTimeout(() => node.remove(), 2600);
}

function openModal(id) {
  $(id).classList.remove("hidden");
}

function closeModal(id) {
  $(id).classList.add("hidden");
}

function switchPanel(panelId) {
  document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
  document.querySelectorAll(".menu-btn").forEach((p) => p.classList.remove("active"));
  $(panelId).classList.add("active");
  document.querySelectorAll(`.menu-btn[data-target="${panelId}"]`).forEach((p) => p.classList.add("active"));
}

function refreshTopStats() {
  const isPlaylist = $("playlistMode").value === "true";
  $("statMode").textContent = isPlaylist ? t("playlistModeOption", "合集") : t("singleMode", "单视频");
  const total = state.playlistEntries.length;
  const selected = state.selectedEntries.length;
  $("statPlaylist").textContent = `${selected}/${total}`;
}

function selectedValue(selectId) {
  const raw = $(selectId).value;
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function fillSelect(selectEl, options) {
  selectEl.innerHTML = "";
  (options || []).forEach((item, idx) => {
    const opt = document.createElement("option");
    opt.textContent = item.label;
    opt.value = JSON.stringify(item.value);
    if (idx === 0) opt.selected = true;
    selectEl.appendChild(opt);
  });
}

function buildProxy() {
  return {
    type: $("proxyTypeSelect").value,
    host: $("proxyHostInput").value.trim(),
    port: $("proxyPortInput").value.trim()
  };
}

function applyI18n(lang) {
  const dict = window.I18N_MAP[lang] || window.I18N_MAP["zh-CN"];
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const key = node.dataset.i18n;
    if (dict[key]) node.textContent = dict[key];
  });
  document.documentElement.lang = lang;
}

async function loadLanguages() {
  const res = await fetch("/api/languages");
  const data = await res.json();
  const select = $("languageSelect");
  select.innerHTML = "";
  (data.items || []).forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.code;
    opt.textContent = item.name;
    select.appendChild(opt);
  });
}

async function loadSettings() {
  const res = await fetch("/api/settings");
  const settings = await res.json();
  state.settings = settings;
  $("downloadPathInput").value = settings.download_path || "";
  $("proxyTypeSelect").value = settings.proxy_type || "http";
  $("proxyHostInput").value = settings.proxy_host || "127.0.0.1";
  $("proxyPortInput").value = settings.proxy_port || "7890";
  $("languageSelect").value = settings.language || "zh-CN";
  state.language = settings.language || "zh-CN";
  applyI18n(state.language);
}

async function saveSettings() {
  const payload = {
    language: $("languageSelect").value,
    download_path: $("downloadPathInput").value.trim(),
    proxy_type: $("proxyTypeSelect").value,
    proxy_host: $("proxyHostInput").value.trim(),
    proxy_port: $("proxyPortInput").value.trim()
  };
  const res = await fetch("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (!res.ok) {
    toast(data.error || "save failed");
    return;
  }
  state.settings = data;
  state.language = data.language;
  applyI18n(state.language);
  toast(t("saved", "保存成功"));
  closeModal("settingsModal");
}

function renderPlaylistSummary() {
  if (!state.info?.is_playlist) {
    $("playlistSummary").textContent = "";
    return;
  }
  const total = state.playlistEntries.length;
  const selected = state.selectedEntries.length;
  $("playlistSummary").textContent = `${t("selectedCount", "已选")} ${selected}/${total}`;
  refreshTopStats();
}

function renderPlaylistItems() {
  const wrap = $("playlistItemsWrap");
  wrap.innerHTML = "";
  state.playlistEntries.forEach((item) => {
    const row = document.createElement("label");
    row.className = "playlist-item";
    row.innerHTML = `
      <div class="playlist-left">
        <input type="checkbox" data-index="${item.index}">
        <span class="playlist-title">${item.index}. ${item.title}</span>
      </div>
      <span>${item.duration_text}</span>
    `;
    row.querySelector("input").checked = state.selectedEntries.includes(item.index);
    wrap.appendChild(row);
  });
}

function applyPlaylistSelection() {
  const values = [];
  document.querySelectorAll("#playlistItemsWrap input[type='checkbox']").forEach((node) => {
    if (node.checked) values.push(Number(node.dataset.index));
  });
  state.selectedEntries = values.sort((a, b) => a - b);
  renderPlaylistSummary();
  closeModal("playlistModal");
}

async function fetchInfo() {
  const url = $("urlInput").value.trim();
  if (!url) {
    $("infoStatus").textContent = t("urlRequired", "请填写 URL");
    return;
  }
  $("infoStatus").textContent = t("loading", "加载中...");
  $("videoMeta").textContent = "";
  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        playlist_mode: $("playlistMode").value === "true",
        proxy: buildProxy()
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "fetch failed");
    state.info = data;
    fillSelect($("formatSelect"), data.format_options);
    fillSelect($("audioTrackSelect"), data.audio_track_options);
    fillSelect($("subtitleSelect"), data.subtitle_options);
    state.playlistEntries = data.playlist_entries || [];
    state.selectedEntries = state.playlistEntries.map((x) => x.index);
    $("choosePlaylistBtn").disabled = !data.is_playlist;
    renderPlaylistSummary();
    const lines = [];
    lines.push(`title: ${data.title}`);
    lines.push(`duration: ${data.duration_text}`);
    lines.push(`uploader: ${data.uploader}`);
    if (data.is_playlist) lines.push(`playlist: ${data.playlist_title} (${data.entry_count})`);
    $("videoMeta").textContent = lines.join("\n");
    $("infoStatus").textContent = "ok";
    toast(t("infoLoaded", "信息已更新"));
  } catch (err) {
    $("infoStatus").textContent = `error: ${err.message}`;
    toast(err.message);
  }
}

function advancedOptions() {
  return {
    output_template: $("outputTemplateInput").value.trim(),
    rate_limit: $("rateLimitInput").value.trim(),
    retries: $("retriesInput").value.trim(),
    concurrent_fragments: $("fragmentsInput").value.trim(),
    write_thumbnail: $("writeThumbnailCheck").checked,
    write_description: $("writeDescriptionCheck").checked,
    write_infojson: $("writeInfoJsonCheck").checked,
    embed_metadata: $("embedMetadataCheck").checked
  };
}

async function startDownload() {
  if (!state.info) {
    toast(t("fetchInfoFirst", "请先获取信息"));
    return;
  }
  if (state.info.is_playlist && state.selectedEntries.length === 0) {
    toast(t("needSelectPlaylist", "请先选择合集条目"));
    return;
  }
  const payload = {
    url: $("urlInput").value.trim(),
    download_path: $("downloadPathInput").value.trim(),
    playlist_mode: $("playlistMode").value === "true",
    selected_entries: state.info.is_playlist ? state.selectedEntries : [],
    selected_format: selectedValue("formatSelect"),
    selected_audio_track: selectedValue("audioTrackSelect"),
    selected_subtitle: selectedValue("subtitleSelect"),
    proxy: buildProxy(),
    advanced: advancedOptions()
  };
  const res = await fetch("/api/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (!res.ok) {
    toast(data.error || "task create failed");
    return;
  }
  state.taskId = data.task_id;
  $("taskIdText").textContent = `task: ${state.taskId}`;
  $("cancelTaskBtn").disabled = false;
  $("openFilesBtn").disabled = true;
  $("filesWrap").innerHTML = "";
  $("statTask").textContent = "running";
  openModal("taskModal");
  pollTask();
}

async function cancelTask() {
  if (!state.taskId) return;
  await fetch(`/api/tasks/${state.taskId}/cancel`, { method: "POST" });
  $("taskStatus").textContent = t("cancelRequested", "取消中...");
}

function stopPolling() {
  if (state.timer) clearTimeout(state.timer);
  state.timer = null;
  $("cancelTaskBtn").disabled = true;
}

async function loadTaskFiles() {
  if (!state.taskId) return;
  const res = await fetch(`/api/tasks/${state.taskId}/files`);
  const data = await res.json();
  if (!res.ok) return;
  state.files = data.items || [];
  const wrap = $("filesWrap");
  wrap.innerHTML = "";
  state.files.forEach((item) => {
    const row = document.createElement("div");
    row.className = "file-item";
    row.innerHTML = `
      <span class="file-title">${item.name}</span>
      <div class="action-row">
        <span>${item.size_text || ""}</span>
        <a class="btn btn-secondary" href="${item.download_url}">${t("download", "下载")}</a>
      </div>
    `;
    wrap.appendChild(row);
  });
  $("openFilesBtn").disabled = state.files.length === 0;
}

function downloadAllFiles() {
  if (!state.files || state.files.length === 0) return;
  const paths = state.files.map(f => {
    // extract path from download_url: /api/files/download?path=XXXX
    const url = new URL(f.download_url, window.location.origin);
    return `path=${encodeURIComponent(url.searchParams.get("path"))}`;
  });
  const a = document.createElement("a");
  a.href = `/api/files/download-all?${paths.join("&")}`;
  a.target = "_blank";
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

async function pollTask() {
  if (!state.taskId) return;
  try {
    const res = await fetch(`/api/tasks/${state.taskId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "task fetch failed");
    $("progressBar").style.width = `${Math.max(0, Math.min(100, Number(data.progress || 0)))}%`;
    $("taskStatus").textContent = `${data.status} | ${data.status_text || ""}`;
    $("statTask").textContent = data.status;
    $("logBox").textContent = (data.logs || []).join("\n");
    $("logBox").scrollTop = $("logBox").scrollHeight;
    if (["success", "error", "cancelled"].includes(data.status)) {
      stopPolling();
      if (data.status === "success") {
        await loadTaskFiles();
        if (state.files.length > 0) openModal("filesModal");
      }
      return;
    }
    state.timer = setTimeout(pollTask, 900);
  } catch (err) {
    $("taskStatus").textContent = `poll error: ${err.message}`;
    state.timer = setTimeout(pollTask, 1500);
  }
}

function bindEvents() {
  bind("languageSelect", "change", () => {
    state.language = $("languageSelect").value;
    applyI18n(state.language);
  });
  bind("menuSettingsBtn", "click", () => openModal("settingsModal"));

  bind("saveSettingsBtn", "click", saveSettings);
  bind("fetchInfoBtn", "click", fetchInfo);
  bind("startDownloadBtn", "click", () => openModal("confirmDownloadModal"));
  bind("confirmDownloadBtn", "click", () => {
    closeModal("confirmDownloadModal");
    startDownload();
  });
  bind("cancelTaskBtn", "click", cancelTask);
  bind("openTaskModalBtn", "click", () => {
    openModal("taskModal");
    if (state.taskId && !state.timer) {
      pollTask();
    }
  });
  bind("openFilesBtn", "click", async () => {
    await loadTaskFiles();
    openModal("filesModal");
  });
  bind("downloadAllFilesBtn", "click", downloadAllFiles);

  bind("changePathBtn", "click", () => {
    $("pathDraftInput").value = $("downloadPathInput").value;
    openModal("pathModal");
  });
  bind("applyPathBtn", "click", () => {
    $("downloadPathInput").value = $("pathDraftInput").value.trim();
    closeModal("pathModal");
  });

  bind("choosePlaylistBtn", "click", () => {
    renderPlaylistItems();
    openModal("playlistModal");
  });
  bind("selectAllPlaylistBtn", "click", () => {
    document.querySelectorAll("#playlistItemsWrap input[type='checkbox']").forEach((node) => {
      node.checked = true;
    });
  });
  bind("invertPlaylistBtn", "click", () => {
    document.querySelectorAll("#playlistItemsWrap input[type='checkbox']").forEach((node) => {
      node.checked = !node.checked;
    });
  });
  bind("applyPlaylistBtn", "click", applyPlaylistSelection);
  bind("playlistMode", "change", refreshTopStats);

  bind("closeSettingsBtn", "click", () => closeModal("settingsModal"));
  bind("closePathBtn", "click", () => closeModal("pathModal"));
  bind("closePlaylistBtn", "click", () => closeModal("playlistModal"));
  bind("closeFilesBtn", "click", () => closeModal("filesModal"));
  bind("closeConfirmDownloadBtn", "click", () => closeModal("confirmDownloadModal"));
  bind("closeTaskBtn", "click", () => closeModal("taskModal"));
}

async function bootstrap() {
  await loadLanguages();
  await loadSettings();
  bindEvents();
  $("infoStatus").textContent = "ready";
  $("taskStatus").textContent = "idle";
  $("statTask").textContent = "idle";
  refreshTopStats();
}

bootstrap();
