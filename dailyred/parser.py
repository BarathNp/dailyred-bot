"""Turn the visible text of a team section into Pokémon.

This doesn't depend on the site's HTML/CSS (which can change with every
deploy). It walks the section's text line by line and recognises names from
the Gen 1-3 data: a species name starts a new Pokémon, and the move, ability
and item names after it belong to that Pokémon. Anything else (stats, labels,
buttons) is ignored. Showdown-style text ("Pikachu @ Light Ball",
"Ability: Static", "- Thunderbolt") works too.
"""

from __future__ import annotations

import re

from .models import Mon
from .pokedata import PokeData, key, load

TEAM_SIZE = 6
MAX_MOVES = 4

# Pieces of a line that never name anything: levels, labels, gender marks.
_NOISE = re.compile(
    r"\b(?:lv\.?|level|l)\s*100\b|\b(?:ability|item|held item|holds|moves?|type|types)\s*:?",
    re.IGNORECASE,
)
_SPLIT = re.compile(r"\s*(?:[•·|,;/@]|\s-\s|^-\s*|\n)\s*")


def _tokens(line: str) -> list[str]:
    line = _NOISE.sub(" ", line)
    return [t.strip(" .:-–—*()[]\t") for t in _SPLIT.split(line) if t and t.strip(" .:-–—*()[]\t")]


def _species_at_start(line: str, data: PokeData) -> str | None:
    """'Pikachu ♂ Lv. 100' -> 'Pikachu' (longest species name the line starts with)."""
    words = line.split()
    for n in range(min(3, len(words)), 0, -1):
        name = data.species.get(key(" ".join(words[:n])))
        if name:
            return name
    return None


def parse_section(text: str, data: PokeData | None = None, limit: int = TEAM_SIZE) -> list[Mon]:
    data = data or load()
    mons: list[Mon] = []
    seen_types: set[str] = set()
    current: Mon | None = None

    def start(name: str) -> bool:
        """Begin a new Pokémon. False once the team is full."""
        nonlocal current, seen_types
        if any(m.name == name for m in mons):
            # Teams never repeat a species, so this is the same card naming
            # it twice (title + label, alt text...): keep filling it in.
            return True
        if len(mons) >= limit:
            return False
        info = data.species_info(name)
        current = Mon(name=name, dex=info["id"], types=list(info["types"]))
        seen_types = set()
        mons.append(current)
        return True

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        is_move_line = line.startswith(("-", "–", "•"))
        tokens = _tokens(line)
        # A line that starts with a species ("Snorlax", "Snorlax ♂ Lv. 100",
        # "Pikachu @ Light Ball") begins a new Pokémon.
        first = _species_at_start(_NOISE.sub(" ", line), data)
        if first:
            if not start(first):
                break
            if tokens and key(tokens[0]).startswith(key(first)):
                tokens = tokens[1:]

        if current is None:
            continue

        for tok in tokens:
            k = key(tok)
            if not k:
                continue
            if k in data.species:
                # Another species later on the same line.
                if not start(data.species[k]):
                    return mons
                continue
            if k in data.abilities and current.ability is None:
                current.ability = data.abilities[k]
            elif k in data.items and current.item is None:
                current.item = data.items[k]
            elif (k in data.types and data.types[k] in current.types and k not in seen_types
                  and not is_move_line and not (current.moves or current.item or current.ability)):
                # "Psychic" right under Espeon's name is its type; later it's a move.
                seen_types.add(k)
            elif k in data.moves:
                move = data.moves[k]
                if move not in current.moves and len(current.moves) < MAX_MOVES:
                    current.moves.append(move)
    return mons
