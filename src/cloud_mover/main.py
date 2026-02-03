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

---

## Upload (Source Machine)

You are helping the user transfer Claude Code settings to a new machine.

### Step 1: Prepare Installation Instructions

Create an `INSTALL.md` file containing:
- What settings are included (settings.json, keybindings.json, plugins, etc.)
- Where each file should be placed
- Additional installation steps for plugins (if any)

Example INSTALL.md:
```markdown
# Claude Code Migration Installation Guide

## Contents
- settings.json - User settings
- keybindings.json - Keyboard shortcuts
- plugins/ - Installed plugins

## Installation Steps
1. Extract to ~/.claude/
2. Restart Claude Code

## Plugin Notes
- my-plugin: Run `npm install` to install dependencies
```

### Step 2: Package Files

Package the following into a zip (based on what exists):
- `~/.claude/settings.json`
- `~/.claude/keybindings.json`
- `~/.claude/plugins/`
- `INSTALL.md` (the one you just created)

**Important**: Ask the user to set a zip password to protect the contents.

### Step 3: Upload

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

### Step 4: Inform the User

Tell the user:
- Verification code: `a7x9k2` (6 characters)
- Zip password: the one they set
- Valid for: 24 hours

The user needs to provide both pieces of information on the new machine.

---

## Download (Target Machine)

You are helping the user receive Claude Code settings from their old machine.

### Step 1: Get Information

Ask the user for:
1. **Verification code** (6 alphanumeric characters)
2. **Zip password** (set by user on the old machine)

### Step 2: Download

```
GET {settings.base_url}/download/{{code}}
```

Response: zip file stream

### Step 3: Extract

Extract the file using the zip password provided by the user.

### Step 4: Follow INSTALL.md

Read the extracted `INSTALL.md` and follow the instructions:
1. Place files in the correct location (usually `~/.claude/`)
2. Run any additional steps (like plugin dependency installation)
3. Prompt the user to restart Claude Code

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
