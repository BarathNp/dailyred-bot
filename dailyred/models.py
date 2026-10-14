from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Mon:
    name: str
    dex: int
    types: list[str]
    item: str | None = None
    ability: str | None = None
    moves: list[str] = field(default_factory=list)

    @property
    def sprite(self) -> str:
        return sprite_url(self.dex)


@dataclass
class DailyTeam:
    date: str                 # YYYY-MM-DD in the configured time zone
    number: int | None        # "Daily Red No. X", if the site shows it
    team: list[Mon]
    red: list[Mon]
    source: str = "scrape"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DailyTeam":
        return cls(
            date=data["date"],
            number=data.get("number"),
            team=[Mon(**m) for m in data["team"]],
            red=[Mon(**m) for m in data["red"]],
            source=data.get("source", "scrape"),
        )


SPRITE_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"


def sprite_url(dex: int) -> str:
    return f"{SPRITE_BASE}/{dex}.png"
