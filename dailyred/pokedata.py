"""Gen 1-3 names (species, moves, abilities, items) and types from PokeAPI.

The names are used to recognise what's on the page, whatever the site's
markup looks like, and the types/dex numbers fill in the embeds.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "gen3.json"

# Gen 3 spellings that normalise differently from PokeAPI's modern names.
MOVE_ALIASES = {
    "faintattack": "Feint Attack",
    "hijumpkick": "High Jump Kick",
    "vicegrip": "Vise Grip",
    "smellingsalt": "Smelling Salts",
}
SPECIES_ALIASES = {
    "nidoranf": "Nidoran♀",
    "nidoranfemale": "Nidoran♀",
    "nidoranm": "Nidoran♂",
    "nidoranmale": "Nidoran♂",
}
ITEM_ALIASES = {}


def key(text: str) -> str:
    """Lowercase letters/digits only: "ThunderPunch" == "Thunder Punch"."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("♀", "f").replace("♂", "m").replace("é", "e").replace("É", "e")
    return re.sub(r"[^a-z0-9]", "", text.lower())


class PokeData:
    def __init__(self, raw: dict):
        self.pokemon = raw["pokemon"]
        self.by_name = {p["name"]: p for p in self.pokemon}
        self.species = self._index([p["name"] for p in self.pokemon], SPECIES_ALIASES)
        self.moves = self._index(raw["moves"], MOVE_ALIASES)
        self.abilities = self._index(raw["abilities"], {})
        self.items = self._index(raw["items"], ITEM_ALIASES)
        self.types = {key(t): t for p in self.pokemon for t in p["types"]}

    @staticmethod
    def _index(names, aliases):
        index = {key(n): n for n in names}
        index.update(aliases)
        return index

    def species_info(self, name: str) -> dict:
        return self.by_name[name]


@lru_cache(maxsize=1)
def load() -> PokeData:
    return PokeData(json.loads(DATA_FILE.read_text(encoding="utf-8")))
