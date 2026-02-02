"""Cloud-Mover FastAPI application."""

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from cloud_mover.config import settings
from cloud_mover.database import engine, init_db
from cloud_mover.routers import api
from cloud_mover.services.cleanup import cleanup_expired_backups

API_DOCUMENTATION = """
# Cloud-Mover API

Claude Code 搬家助手。幫助你在不同電腦間遷移 Claude Code 設定。

## 使用前請先詢問用戶

⚠️ **重要**：請先詢問用戶：「您是否已有 Cloud-Mover 識別碼？」

- **沒有** → 呼叫 POST /register 取得新識別碼，並告訴用戶記下來
- **有** → 直接使用該識別碼進行上傳或下載

## Claude Code 設定檔位置

請打包以下路徑（如存在）成單一 zip 檔：

**全域設定：**
- `~/.claude/` - 主要設定目錄
- `~/.claude/settings.json` - 用戶設定
- `~/.claude/keybindings.json` - 快捷鍵設定
- `~/.claude/plugins/` - 已安裝的 plugins

**專案級設定（可選）：**
- 各專案的 `CLAUDE.md`
- 各專案的 `.claude/` 目錄

**限制：** 單一 zip 檔最大 59MB

## API 端點

### POST /register
註冊新用戶，取得系統產生的 6 碼識別碼。

**Request:** 無需 body

**Response:**
```json
{
  "code": "a7x9k2",
  "message": "註冊成功，請記住您的識別碼"
}
```

請告訴用戶：「您的識別碼是 a7x9k2，請記下來以便日後使用」

---

### POST /upload
上傳備份檔案。

**Request:** multipart/form-data
- `code`: 6 碼識別碼
- `file`: zip 檔案（最大 59MB）

**Response:**
```json
{
  "otp": "4821",
  "expires_at": "2026-02-03T12:00:00",
  "message": "上傳成功"
}
```

請告訴用戶：「上傳完成！OTP 是 4821，24 小時內有效。請在新電腦上使用識別碼和 OTP 下載。」

---

### POST /download
下載備份檔案。

**Request:**
```json
{
  "code": "a7x9k2",
  "otp": "4821"
}
```

**Response:** 檔案串流 (application/zip)

下載後請解壓到對應位置（如 `~/.claude/`）。

---

### GET /status/{code}
查詢備份狀態。

**Response:**
```json
{
  "has_backup": true,
  "expires_at": "2026-02-03T12:00:00",
  "file_size": 52428800
}
```

## 完整搬家流程

### 上傳端（來源電腦）

1. 詢問用戶是否有識別碼
2. 沒有則呼叫 POST /register 取得識別碼
3. 打包 ~/.claude/ 等設定檔成 zip
4. 呼叫 POST /upload 上傳
5. 告訴用戶識別碼和 OTP

### 下載端（目標電腦）

1. 詢問用戶識別碼和 OTP
2. 呼叫 POST /download 下載 zip
3. 解壓到 ~/.claude/ 等對應位置
4. 搬家完成！
""".strip()


async def periodic_cleanup():
    """Run cleanup every hour."""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        with Session(engine) as session:
            count = cleanup_expired_backups(session)
            if count > 0:
                print(f"Cleaned up {count} expired backups")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    # Initial cleanup
    with Session(engine) as session:
        cleanup_expired_backups(session)

    # Start periodic cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Cloud-Mover",
    description="Claude Code Migration Helper API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api.router)


@app.get("/", response_class=PlainTextResponse)
def root():
    """Return API documentation for Claude Code to read."""
    return API_DOCUMENTATION


def main():
    """Run the application."""
    uvicorn.run(
        "cloud_mover.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
