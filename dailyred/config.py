from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    token: str
    channel_id: int | None
    tz: ZoneInfo
    post_time: time          # tz-aware, in `tz`
    state_dir: Path
    day_one: date | None     # date of "Daily Red No. 1", if the site doesn't show the number

    @property
    def tz_name(self) -> str:
        return self.tz.key

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def today(self) -> str:
        return self.now().date().isoformat()

    def next_midnight(self) -> datetime:
        tomorrow = self.now().date() + timedelta(days=1)
        return datetime.combine(tomorrow, time(0, 0), self.tz)

    def next_post(self) -> datetime:
        now = self.now()
        at = datetime.combine(now.date(), self.post_time.replace(tzinfo=None), self.tz)
        return at if at > now else datetime.combine(now.date() + timedelta(days=1),
                                                     self.post_time.replace(tzinfo=None), self.tz)

    def post_time_passed(self) -> bool:
        now = self.now()
        return now >= datetime.combine(now.date(), self.post_time.replace(tzinfo=None), self.tz)


def parse_post_time(value: str, tz: ZoneInfo) -> time:
    try:
        hour, minute = (int(part) for part in value.strip().split(":"))
        return time(hour, minute, tzinfo=tz)
    except ValueError as exc:
        raise ConfigError(f"POST_TIME must look like 09:00 (24-hour), got {value!r}") from exc


def load_config(require_token: bool = True) -> Config:
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if require_token and not token:
        raise ConfigError("DISCORD_TOKEN is missing. Copy .env.example to .env and paste your bot token.")

    tz_name = os.getenv("TZ", "").strip() or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception as exc:  # noqa: BLE001 - ZoneInfo raises several types
        raise ConfigError(f"TZ must be a time zone name like America/New_York, got {tz_name!r}") from exc

    channel = os.getenv("CHANNEL_ID", "").strip()
    if channel and not channel.isdigit():
        raise ConfigError(f"CHANNEL_ID must be a number, got {channel!r}")

    day_one = os.getenv("DAILYRED_DAY_ONE", "").strip()
    return Config(
        token=token,
        channel_id=int(channel) if channel else None,
        tz=tz,
        post_time=parse_post_time(os.getenv("POST_TIME", "09:00"), tz),
        state_dir=Path(os.getenv("STATE_DIR", "state")),
        day_one=date.fromisoformat(day_one) if day_one else None,
    )
