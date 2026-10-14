"""Rebuild dailyred/data/gen3.json from PokeAPI's CSV data.

You only need this if you want to refresh the bundled data; the bot ships with
the JSON already built.

    python tools/build_data.py            # downloads the CSVs from GitHub
    python tools/build_data.py CSV_DIR    # or reads them from a local folder
"""

import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

CSV_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/{}.csv"
OUT = Path(__file__).resolve().parent.parent / "dailyred" / "data" / "gen3.json"
ENGLISH = "9"
GEN3_ITEM_GENERATION = "3"


def load(name, folder=None):
    if folder:
        text = (Path(folder) / f"{name}.csv").read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(CSV_URL.format(name)) as resp:
            text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def english_names(rows, id_key):
    return {r[id_key]: r["name"] for r in rows if r["local_language_id"] == ENGLISH}


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else None
    type_names = english_names(load("type_names", folder), "type_id")

    # Species 1-386 with their Gen 3 types (Fairy didn't exist yet, so
    # pokemon_types_past overrides e.g. Clefairy back to Normal).
    species_names = english_names(load("pokemon_species_names", folder), "pokemon_species_id")
    types = {}
    for r in load("pokemon_types", folder):
        if int(r["pokemon_id"]) <= 386:
            types.setdefault(r["pokemon_id"], {})[int(r["slot"])] = r["type_id"]
    past = {}
    for r in load("pokemon_types_past", folder):
        # The newest entry with generation_id > 3 describes types up to that gen.
        if int(r["pokemon_id"]) <= 386 and int(r["generation_id"]) > 3:
            gen = int(r["generation_id"])
            entry = past.setdefault(r["pokemon_id"], {"gen": gen, "slots": {}})
            if gen < entry["gen"]:
                entry.update(gen=gen, slots={})
            if gen == entry["gen"]:
                entry["slots"][int(r["slot"])] = r["type_id"]
    for pid, entry in past.items():
        types[pid] = entry["slots"]

    pokemon = []
    for i in range(1, 387):
        pid = str(i)
        pokemon.append({
            "id": i,
            "name": species_names[pid],
            "types": [type_names[types[pid][s]] for s in sorted(types[pid])],
        })

    move_names = english_names(load("move_names", folder), "move_id")
    moves = sorted(move_names[r["id"]] for r in load("moves", folder)
                   if int(r["generation_id"]) <= 3 and r["id"] in move_names)

    ability_names = english_names(load("ability_names", folder), "ability_id")
    abilities = sorted(ability_names[r["id"]] for r in load("abilities", folder)
                       if r["is_main_series"] == "1" and int(r["generation_id"]) <= 3)

    item_names = english_names(load("item_names", folder), "item_id")
    gen3_items = {r["item_id"] for r in load("item_game_indices", folder)
                  if r["generation_id"] == GEN3_ITEM_GENERATION}
    items = sorted(item_names[i] for i in gen3_items if i in item_names)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "PokeAPI (https://github.com/PokeAPI/pokeapi), CC BY-NC-SA / BSD data",
        "pokemon": pokemon,
        "moves": moves,
        "abilities": abilities,
        "items": items,
    }, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"wrote {OUT}: {len(pokemon)} pokemon, {len(moves)} moves, "
          f"{len(abilities)} abilities, {len(items)} items")


if __name__ == "__main__":
    main()
