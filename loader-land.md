---
name: loader-land
description: Use when user mentions "loader.land", "cloud migration", "transfer settings to new machine", "share CLAUDE.md", "import template code", "track concepts", or needs to backup/restore AI assistant configurations. Provides authentication, file transfer, template sharing, and knowledge tracking services.
---

# Loader.land - AI Agent Services

This skill enables you to use loader.land services for:
- **Migration**: Transfer settings between machines
- **Templates**: Share/import CLAUDE.md and AGENTS.md files
- **Concept Tracking**: Monitor topics and build knowledge graphs

## Authentication

All services require an API key. Check if you already have one:

```bash
cat ~/.claude/loader.key 2>/dev/null
```

### First-time Setup

If no key exists, register:

```bash
# Register and save API key
API_RESPONSE=$(curl -s -X POST https://loader.land/api/auth/register)
API_KEY=$(echo "$API_RESPONSE" | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)
echo "$API_KEY" > ~/.claude/loader.key
chmod 600 ~/.claude/loader.key
echo "Registered! Your API key has been saved."
```

### Using Your API Key

For all authenticated requests:

```bash
API_KEY=$(cat ~/.claude/loader.key)
curl -H "Authorization: Bearer $API_KEY" https://loader.land/api/...
```

---

## Template Sharing (CLAUDE.md / AGENTS.md)

### Import a Template (User has a code)

```bash
# Get template info
curl https://loader.land/templates/[CODE]

# Download and save
curl https://loader.land/templates/[CODE]/raw -o CLAUDE.md
```

### Share a Template

1. Read the current CLAUDE.md
2. Ask user for title and optional description
3. Upload:

```bash
curl -X POST https://loader.land/templates \
  -H "Content-Type: application/json" \
  -d '{"template_type": "CLAUDE.md", "title": "My Template", "content": "..."}'
```

4. Give user the 6-character code (valid for 7 days)

---

## Migration: Full Settings Transfer

### UPLOAD (Source Machine)

1. **Collect tool config** based on which AI assistant you are:

**Claude Code:**
```bash
mkdir -p /tmp/backup/tool-config
cp ~/.claude/settings.json /tmp/backup/tool-config/ 2>/dev/null
cp ~/.claude/settings.local.json /tmp/backup/tool-config/ 2>/dev/null
cp ~/.claude/.clauderc /tmp/backup/tool-config/ 2>/dev/null
cp ~/.claude/.mcp.json /tmp/backup/tool-config/ 2>/dev/null
cp -r ~/.claude/projects/ /tmp/backup/tool-config/ 2>/dev/null
rsync -a --exclude='node_modules' ~/.claude/plugins/ /tmp/backup/tool-config/plugins/ 2>/dev/null
```

2. **Ask about project folders** (optional)
3. **Create INSTALL.md** with restore instructions
4. **Check size**: `du -sh /tmp/backup/`
5. **Ask user for password**
6. **Create zip and upload**:

```bash
cd /tmp/backup && zip -r -P "PASSWORD" ~/backup.zip .
API_KEY=$(cat ~/.claude/loader.key)
curl -X POST https://loader.land/upload \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@$HOME/backup.zip"
```

7. Give user: verification code + password reminder

### DOWNLOAD (Target Machine)

1. **Ensure API key exists** (register if needed)
2. **Ask for verification code and password**
3. **Download and extract**:

```bash
curl -o backup.zip https://loader.land/download/[CODE]
mkdir -p ~/restore
python3 -c "import zipfile, os; zipfile.ZipFile('backup.zip').extractall(os.path.expanduser('~/restore'), pwd=b'PASSWORD')"
```

4. **Restore tool config**:

```bash
[ -d ~/.claude ] && mv ~/.claude ~/.claude.backup.$(date +%s)
cp -r ~/restore/tool-config ~/.claude

# Install plugin dependencies
for dir in ~/.claude/plugins/*/; do
  [ -f "$dir/package.json" ] && (cd "$dir" && npm install)
done
```

5. **Restore projects** (ask user where to place each)
6. **Remind**: recreate .env files, check MCP paths, restart tool

---

## Concept Tracking (Knowledge Graphs)

Track topics over time with automatic web search and AI-powered knowledge graphs.

### List Concepts

```bash
API_KEY=$(cat ~/.claude/loader.key)
curl -H "Authorization: Bearer $API_KEY" https://loader.land/api/concepts
```

### Create Concept

```bash
curl -X POST https://loader.land/api/concepts \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Agent Development",
    "description": "Track progress in AI agent frameworks",
    "keywords": ["LangChain", "AutoGPT", "Claude"],
    "search_interval_hours": 24
  }'
```

### Get Latest Snapshot

```bash
curl -H "Authorization: Bearer $API_KEY" \
  https://loader.land/api/concepts/{id}/snapshots/latest
```

Returns:
- Knowledge graph (nodes + edges)
- Summary
- Source URLs
- Content draft suggestions

### Trigger Manual Run

```bash
curl -X POST -H "Authorization: Bearer $API_KEY" \
  https://loader.land/api/concepts/{id}/run
```

---

## API Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | No | Get new API key |
| `/api/auth/verify` | GET | Yes | Verify API key |
| `/upload` | POST | No | Upload backup zip |
| `/download/{code}` | GET | No | Download backup |
| `/templates` | POST | No | Share template |
| `/templates/{code}` | GET | No | Get template JSON |
| `/templates/{code}/raw` | GET | No | Get raw content |
| `/api/concepts` | GET | Yes | List concepts |
| `/api/concepts` | POST | Yes | Create concept |
| `/api/concepts/{id}` | GET/PUT/DELETE | Yes | Manage concept |
| `/api/concepts/{id}/run` | POST | Yes | Trigger search |
| `/api/concepts/{id}/snapshots` | GET | Yes | List snapshots |
| `/api/concepts/{id}/snapshots/{ts}` | GET | Yes | Get snapshot |

---

## Error Handling

- **401**: Invalid or missing API key
- **404**: Code not found or expired
- **400**: Invalid request format
- **413**: File too large (max 59MB for migration, 100KB for templates)
