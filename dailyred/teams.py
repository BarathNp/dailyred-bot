"""Today's team, scraped once per day and cached on disk."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date as Date

from .config import Config
from .models import DailyTeam
from .scraper import scrape

log = logging.getLogger(__name__)


class TeamService:
    def __init__(self, config: Config):
        self.config = config
        self.cache_dir = config.state_dir / "teams"
        self._lock = asyncio.Lock()
        self._memory: dict[str, DailyTeam] = {}

    async def today(self) -> DailyTeam:
        date = self.config.today()
        async with self._lock:
            if date in self._memory:
                return self._memory[date]
            path = self.cache_dir / f"{date}.json"
            if path.exists():
                team = DailyTeam.from_dict(json.loads(path.read_text(encoding="utf-8")))
            else:
                log.info("fetching the team for %s (%s)", date, self.config.tz_name)
                team = await scrape(self.config.tz_name, date)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(team.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            if team.number is None and self.config.day_one:
                team.number = (Date.fromisoformat(date) - self.config.day_one).days + 1
            self._memory = {date: team}
            return team
