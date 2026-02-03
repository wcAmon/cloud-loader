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
from cloud_mover.services.cleanup import cleanup_expired_backups, cleanup_expired_templates


def get_api_documentation() -> str:
    """Generate API documentation with current base_url."""
    return f"""# Cloud-Mover API

AI Assistant migration helper. Transfer settings between machines securely.

Service URL: {settings.base_url}
Max file size: {settings.max_file_size_mb}MB
Expiry: {settings.expiry_hours} hours

---

## Language

IMPORTANT: Always communicate with the user in their primary language.
Detect the user's language from their messages and respond in that language.
Technical commands (bash, paths) stay in English, but all explanations,
questions, and instructions should be in the user's language.

---

## Supported Tools

This service supports migration for multiple AI assistants:

| Tool | Config Location | Detected By |
|------|-----------------|-------------|
| Claude Code | `~/.claude/` | You are Claude Code |
| OpenClaw (Moltbot) | `~/.openclaw/` or `~/.moltbot/` | You are OpenClaw/Moltbot |
| Codex | `~/.codex/` | You are Codex |
| Other | Ask user | Unknown tool |

**Identify which tool you are, then follow the corresponding section below.**

---

## UPLOAD: Tool-Specific Data Collection

### If you are Claude Code

**Auto-collect these files:**
```bash
mkdir -p /tmp/backup/tool-config

# Settings and configs
cp ~/.claude/settings.json /tmp/backup/tool-config/ 2>/dev/null
cp ~/.claude/settings.local.json /tmp/backup/tool-config/ 2>/dev/null
cp ~/.claude/keybindings.json /tmp/backup/tool-config/ 2>/dev/null
cp ~/.claude/.clauderc /tmp/backup/tool-config/ 2>/dev/null
cp ~/.claude/.mcp.json /tmp/backup/tool-config/ 2>/dev/null
cp ~/.claude/mcp.json /tmp/backup/tool-config/ 2>/dev/null

# Directories
cp -r ~/.claude/projects/ /tmp/backup/tool-config/ 2>/dev/null
cp -r ~/.claude/statsig/ /tmp/backup/tool-config/ 2>/dev/null
cp -r ~/.claude/todos/ /tmp/backup/tool-config/ 2>/dev/null

# Plugins (exclude node_modules)
rsync -a --exclude='node_modules' ~/.claude/plugins/ /tmp/backup/tool-config/plugins/ 2>/dev/null
```

**Restore location:** `~/.claude/`
**Post-restore:** Run `npm install` in each plugin folder

---

### If you are OpenClaw (Moltbot)

**Auto-collect these files:**
```bash
mkdir -p /tmp/backup/tool-config

# Check which config exists
if [ -d ~/.openclaw ]; then
  CONFIG_DIR=~/.openclaw
  CONFIG_NAME="openclaw"
elif [ -d ~/.moltbot ]; then
  CONFIG_DIR=~/.moltbot
  CONFIG_NAME="moltbot"
elif [ -d ~/.clawdbot ]; then
  CONFIG_DIR=~/.clawdbot
  CONFIG_NAME="clawdbot"
fi

# Copy everything
cp "$CONFIG_DIR/$CONFIG_NAME.json" /tmp/backup/tool-config/ 2>/dev/null
cp -r "$CONFIG_DIR/skills/" /tmp/backup/tool-config/ 2>/dev/null
cp -r "$CONFIG_DIR/commands/" /tmp/backup/tool-config/ 2>/dev/null
cp -r "$CONFIG_DIR/memory/" /tmp/backup/tool-config/ 2>/dev/null

# Record which version for restore
echo "$CONFIG_NAME" > /tmp/backup/tool-config/.tool-version
```

**Restore location:** `~/.openclaw/` (or original location)
**Post-restore:** Run `openclaw doctor` to verify config

---

### If you are Codex

**Auto-collect these files:**
```bash
mkdir -p /tmp/backup/tool-config

# Config and sessions
cp ~/.codex/config.toml /tmp/backup/tool-config/ 2>/dev/null
cp -r ~/.codex/sessions/ /tmp/backup/tool-config/ 2>/dev/null
cp -r ~/.codex/profiles/ /tmp/backup/tool-config/ 2>/dev/null
```

**Restore location:** `~/.codex/`
**Post-restore:** Verify model settings in config.toml

---

### If you are another AI assistant

Ask the user:
> "I can help you migrate your settings to a new machine.
> Which folder contains your configuration? (e.g., ~/.your-tool/)"

Then pack that folder:
```bash
mkdir -p /tmp/backup/tool-config
cp -r ~/.your-tool/* /tmp/backup/tool-config/
```

---

## UPLOAD: Project Folders (All Tools)

Ask the user:

> "Which project folders do you want to include?
> (These will be packed entirely, excluding dependencies and large files)
>
> Options:
> 1. Current folder only
> 2. Search for project folders
> 3. I'll specify the folders
> 4. Skip - only pack tool settings"

**Search command (finds folders with AI assistant configs):**
```bash
find ~ -maxdepth 4 \\( -name "CLAUDE.md" -o -name "AGENTS.md" -o -name "codex.md" -o -type d -name ".claude" -o -type d -name ".codex" \\) 2>/dev/null | \\
  sed 's|/CLAUDE.md$||; s|/AGENTS.md$||; s|/codex.md$||; s|/.claude$||; s|/.codex$||' | sort -u | head -20
```

**Pack each selected project:**
```bash
rsync -a \\
  --exclude='node_modules' \\
  --exclude='.venv' \\
  --exclude='venv' \\
  --exclude='env' \\
  --exclude='.git' \\
  --exclude='__pycache__' \\
  --exclude='*.pyc' \\
  --exclude='.env' \\
  --exclude='*.bin' \\
  --exclude='*.model' \\
  --exclude='*.onnx' \\
  --exclude='*.pt' \\
  --exclude='*.pth' \\
  --exclude='*.safetensors' \\
  --exclude='*.gguf' \\
  --exclude='*.mp4' \\
  --exclude='*.mov' \\
  --exclude='*.avi' \\
  --exclude='*.mkv' \\
  --exclude='dist' \\
  --exclude='build' \\
  --exclude='.next' \\
  --exclude='target' \\
  /path/to/project/ /tmp/backup/projects/project-name/
```

---

## UPLOAD: Create INSTALL.md

Create `/tmp/backup/INSTALL.md`:

```markdown
# Migration Installation Guide

## Tool
[Your tool name]: [config location]

## Restore Steps
1. Extract to ~/restore/
2. Copy tool-config/ to [restore location]
3. [Tool-specific post-restore steps]

## Project Folders
| Folder | Original Path | Size |
|--------|---------------|------|
| ... | ... | ... |

## Security Reminders
- .env files were NOT included - recreate them
- Review any path-dependent configs (MCP servers, etc.)
```

---

## UPLOAD: Size Check

```bash
du -sh /tmp/backup/
```

If larger than {settings.max_file_size_mb}MB:
```bash
# Find large files
find /tmp/backup -type f -size +1M -exec ls -lh {{}} \\; | sort -k5 -hr | head -20

# Size by folder
du -sh /tmp/backup/*/ | sort -hr
```

**Reduce size by:**
1. Remove non-essential project folders
2. Add more exclusions to rsync
3. Remove large files found above

---

## UPLOAD: Zip and Upload

**Ask for password:**
> "Please set a password to protect your backup:"

**Create zip:**
```bash
cd /tmp/backup
zip -r -P "PASSWORD" ~/backup.zip .
```

**Upload:**
```
POST {settings.base_url}/upload
Content-Type: multipart/form-data
file: <zip file>
```

**Tell user:**
- Verification code: [6 chars from response]
- Zip password: [their password]
- Valid for: {settings.expiry_hours} hours

---

## DOWNLOAD: Get and Extract

**Ask user for:**
1. Verification code (6 alphanumeric)
2. Zip password

**Download:**
```bash
curl -o backup.zip {settings.base_url}/download/[CODE]
```

**Extract (Python - works on all systems):**
```bash
mkdir -p ~/restore
python3 -c "import zipfile, os; zipfile.ZipFile('backup.zip').extractall(os.path.expanduser('~/restore'), pwd=b'PASSWORD')"
```

**Alternative (unzip):**
```bash
unzip -P "PASSWORD" backup.zip -d ~/restore/
```

If unzip not installed:
- macOS: `brew install unzip` (or use Python above)
- Ubuntu/Debian: `sudo apt install unzip`
- Fedora/RHEL: `sudo dnf install unzip`
- Arch: `sudo pacman -S unzip`

---

## DOWNLOAD: Restore Tool Config

**Read INSTALL.md first:**
```bash
cat ~/restore/INSTALL.md
```

### Claude Code
```bash
[ -d ~/.claude ] && mv ~/.claude ~/.claude.backup.$(date +%s)
cp -r ~/restore/tool-config ~/.claude

# Install plugin dependencies
for dir in ~/.claude/plugins/*/; do
  [ -f "$dir/package.json" ] && (cd "$dir" && npm install)
done
```

### OpenClaw (Moltbot)
```bash
CONFIG_NAME=$(cat ~/restore/tool-config/.tool-version 2>/dev/null || echo "openclaw")
[ -d ~/.$CONFIG_NAME ] && mv ~/.$CONFIG_NAME ~/.$CONFIG_NAME.backup.$(date +%s)
mkdir -p ~/.$CONFIG_NAME
cp -r ~/restore/tool-config/* ~/.$CONFIG_NAME/

# Verify
openclaw doctor
```

### Codex
```bash
[ -d ~/.codex ] && mv ~/.codex ~/.codex.backup.$(date +%s)
cp -r ~/restore/tool-config ~/.codex
```

### Other
Follow instructions in INSTALL.md

---

## DOWNLOAD: Restore Project Folders

For each folder in `~/restore/projects/`:

> "Found project: `[name]`
> Original path: `[from INSTALL.md]`
>
> Where should I place it?
> 1. Same location
> 2. Different location
> 3. Skip"

```bash
cp -r ~/restore/projects/[name] /path/user/chose/
```

---

## DOWNLOAD: Final Steps

1. **Remind about .env files** - need to recreate
2. **Check path configs** - MCP servers, project paths may need adjustment
3. **Restart the tool** - to load new settings

---

## API Reference

### Migration Endpoints

#### POST /upload
Upload backup file, receive verification code.

**Request:** `multipart/form-data`, field `file` (max {settings.max_file_size_mb}MB)

**Response:**
```json
{{"code": "abc123", "expires_at": "2024-01-01T12:00:00Z", "message": "..."}}
```

#### GET /download/{{code}}
Download backup using verification code.

**Response:** `application/zip`

---

### Template Sharing Endpoints

Share CLAUDE.md or AGENTS.md templates with a simple code.

#### POST /templates
Share a template and receive a verification code.

**Request:**
```json
{{
  "template_type": "CLAUDE.md",
  "title": "FastAPI Backend Template",
  "description": "Best practices for FastAPI projects",
  "content": "# Project\\n\\n## Commands\\n..."
}}
```

- `template_type`: `"CLAUDE.md"` or `"AGENTS.md"`
- `title`: Template name (max 100 chars)
- `description`: Optional description (max 500 chars)
- `content`: Markdown content (max {settings.max_template_size_kb}KB)

**Response:**
```json
{{"code": "xyz789", "expires_at": "2024-01-08T12:00:00Z", "message": "..."}}
```

**Expiry:** {settings.template_expiry_days} days

#### GET /templates/{{code}}
Get template metadata and content as JSON.

**Response:**
```json
{{
  "code": "xyz789",
  "template_type": "CLAUDE.md",
  "title": "FastAPI Backend Template",
  "description": "Best practices for FastAPI projects",
  "content": "# Project\\n...",
  "content_size": 1234,
  "created_at": "2024-01-01T12:00:00Z",
  "expires_at": "2024-01-08T12:00:00Z",
  "download_count": 5
}}
```

#### GET /templates/{{code}}/raw
Get raw template content as plain text (for direct file download).

**Response:** `text/markdown` with `Content-Disposition: attachment`

---

### Errors

- 404: Code not found or expired
- 400: Invalid code format or request
""".strip()


async def periodic_cleanup():
    """Run cleanup every hour."""
    while True:
        await asyncio.sleep(3600)
        with Session(engine) as session:
            backup_count = cleanup_expired_backups(session)
            template_count = cleanup_expired_templates(session)
            if backup_count > 0:
                print(f"Cleaned up {backup_count} expired backups")
            if template_count > 0:
                print(f"Cleaned up {template_count} expired templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        cleanup_expired_backups(session)
        cleanup_expired_templates(session)

    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Cloud-Mover",
    description="AI Assistant Migration & Template Sharing API",
    version="0.4.0",
    lifespan=lifespan,
)

app.include_router(api.router)


@app.get("/", response_class=PlainTextResponse)
def root():
    """Return API documentation for AI assistants to read."""
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
