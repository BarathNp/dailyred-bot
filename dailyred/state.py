"""A small JSON file: which channel to post in (per server) and what was posted."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class State:
    def __init__(self, path: Path):
        self.path = path
        self.data = {"channels": {}, "posted": {}}
        if path.exists():
            self.data.update(json.loads(path.read_text(encoding="utf-8")))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        os.replace(tmp, self.path)  # atomic: a crash never leaves half a file

    # Channels set with /dailyred setchannel, by server id.
    def channels(self) -> dict[str, int]:
        return dict(self.data["channels"])

    def set_channel(self, guild_id: int, channel_id: int) -> None:
        self.data["channels"][str(guild_id)] = channel_id
        self.save()

    # Last date posted, by channel id.
    def posted(self, channel_id: int) -> str | None:
        return self.data["posted"].get(str(channel_id))

    def mark_posted(self, channel_id: int, date: str) -> None:
        self.data["posted"][str(channel_id)] = date
        self.save()
