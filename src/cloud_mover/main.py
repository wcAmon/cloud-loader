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

Claude Code migration helper. Transfer Claude Code settings between machines.

Service URL: {settings.base_url}
Max file size: {settings.max_file_size_mb}MB
Expiry: {settings.expiry_hours} hours

---

## Upload (Source Machine)

You are helping the user transfer Claude Code settings to a new machine.

### Step 1: Analyze ~/.claude/ Directory

First, check what exists and calculate sizes:

```bash
# Check directory structure
ls -la ~/.claude/

# Calculate total size
du -sh ~/.claude/

# Check individual folder sizes
du -sh ~/.claude/*/
```

### Step 2: Ask User What to Include

Based on the analysis, ask the user what to include. Present options like:

**Typical contents to migrate:**
- `~/.claude/settings.json` - User settings (usually small)
- `~/.claude/keybindings.json` - Keyboard shortcuts (usually small)
- `~/.claude/plugins/` - Installed plugins (can be large)
- `~/.claude/projects/` - Project memories (can be large)
- `~/.claude/todos/` - Todo lists

**Often excluded (can be reinstalled or too large):**
- AI models or large binary files
- Cache directories
- Temporary files
- node_modules inside plugins (can reinstall with npm install)

If total size exceeds {settings.max_file_size_mb}MB, suggest:
1. Exclude large items that can be reinstalled (node_modules, models)
2. Only include essential config files
3. Handle plugins separately (just include plugin.json, reinstall deps on new machine)

### Step 3: Create INSTALL.md

Create an `INSTALL.md` with specific instructions based on what's included:

```markdown
# Claude Code Migration - Installation Guide

## Contents
[List exactly what files/folders are in this backup]

## Installation Steps
1. Extract to ~/.claude/ (or specific instructions)
2. [Any folder-specific steps]

## Post-Installation
- Run `cd ~/.claude/plugins/xxx && npm install` for plugins with dependencies
- Restart Claude Code
```

### Step 4: Ask User for Zip Password

Ask the user to provide a password to protect the zip file. This password is NOT stored on the server - only the user knows it.

### Step 5: Create Password-Protected Zip

Create the zip with the user's password:

```bash
# Install zip if needed (usually pre-installed)
# Create password-protected zip
zip -r -P "USER_PASSWORD" claude-backup.zip INSTALL.md [selected files/folders]
```

Or if using Python:
```python
import pyminizip
pyminizip.compress_multiple(files, prefixes, "backup.zip", "USER_PASSWORD", 5)
```

### Step 6: Upload

```
POST {settings.base_url}/upload
Content-Type: multipart/form-data
file: <zip file>
```

Response:
```json
{{
  "code": "a7x9k2",
  "expires_at": "2026-02-04T12:00:00Z",
  "message": "Upload successful, please remember your verification code"
}}
```

### Step 7: Tell User the Information

Tell the user clearly:
- **Verification code**: `a7x9k2` (6 characters) - for identifying the file on server
- **Zip password**: [the one they set] - for decrypting the contents
- **Valid for**: {settings.expiry_hours} hours

They need BOTH to restore on the new machine.

---

## Download (Target Machine)

You are helping the user receive Claude Code settings from their old machine.

### Step 1: Ask User for Credentials

Ask the user for:
1. **Verification code** (6 alphanumeric characters) - to find the file
2. **Zip password** (set on old machine) - to decrypt contents

### Step 2: Download

```
GET {settings.base_url}/download/{{code}}
```

Save the response as a zip file.

### Step 3: Extract with Password

```bash
unzip -P "USER_PASSWORD" claude-backup-xxx.zip -d ~/claude-restore/
```

### Step 4: Follow INSTALL.md

Read `INSTALL.md` from the extracted files and follow instructions exactly:
1. Copy files to correct locations
2. Run any post-install commands (npm install for plugins, etc.)
3. Verify permissions if needed

### Step 5: Prompt Restart

Tell the user to restart Claude Code to apply the new settings.

---

## Error Handling

**If zip creation fails due to size:**
- Re-analyze with `du -sh` to find large items
- Ask user which large items to exclude
- Suggest keeping only essential configs

**If upload fails (file too large):**
- Current limit is {settings.max_file_size_mb}MB
- Help user reduce size by excluding reinstallable items

**If download fails (code expired/invalid):**
- Ask user to verify the code
- Check if 24 hours have passed
- May need to re-upload from source machine

---

## API Reference

### POST /upload

Upload a backup file and receive a verification code.

**Request:** multipart/form-data
- `file`: zip file (max {settings.max_file_size_mb}MB)

**Response:**
```json
{{
  "code": "a7x9k2",
  "expires_at": "2026-02-04T12:00:00Z",
  "message": "Upload successful, please remember your verification code"
}}
```

### GET /download/{{code}}

Download a backup file using the verification code.

**Response:** application/zip

**Errors:**
- 400: Invalid verification code format
- 404: Verification code not found or expired
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
