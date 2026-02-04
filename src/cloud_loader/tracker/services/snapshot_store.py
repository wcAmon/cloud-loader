"""Snapshot storage service for concept knowledge graphs."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from cloud_loader.config import settings


def _get_concept_dir(concept_id: int) -> Path:
    """Get the directory for a concept's snapshots."""
    path = settings.snapshots_dir / str(concept_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp_to_filename(ts: datetime) -> str:
    """Convert timestamp to filename."""
    return ts.strftime("%Y-%m-%dT%H-%M-%SZ") + ".json"


def _filename_to_timestamp(filename: str) -> datetime:
    """Convert filename to timestamp."""
    return datetime.strptime(filename.replace(".json", ""), "%Y-%m-%dT%H-%M-%SZ")


async def save_snapshot(concept_id: int, snapshot: dict) -> str:
    """Save a snapshot and update latest.json. Returns the relative path."""
    concept_dir = _get_concept_dir(concept_id)

    timestamp = datetime.utcnow()
    snapshot["timestamp"] = timestamp.isoformat() + "Z"
    snapshot["concept_id"] = concept_id

    # Count existing snapshots to determine version
    existing = list(concept_dir.glob("*.json"))
    existing = [f for f in existing if f.name != "latest.json"]
    snapshot["version"] = len(existing) + 1

    # Save timestamped file
    filename = _timestamp_to_filename(timestamp)
    filepath = concept_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    # Update latest.json (copy for quick access)
    latest_path = concept_dir / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    return str(filepath.relative_to(settings.snapshots_dir.parent))


async def get_snapshot(concept_id: int, timestamp: Optional[str] = None) -> Optional[dict]:
    """Get a snapshot by timestamp, or latest if not specified."""
    concept_dir = _get_concept_dir(concept_id)

    if timestamp is None or timestamp == "latest":
        filepath = concept_dir / "latest.json"
    else:
        filepath = concept_dir / f"{timestamp}.json"

    if not filepath.exists():
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


async def list_snapshots(concept_id: int) -> list[dict]:
    """List all snapshot timestamps for a concept."""
    concept_dir = _get_concept_dir(concept_id)

    snapshots = []
    for filepath in sorted(concept_dir.glob("*.json"), reverse=True):
        if filepath.name == "latest.json":
            continue

        ts = _filename_to_timestamp(filepath.name)
        snapshots.append({
            "timestamp": filepath.name.replace(".json", ""),
            "datetime": ts.isoformat() + "Z",
            "filename": filepath.name
        })

    return snapshots


async def get_previous_snapshot(concept_id: int) -> Optional[dict]:
    """Get the most recent snapshot for a concept."""
    snapshots = await list_snapshots(concept_id)
    if len(snapshots) < 1:
        return None

    latest_ts = snapshots[0]["timestamp"] if snapshots else None
    if latest_ts:
        return await get_snapshot(concept_id, latest_ts)
    return None
