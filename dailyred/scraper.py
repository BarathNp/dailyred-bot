"""Read today's team and Red's team from daily-red.com with headless Chromium.

The site builds the team in the browser from the visitor's local date, so we
open it in a browser set to the bot's time zone and read what it shows.

How the sections are found (so a CSS/markup change on the site doesn't break
the bot): we look for the "Today's team" and "Red's team" headings, walk up
from each heading to the smallest element that contains at least six
Pokémon names, and hand that element's text to parser.parse_section.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path

from . import SITE_URL
from .models import DailyTeam, Mon
from .parser import TEAM_SIZE, parse_section
from .pokedata import load

log = logging.getLogger(__name__)

TODAY_HEADING = r"today[’']?s\s+team"
RED_HEADING = r"red[’']?s\s+team"

# Red's team never changes (the site says so); used only if his section can't be read.
RED_SPECIES = ["Pikachu", "Espeon", "Snorlax", "Venusaur", "Charizard", "Blastoise"]

# Runs in the page. Returns {today: {text, offset}, red: {...}, body: "..."}.
_FIND_SECTIONS_JS = r"""
([patterns, speciesKeys, minSpecies]) => {
  const keyOf = (s) => s.toLowerCase().replace(/♀/g, 'f').replace(/♂/g, 'm')
                        .normalize('NFKD').replace(/[^a-z0-9]/g, '');
  const species = new Set(speciesKeys);
  const countSpecies = (text) => {
    const found = new Set();
    for (const line of text.split(/\n/)) {
      const words = line.trim().split(/\s+/);
      for (let n = Math.min(3, words.length); n > 0; n--) {
        const k = keyOf(words.slice(0, n).join(' '));
        if (species.has(k)) { found.add(k); break; }
      }
    }
    return found.size;
  };
  const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  // Every visible text node on its own line. Unlike innerText this keeps
  // <span>Leftovers</span><span>Levitate</span> apart.
  const textOf = (root) => {
    const lines = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (n.nodeType === Node.ELEMENT_NODE) {
        // Alt text, for cards that show a sprite instead of a name.
        if (n.tagName === 'IMG' && n.alt && visible(n)) lines.push(n.alt.trim());
        continue;
      }
      const parent = n.parentElement;
      if (!parent || /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(parent.tagName) || !visible(parent)) continue;
      const t = n.textContent.replace(/\s+/g, ' ').trim();
      if (t) lines.push(t);
    }
    return lines.join('\n');
  };
  const result = { body: textOf(document.body) };
  for (const [name, source] of Object.entries(patterns)) {
    const re = new RegExp(source, 'i');
    // Elements whose (short) text is the heading.
    const headings = [...document.querySelectorAll('body *')].filter((el) =>
      visible(el) && el.textContent.trim().length <= 60 && re.test(el.textContent));
    let best = null;
    for (const h of headings) {
      let node = h;
      while (node && node !== document.body && countSpecies(textOf(node)) < minSpecies) {
        node = node.parentElement;
      }
      if (!node) continue;
      const text = textOf(node);
      const match = text.search(re);
      const candidate = { text, offset: Math.max(match, 0), size: text.length };
      if (!best || candidate.size < best.size) best = candidate;
    }
    result[name] = best;
  }
  return result;
}
"""

_NUMBER_PATTERNS = [
    re.compile(r"daily\s*red\s*(?:no\.?|#|day)\s*(\d{1,5})", re.IGNORECASE),
    re.compile(r"\bno\.\s*(\d{1,5})\b", re.IGNORECASE),
]


class ScrapeError(RuntimeError):
    pass


def _section_text(found: dict | None, body: str, heading: str) -> str:
    if found:
        return found["text"][found["offset"]:]
    match = re.search(heading, body, re.IGNORECASE)
    return body[match.start():] if match else ""


def find_number(body: str) -> int | None:
    for pattern in _NUMBER_PATTERNS:
        match = pattern.search(body)
        if match:
            return int(match.group(1))
    return None


def build_team(date: str, today_text: str, red_text: str, body: str) -> DailyTeam:
    data = load()
    team = parse_section(today_text, data)
    if len(team) < TEAM_SIZE:
        raise ScrapeError(f"found {len(team)} of today's {TEAM_SIZE} Pokémon on the page")
    red = parse_section(red_text, data) if red_text else []
    if len(red) < TEAM_SIZE:
        log.warning("Red's section read as %s; using his fixed lineup (species only)",
                    [m.name for m in red])
        red = [Mon(name=n, dex=data.species_info(n)["id"], types=list(data.species_info(n)["types"]))
               for n in RED_SPECIES]
    return DailyTeam(date=date, number=find_number(body), team=team, red=red)


async def scrape(timezone: str, date: str, *, url: str = SITE_URL, at: datetime | None = None,
                 dump_dir: Path | None = None, timeout_ms: int = 45_000) -> DailyTeam:
    """Open the site in a browser set to `timezone` and read the teams.

    `at` (optional, timezone-aware) fakes the browser clock, e.g. to read
    tomorrow's team. `dump_dir` saves the page HTML, text and a screenshot,
    which is how you'd debug the parser if the site changes.
    """
    from playwright.async_api import async_playwright

    data = load()
    patterns = {"today": TODAY_HEADING, "red": RED_HEADING}
    launch = {"headless": True}
    if os.getenv("CHROMIUM_PATH"):
        launch["executable_path"] = os.environ["CHROMIUM_PATH"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch)
        try:
            context = await browser.new_context(timezone_id=timezone, locale="en-US",
                                                viewport={"width": 1280, "height": 2000})
            page = await context.new_page()
            if at is not None:
                await page.clock.set_system_time(at)
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                await page.get_by_text(re.compile(TODAY_HEADING, re.IGNORECASE)).first.wait_for(timeout=timeout_ms)
            except Exception as exc:  # noqa: BLE001 - re-raised with context below
                if dump_dir:
                    await _dump(page, dump_dir)
                raise ScrapeError(f"no \"Today's team\" heading on {url}: {exc}") from exc
            try:
                await page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:  # noqa: BLE001 - analytics etc. can keep the network busy
                pass
            found = await page.evaluate(_FIND_SECTIONS_JS, [patterns, sorted(data.species), TEAM_SIZE])
            if dump_dir:
                await _dump(page, dump_dir)
        finally:
            await browser.close()

    body = found["body"]
    return build_team(date,
                      _section_text(found.get("today"), body, TODAY_HEADING),
                      _section_text(found.get("red"), body, RED_HEADING),
                      body)


async def _dump(page, dump_dir: Path) -> None:
    dump_dir.mkdir(parents=True, exist_ok=True)
    (dump_dir / "page.html").write_text(await page.content(), encoding="utf-8")
    (dump_dir / "page.txt").write_text(await page.evaluate("document.body.innerText"), encoding="utf-8")
    await page.screenshot(path=str(dump_dir / "page.png"), full_page=True)
    log.info("saved page dump to %s", dump_dir)
