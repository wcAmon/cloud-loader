# Cloud-Mover

[繁體中文](README.zh-TW.md) | English

Claude Code migration helper API service.

## Features

- Upload backup files and receive a 6-character verification code
- Download backup files using the verification code
- Auto-delete after 24 hours (files + records)

## Privacy

- Server does not store zip passwords - only the user knows it
- Complete deletion after expiry - no records retained
- Verification code only identifies the file - cannot decrypt contents

## Installation

```bash
uv sync
```

## Configuration

Create a `.env` file:

```env
HOST=0.0.0.0
PORT=8080
BASE_URL=https://your-domain.com
MAX_FILE_SIZE_MB=59
EXPIRY_HOURS=24
```

## Run

```bash
uv run cloud-mover
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API documentation (for Claude Code to read) |
| `/upload` | POST | Upload backup, returns verification code |
| `/download/{code}` | GET | Download backup using verification code |

## License

MIT
