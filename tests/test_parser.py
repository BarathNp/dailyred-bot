"""Parser tests on hand-written page text in a few plausible layouts.

These check the parsing logic only; they are not copies of daily-red.com.
Check against the live site with:  python -m dailyred.check
"""

from dailyred.parser import parse_section

CARDS = """
Today's team
Espeon
Psychic
Leftovers
Synchronize
Psychic
Shadow Ball
Morning Sun
Reflect
Nidoran♀ Lv. 100
Poison
Item: Quick Claw
Ability: Poison Point
Moves: Double Kick, Poison Sting, ThunderBolt, Faint Attack
Mr. Mime
Psychic
Choice Band · Soundproof
Psychic · Barrier · Hi Jump Kick · SolarBeam
Farfetch'd
Normal / Flying
King's Rock
Keen Eye
Swords Dance
Slash
Ho-Oh ♂
Fire / Flying
Lum Berry
Pressure
Sacred Fire
Charizard
Fire / Flying
Charcoal
Blaze
Flamethrower
Red's team
Pikachu
"""

SHOWDOWN = """
Pikachu @ Light Ball
Ability: Static
Level: 100
- Thunderbolt
- Quick Attack
- Iron Tail
- Thunder

Espeon @ Leftovers
Ability: Synchronize
- Psychic
- Morning Sun

Snorlax @ Chesto Berry
Ability: Immunity
- Body Slam
- Rest

Venusaur @ Miracle Seed
Ability: Overgrow
- Giga Drain
- Sleep Powder

Charizard @ Charcoal
Ability: Blaze
- Fire Blast
- Fly

Blastoise @ Mystic Water
Ability: Torrent
- Surf
- Ice Beam
"""


def by_name(mons):
    return {m.name: m for m in mons}


def test_card_layout():
    mons = parse_section(CARDS)
    assert [m.name for m in mons] == ["Espeon", "Nidoran♀", "Mr. Mime", "Farfetch’d", "Ho-Oh", "Charizard"]
    m = by_name(mons)
    # The first "Psychic" is Espeon's type, the second its move.
    assert m["Espeon"].types == ["Psychic"]
    assert m["Espeon"].item == "Leftovers" and m["Espeon"].ability == "Synchronize"
    assert m["Espeon"].moves == ["Psychic", "Shadow Ball", "Morning Sun", "Reflect"]
    # Gen 3 spellings map to the modern names.
    assert m["Nidoran♀"].moves == ["Double Kick", "Poison Sting", "Thunderbolt", "Feint Attack"]
    assert m["Mr. Mime"].item == "Choice Band" and m["Mr. Mime"].ability == "Soundproof"
    assert m["Mr. Mime"].moves == ["Psychic", "Barrier", "High Jump Kick", "Solar Beam"]
    assert m["Farfetch’d"].item == "King’s Rock"
    assert m["Ho-Oh"].moves == ["Sacred Fire"]
    assert m["Charizard"].dex == 6 and m["Charizard"].types == ["Fire", "Flying"]


def test_stops_after_six():
    # Red's Pikachu after the sixth Pokémon must not leak into today's team.
    assert len(parse_section(CARDS)) == 6


def test_showdown_export():
    mons = parse_section(SHOWDOWN)
    assert [m.name for m in mons] == ["Pikachu", "Espeon", "Snorlax", "Venusaur", "Charizard", "Blastoise"]
    pika = mons[0]
    assert pika.item == "Light Ball" and pika.ability == "Static"
    assert pika.moves == ["Thunderbolt", "Quick Attack", "Iron Tail", "Thunder"]
    assert by_name(mons)["Blastoise"].moves == ["Surf", "Ice Beam"]
    # "- Psychic" is a move here, not Espeon's type.
    assert by_name(mons)["Espeon"].moves == ["Psychic", "Morning Sun"]


def test_same_species_named_twice_in_one_card():
    text = "PIKACHU\nPikachu\nElectric\nLight Ball\nStatic\nThunderbolt"
    mons = parse_section(text)
    assert len(mons) == 1 and mons[0].moves == ["Thunderbolt"]


def test_gen3_types_from_data():
    mons = parse_section("Clefairy\nMarill\nGranbull")
    assert [m.types for m in mons] == [["Normal"], ["Water"], ["Normal"]]
