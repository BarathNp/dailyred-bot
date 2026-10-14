"""Fetch today's team from the live site and print it: no Discord needed.

    python -m dailyred.check                    # today in TZ from .env
    python -m dailyred.check --tz Asia/Tokyo
    python -m dailyred.check --date 2026-10-20  # fakes the browser clock
    python -m dailyred.check --dump debug/      # also saves page.html/txt/png

Use it to check the bot reads the site correctly (compare with what you see
at https://daily-red.com/) and to debug if the site changes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .scraper import scrape


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tz", default=os.getenv("TZ") or "UTC")
    parser.add_argument("--date", help="YYYY-MM-DD (default: today in --tz)")
    parser.add_argument("--dump", type=Path, help="folder to save the page HTML, text and a screenshot")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a summary")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    tz = ZoneInfo(args.tz)
    at = None
    if args.date:
        at = datetime.combine(date.fromisoformat(args.date), time(12, 0), tz)
    day = (at or datetime.now(tz)).date().isoformat()
    team = asyncio.run(scrape(args.tz, day, at=at, dump_dir=args.dump))

    if args.json:
        print(json.dumps(team.to_dict(), ensure_ascii=False, indent=2))
        return
    print(f"Daily Red No. {team.number or '?'} — {team.date} ({args.tz})\n")
    for label, mons in (("Today's team", team.team), ("Red's team", team.red)):
        print(label)
        for m in mons:
            print(f"  {m.name:<12} {'/'.join(m.types):<16} @ {m.item or '-':<14} "
                  f"[{m.ability or '-'}]  {', '.join(m.moves) or '-'}")
        print()


if __name__ == "__main__":
    main()
