# Cloud-Mover

繁體中文 | [English](README.md)

Claude Code 搬家助手 API 服務。

## 功能

- 上傳備份檔案，取得 6 碼驗證碼
- 使用驗證碼下載備份檔案
- 24 小時後自動刪除（檔案 + 記錄）

## 隱私保護

- 伺服器不儲存壓縮密碼，只有用戶知道
- 過期後完全刪除，不保留任何記錄
- 驗證碼僅用於識別檔案，無法解密內容

## 安裝

```bash
uv sync
```

## 設定

建立 `.env` 檔案：

```env
HOST=0.0.0.0
PORT=8080
BASE_URL=https://your-domain.com
MAX_FILE_SIZE_MB=59
EXPIRY_HOURS=24
```

## 啟動

```bash
uv run cloud-mover
```

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | API 使用說明（給 Claude Code 閱讀） |
| `/upload` | POST | 上傳備份，回傳驗證碼 |
| `/download/{code}` | GET | 使用驗證碼下載備份 |

## 授權

MIT
