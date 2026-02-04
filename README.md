# Cloud-Loader

[繁體中文](README.zh-TW.md) | English

AI Agent Services - File Transfer, Template Sharing & Knowledge Tracking.

**Try it now:** https://loader.land

## Features

### Migration (Settings Transfer)
- Upload backup files with a 6-character verification code
- Download backups on your new machine
- Auto-delete after 24 hours (files + records)
- Password-protected zip files

### Template Sharing
- Share CLAUDE.md or AGENTS.md templates
- Simple 6-character code for sharing
- 7-day expiry for templates
- Download count tracking

### Concept Tracking (NEW)
- Monitor topics with automatic web search
- Build knowledge graphs with AI (Claude/OpenAI)
- Generate content drafts (video scripts, tweets, articles)
- API key authentication for personal tracking

## Quick Start with Claude Code

Tell Claude Code:

```
幫我用 loader.land 搬家
```

or

```
Help me migrate using loader.land
```

Claude Code will read the API documentation and guide you through the process.

## Supported AI Tools

| Tool | Config File | Migration | Template |
|------|-------------|-----------|----------|
| Claude Code | CLAUDE.md | ✅ | ✅ |
| OpenAI Codex | AGENTS.md | ✅ | ✅ |
| GitHub Copilot | AGENTS.md | - | ✅ |
| Cursor | .cursorrules | - | ✅ |
| OpenClaw (Moltbot) | ~/.openclaw/ | ✅ | - |

## API Endpoints

### Public (No Auth)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API documentation |
| `/upload` | POST | Upload backup, returns code |
| `/download/{code}` | GET | Download backup |
| `/templates` | POST | Share template, returns code |
| `/templates/{code}` | GET | Get template (JSON) |
| `/templates/{code}/raw` | GET | Get raw markdown |

### Authenticated (API Key Required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Get new API key |
| `/api/auth/verify` | GET | Verify API key |
| `/api/concepts` | GET/POST | List/create concepts |
| `/api/concepts/{id}` | GET/PUT/DELETE | Manage concept |
| `/api/concepts/{id}/run` | POST | Trigger search |
| `/api/concepts/{id}/snapshots` | GET | List snapshots |

## Self-Hosting

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
git clone https://github.com/wcAmon/cloud-loader.git
cd cloud-loader
uv sync
```

### Configuration

Create a `.env` file:

```env
HOST=0.0.0.0
PORT=8080
BASE_URL=https://your-domain.com
UPLOAD_DIR=./uploads
DATA_DIR=./data
MAX_FILE_SIZE_MB=59
EXPIRY_HOURS=24
TEMPLATE_EXPIRY_DAYS=7

# For Concept Tracking (optional)
TAVILY_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### Run

```bash
uv run cloud-loader
```

### Run with systemd

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

### Reverse Proxy (Caddy)

```
your-domain.com {
    reverse_proxy localhost:8080
}
```

## Privacy & Security

- Server does NOT store zip passwords - only users know them
- Complete deletion after expiry - no records retained
- Verification codes only identify files - cannot decrypt contents
- Templates are public (no password) but expire after 7 days
- Concept tracking requires API key - data is per-user

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run with auto-reload (development)
uv run uvicorn cloud_loader.main:app --reload
```

## License

MIT
