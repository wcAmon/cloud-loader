# Cloud-Loader

繁體中文 | [English](README.md)

AI 助手服務 - 檔案傳輸、模板分享與知識追蹤。

**立即試用：** https://loader.land

## 功能

### 搬家（設定遷移）
- 上傳備份檔案，取得 6 碼驗證碼
- 在新機器下載備份
- 24 小時後自動刪除（檔案 + 記錄）
- 密碼保護的壓縮檔

### 模板分享
- 分享 CLAUDE.md 或 AGENTS.md 模板
- 簡單的 6 碼分享碼
- 模板 7 天後過期
- 下載次數追蹤

### 概念追蹤（新功能）
- 自動網路搜尋監控主題
- 使用 AI（Claude/OpenAI）建構知識圖譜
- 生成內容草稿（影片腳本、推文、文章）
- API 金鑰驗證的個人追蹤

## 快速開始

告訴 Claude Code：

```
幫我用 loader.land 搬家
```

Claude Code 會讀取 API 文檔並引導你完成流程。

## 支援的 AI 工具

| 工具 | 設定檔 | 搬家 | 模板 |
|------|--------|------|------|
| Claude Code | CLAUDE.md | ✅ | ✅ |
| OpenAI Codex | AGENTS.md | ✅ | ✅ |
| GitHub Copilot | AGENTS.md | - | ✅ |
| Cursor | .cursorrules | - | ✅ |
| OpenClaw (Moltbot) | ~/.openclaw/ | ✅ | - |

## API 端點

### 公開（無需認證）

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | API 文檔 |
| `/upload` | POST | 上傳備份，回傳驗證碼 |
| `/download/{code}` | GET | 下載備份 |
| `/templates` | POST | 分享模板，回傳分享碼 |
| `/templates/{code}` | GET | 取得模板（JSON） |
| `/templates/{code}/raw` | GET | 取得原始 Markdown |

### 需認證（API 金鑰）

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/auth/register` | POST | 取得新 API 金鑰 |
| `/api/auth/verify` | GET | 驗證 API 金鑰 |
| `/api/concepts` | GET/POST | 列出/建立概念 |
| `/api/concepts/{id}` | GET/PUT/DELETE | 管理概念 |
| `/api/concepts/{id}/run` | POST | 觸發搜尋 |
| `/api/concepts/{id}/snapshots` | GET | 列出快照 |

## 自架服務

### 需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 套件管理器

### 安裝

```bash
git clone https://github.com/wcAmon/cloud-loader.git
cd cloud-loader
uv sync
```

### 設定

建立 `.env` 檔案：

```env
HOST=0.0.0.0
PORT=8080
BASE_URL=https://your-domain.com
UPLOAD_DIR=./uploads
DATA_DIR=./data
MAX_FILE_SIZE_MB=59
EXPIRY_HOURS=24
TEMPLATE_EXPIRY_DAYS=7

# 概念追蹤（選用）
TAVILY_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### 啟動

```bash
uv run cloud-loader
```

### 使用 systemd

```ini
[Unit]
Description=Cloud-Loader API
After=network-online.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/cloud-loader
EnvironmentFile=/path/to/cloud-loader/.env
ExecStart=/home/your-user/.local/bin/uv run cloud-loader
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 反向代理（Caddy）

```
your-domain.com {
    reverse_proxy localhost:8080
}
```

## 隱私與安全

- 伺服器**不儲存**壓縮密碼，只有用戶知道
- 過期後完全刪除，不保留任何記錄
- 驗證碼僅用於識別檔案，無法解密內容
- 模板為公開（無密碼）但 7 天後過期
- 概念追蹤需要 API 金鑰，資料按用戶隔離

## 開發

```bash
# 安裝開發依賴
uv sync --group dev

# 執行測試
uv run pytest

# 開發模式（自動重載）
uv run uvicorn cloud_loader.main:app --reload
```

## 授權

MIT
