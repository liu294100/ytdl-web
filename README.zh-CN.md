# ytdl-web

[English](README.md) | 简体中文 | [日本語](README.ja.md)

一个基于 Flask 的 yt-dlp Web 下载工具。  
支持单视频与合集下载、任务进度跟踪、代理设置、多语言界面，以及浏览器本地下载文件。

## 项目介绍

- 后端：Flask + yt-dlp
- 前端：HTML/CSS/JavaScript
- 配置持久化：SQLite
- 任务状态：内存任务管理器
- 默认端口：`8000`

## 功能

- 获取视频/合集信息与可用格式
- 选择视频格式、音轨、字幕和高级参数
- 任务状态显示下载速度、剩余大小、预计时间
- 支持取消任务与查看任务日志
- 支持下载单文件或全部文件到本地
- 支持多语言界面（含中/英/日）
- 支持可选代理（`none/http/socks5`）

## 环境要求

- Python 3.8+
- `pip`
- 建议安装并配置 `ffmpeg` 到 PATH（用于合并/后处理）

## 安装

```bash
pip install -r requirements.txt
```

## 运行方式

### 方式 A：智能脚本启动（推荐）

Windows：

```bat
run.bat
```

- 自动扫描本机 Python
- 按数字选择解释器
- 启动 `app.py`

也可以直接指定序号：

```bat
run.bat 1
```

Linux/macOS：

```bash
chmod +x run.sh
./run.sh
```

### 方式 B：直接启动

```bash
python app.py
```

## 打开地址

启动后访问：

- 首页：`http://127.0.0.1:8000/`
- 健康检查：`http://127.0.0.1:8000/api/health`

## 使用步骤

1. 打开页面
2. 在设置里配置下载路径、代理、语言
3. 粘贴 YouTube 链接并获取信息
4. 选择格式与参数
5. 开始下载并查看任务状态
6. 下载生成文件到本地

## 常见提示

- 如果出现写入权限错误，请改用可写目录（例如 `D:\Downloads\yt`）。
- 对于标题较长或特殊字符较多的文件名，程序已做了更安全的 Windows 文件名处理。
