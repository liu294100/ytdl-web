const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const http = require("http");

const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = process.env.YTDL_WEB_PORT || "18000";
const BASE_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

let backendProcess = null;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function waitForBackend(maxRetries = 60) {
  return new Promise(async (resolve, reject) => {
    for (let i = 0; i < maxRetries; i += 1) {
      const ok = await new Promise((innerResolve) => {
        const req = http.get(`${BASE_URL}/api/health`, (res) => {
          innerResolve(res.statusCode === 200);
        });
        req.on("error", () => innerResolve(false));
        req.setTimeout(1000, () => {
          req.destroy();
          innerResolve(false);
        });
      });
      if (ok) return resolve();
      await delay(500);
    }
    reject(new Error("backend startup timeout"));
  });
}

function resolveBackendCommand() {
  const env = {
    ...process.env,
    YTDL_WEB_HOST: BACKEND_HOST,
    YTDL_WEB_PORT: String(BACKEND_PORT)
  };
  if (app.isPackaged) {
    const baseDir = path.join(process.resourcesPath, "backend");
    const exeName = process.platform === "win32" ? "ytdl-web-backend.exe" : "ytdl-web-backend";
    const executable = path.join(baseDir, exeName);
    if (!fs.existsSync(executable)) {
      throw new Error(`backend not found: ${executable}`);
    }
    env.YTDL_WEB_DATA_DIR = path.join(baseDir, "data");
    return { command: executable, args: [], cwd: baseDir, env };
  }
  const projectRoot = path.resolve(__dirname, "..");
  return { command: "python", args: ["app.py"], cwd: projectRoot, env };
}

function startBackend() {
  const backend = resolveBackendCommand();
  backendProcess = spawn(backend.command, backend.args, {
    cwd: backend.cwd,
    env: backend.env,
    windowsHide: true,
    stdio: "ignore"
  });
  backendProcess.on("exit", () => {
    backendProcess = null;
  });
}

function stopBackend() {
  if (!backendProcess) return;
  backendProcess.kill();
  backendProcess = null;
}

async function createWindow() {
  startBackend();
  await waitForBackend();
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 1080,
    minHeight: 720,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  await win.loadURL(BASE_URL);
  win.show();
}

app.whenReady().then(async () => {
  try {
    await createWindow();
  } catch (err) {
    await dialog.showErrorBox("ytdl-web", String(err.message || err));
    app.quit();
  }
});

app.on("window-all-closed", () => {
  stopBackend();
  app.quit();
});

app.on("before-quit", () => {
  stopBackend();
});
