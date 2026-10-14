"""Runs the whole browser pipeline (headless Chromium, time zone, section
finding, parsing) against a local page with made-up markup.

It doesn't touch daily-red.com; for that run:  python -m dailyred.check
Skipped when Playwright or its Chromium isn't installed.
"""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

pytest.importorskip("playwright")

from dailyred.scraper import scrape  # noqa: E402

TEAM = [("Gengar", "Leftovers", "Levitate", ["Shadow Ball", "Thunderbolt"]),
        ("Lapras", "Mystic Water", "Water Absorb", ["Surf", "Ice Beam"]),
        ("Swampert", "Quick Claw", "Torrent", ["Earthquake", "Surf"]),
        ("Starmie", "Lum Berry", "Natural Cure", ["Psychic", "Thunder"]),
        ("Metagross", "Choice Band", "Clear Body", ["Meteor Mash", "Earthquake"]),
        ("Dragonite", "Leftovers", "Inner Focus", ["Dragon Claw", "Fire Blast"])]
RED = ["Pikachu", "Espeon", "Snorlax", "Venusaur", "Charizard", "Blastoise"]


def page_html() -> str:
    def card(name, item, ability, moves):
        lis = "".join(f"<li>{m}</li>" for m in moves)
        return (f'<div class="card"><img alt="{name}"><h3>{name}</h3><span class="item">{item}</span>'
                f'<span>{ability}</span><ul>{lis}</ul><small>HP 341 Atk 251</small></div>')
    team = "".join(card(*m) for m in TEAM)
    red = "".join(f"<div class='card'><h3>{n}</h3></div>" for n in RED)
    # Rendered by script, after a delay, the way a client-side app would be; it
    # also prints the date the browser thinks it is, to check the time zone.
    return f"""<!doctype html><html><body><div id="app"></div><script>
      setTimeout(() => {{
        const d = new Date();
        const ymd = d.getFullYear() + '-' + (d.getMonth()+1) + '-' + d.getDate();
        document.getElementById('app').innerHTML = `
          <header><h1>Daily Red No. 4</h1><p id="d">${{ymd}}</p><p>Today's team unlocks at midnight.</p></header>
          <section><h2>Today’s team</h2><div class="grid">{team}</div></section>
          <section><h2>Red's team</h2><div class="grid">{red}</div></section>
          <footer>Pikachu Espeon Snorlax</footer>`;
      }}, 300);
    </script></body></html>"""


def test_scrape_local_page(tmp_path):
    html = tmp_path / "index.html"
    html.write_text(page_html(), encoding="utf-8")
    at = datetime(2026, 10, 20, 23, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
    try:
        team = asyncio.run(scrape("Asia/Tokyo", "2026-10-20", url=html.as_uri(), at=at,
                                  dump_dir=tmp_path / "dump", timeout_ms=15_000))
    except Exception as exc:  # browser missing on this machine
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Playwright Chromium not installed")
        raise

    assert team.number == 4
    assert [m.name for m in team.team] == [m[0] for m in TEAM]
    assert team.team[0].item == "Leftovers" and team.team[0].ability == "Levitate"
    assert team.team[4].moves == ["Meteor Mash", "Earthquake"]
    assert [m.name for m in team.red] == RED
    # The browser ran in Tokyo time at the faked clock.
    assert "2026-10-20" in (tmp_path / "dump" / "page.txt").read_text(encoding="utf-8")
