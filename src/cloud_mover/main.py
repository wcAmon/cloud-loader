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


def get_api_documentation() -> str:
    """Generate API documentation with current base_url."""
    return f"""# Cloud-Mover API

Claude Code 搬家助手。在不同電腦間遷移 Claude Code 設定。

服務網址：{settings.base_url}

---

## 上傳端（來源電腦）

你正在幫助用戶將 Claude Code 設定搬到新電腦。

### 步驟 1：準備安裝說明

建立 `INSTALL.md` 檔案，內容包含：
- 此備份包含哪些設定（settings.json、keybindings.json、plugins 等）
- 各檔案應該放置的位置
- plugins 需要的額外安裝步驟（如有）

範例 INSTALL.md：
```markdown
# Claude Code 搬家安裝說明

## 包含內容
- settings.json - 用戶設定
- keybindings.json - 快捷鍵設定
- plugins/ - 已安裝的 plugins

## 安裝步驟
1. 解壓縮到 ~/.claude/
2. 重啟 Claude Code

## plugins 說明
- my-plugin: 需要執行 `npm install` 安裝依賴
```

### 步驟 2：打包檔案

將以下內容打包成 zip（依實際存在的檔案）：
- `~/.claude/settings.json`
- `~/.claude/keybindings.json`
- `~/.claude/plugins/`
- `INSTALL.md`（你剛建立的）

**重要**：請用戶設定一個壓縮密碼保護檔案內容。

### 步驟 3：上傳

```
POST {settings.base_url}/upload
Content-Type: multipart/form-data
file: <zip 檔案>
```

回應：
```json
{{
  "code": "a7x9k2",
  "expires_at": "2026-02-04T12:00:00Z",
  "message": "上傳成功，請記住驗證碼"
}}
```

### 步驟 4：告知用戶

請告訴用戶：
- 驗證碼：`a7x9k2`（6 碼）
- 壓縮密碼：用戶自己設定的
- 有效期限：24 小時

用戶需要在新電腦上提供這兩組資訊。

---

## 下載端（目標電腦）

你正在幫助用戶從舊電腦接收 Claude Code 設定。

### 步驟 1：取得資訊

向用戶索取：
1. **驗證碼**（6 碼英數字）
2. **壓縮密碼**（用戶在舊電腦設定的）

### 步驟 2：下載

```
GET {settings.base_url}/download/{{code}}
```

回應：zip 檔案串流

### 步驟 3：解壓縮

使用用戶提供的壓縮密碼解壓縮檔案。

### 步驟 4：依照 INSTALL.md 安裝

讀取解壓後的 `INSTALL.md`，依照說明：
1. 將檔案放到正確位置（通常是 `~/.claude/`）
2. 執行必要的額外步驟（如 plugin 依賴安裝）
3. 提示用戶重啟 Claude Code

---

## API 參考

### POST /upload

上傳備份檔案，取得驗證碼。

**Request:** multipart/form-data
- `file`: zip 檔案（最大 {settings.max_file_size_mb}MB）

**Response:**
```json
{{
  "code": "a7x9k2",
  "expires_at": "2026-02-04T12:00:00Z",
  "message": "上傳成功，請記住驗證碼"
}}
```

### GET /download/{{code}}

使用驗證碼下載備份檔案。

**Response:** application/zip

**錯誤：**
- 400: 驗證碼格式錯誤
- 404: 驗證碼不存在或已過期
""".strip()


async def periodic_cleanup():
    """Run cleanup every hour."""
    while True:
        await asyncio.sleep(3600)
        with Session(engine) as session:
            count = cleanup_expired_backups(session)
            if count > 0:
                print(f"Cleaned up {count} expired backups")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        cleanup_expired_backups(session)

    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Cloud-Mover",
    description="Claude Code Migration Helper API",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(api.router)


@app.get("/", response_class=PlainTextResponse)
def root():
    """Return API documentation for Claude Code to read."""
    return get_api_documentation()


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
