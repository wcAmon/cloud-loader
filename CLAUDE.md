# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Commands

```bash
uv run cloud-loader                    # Start API server
uv run uvicorn cloud_loader.main:app --reload  # Dev server with auto-reload
uv run pytest                          # Run all tests
uv run pytest tests/test_api.py::test_full_upload_download_flow  # Run single test
```

## Architecture

Cloud-Loader provides these services:
1. **File Transfer** (`/upload`, `/download`): Migrate settings with 6-char verification codes, 24h expiry
2. **MD Storage** (`/md`): Store any MD file with metadata (filename, purpose, install_path), permanent
3. **Agent Hub** (`/hub`): Unified dashboard for Midnight + Dusk agents
4. **Dusk Agent** (`/dusk`): Autonomous agent managing loader.land ecosystem

### API Design

- Root `/` returns plain text documentation for AI agents, redirects browsers to `/human`
- Anonymous: `/upload`, `/download/{code}`, `/md`, `/md/{code}`, `/md/{code}/raw`
- Agent Hub: `/hub` (unified), `/dusk` (Dusk dashboard)
- Verification codes: 6 alphanumeric chars, validated via `services/auth.py:is_valid_code()`

### Testing Pattern

Tests use SQLite in-memory database and dependency injection:
```python
app.dependency_overrides[get_session] = get_session_override
```

### Key Behaviors

- Backups: 24h expiry, 59MB max (`EXPIRY_HOURS`, `MAX_FILE_SIZE_MB`)
- MD Storage: 7-day expiry, 100KB max (`TEMPLATE_EXPIRY_DAYS`)
- Cleanup task runs hourly via `asyncio.create_task()` in lifespan
- All datetimes use UTC via `datetime.now(timezone.utc)`

### Environment Variables

```bash
HOST=0.0.0.0
PORT=8080
BASE_URL=https://loader.land
UPLOAD_DIR=./uploads
DATA_DIR=./data
MAX_FILE_SIZE_MB=59
EXPIRY_HOURS=24
TEMPLATE_EXPIRY_DAYS=7
TAVILY_API_KEY=      # For Dusk agent web search
```
