# Daily Red Discord bot

A Discord bot for [Daily Red](https://daily-red.com/), the Wordle-style Pokémon game where everyone gets the same six random level 100 Pokémon (Gen 1–3) each day and battles Red.

Every day at a time you pick, the bot posts **"Daily Red No. X — <date>"** to your channel. The post shows today's six Pokémon (sprite, types, held item, ability, moves), Red's team and a link to play. It also adds slash commands:

| Command | What it does |
|---|---|
| `/dailyred team` | Today's six Pokémon |
| `/dailyred red` | Red's team |
| `/dailyred countdown` | Time until the next team (midnight) and the next daily post |
| `/dailyred setchannel [channel]` | Admins only: post the daily team in this channel (or the one you pick) |

---

## Contents

1. [How the bot gets the team](#how-the-bot-gets-the-team)
2. [Create the bot in the Discord Developer Portal](#1-create-the-bot-in-the-discord-developer-portal)
3. [Invite it to your server](#2-invite-it-to-your-server)
4. [Run it on Windows](#3-run-it-on-windows)
5. [Start it automatically with Task Scheduler](#4-start-it-automatically-with-task-scheduler-windows)
6. [Deploy it to Railway (runs 24/7 without your PC)](#5-deploy-to-railway)
7. [Settings](#settings)
8. [Troubleshooting](#troubleshooting)
9. [For developers](#for-developers)

---

## How the bot gets the team

Daily Red has no API. The website builds the day's team **in your browser**, from your local date, in its JavaScript bundle (`/assets/index-*.js`).

I considered two ways to get the team:

- **Port the generator to Python.** This would be fast and wouldn't need a browser. But the bundle is minified and not published anywhere, and any change the site makes to it would silently give the bot the wrong team.
- **Open the site in a headless browser (Playwright) and read the page.** ✅ **This is what the bot does.**

The browser approach gets exactly what players see, because it runs the site's own code. It also keeps working when the generator changes. How it works:

1. Once a day the bot opens https://daily-red.com/ in headless Chromium, with the browser's time zone set to your `TZ`. The site therefore builds the same team your players get.
2. It finds the **"Today's team"** and **"Red's team"** headings. From each heading it walks up the page to the smallest block that holds six Pokémon names.
3. It reads that block's text and recognises Pokémon, moves, abilities and items by name. The names come from a bundled Gen 1–3 list built from [PokeAPI](https://github.com/PokeAPI/pokeapi). Because the bot matches names rather than CSS classes, a redesign of the site is unlikely to break it.
4. It caches the result in `state/teams/<date>.json`, so the site is only loaded once a day.

Types and Pokédex numbers come from the bundled data, so they use Gen 3 types (Clefairy is Normal, not Fairy). Sprites come from the [PokeAPI sprites repo](https://github.com/PokeAPI/sprites).

> **Check it against the live site after you install it.** When this bot was built, its build environment couldn't reach daily-red.com. The parser and the browser pipeline are tested against local sample pages (see [For developers](#for-developers)), but not yet against the real page. Run `python -m dailyred.check` (step 3.5 below) and compare the output with https://daily-red.com/. If something is off, run `python -m dailyred.check --dump debug` and look at `debug/page.txt` and `debug/page.png`.

If the bot can't read Red's section, it falls back to his fixed lineup (Pikachu, Espeon, Snorlax, Venusaur, Charizard, Blastoise) without items or moves. If it can't read today's team, the daily post becomes a short "play here" message. It retries after 1, 5 and 15 minutes before giving up for the day.

---

## 1. Create the bot in the Discord Developer Portal

1. Go to https://discord.com/developers/applications and log in.
2. Click **New Application**, name it (e.g. "Daily Red") and click **Create**.
3. In the left menu, click **Bot**.
   - Click **Reset Token**, then **Copy**. This is your `DISCORD_TOKEN`.
   - ⚠️ **Treat the token like a password.** Anyone with it can control your bot. Never paste it in Discord, a screenshot or a GitHub file. If it leaks, click **Reset Token** again.
   - You don't need any of the "Privileged Gateway Intents"; leave them off.
4. In the left menu, click **General Information** and copy the **Application ID**. You need it for the invite link.

## 2. Invite it to your server

Paste this into your browser, replacing `YOUR_APPLICATION_ID` with the ID from step 1.4:

```
https://discord.com/oauth2/authorize?client_id=YOUR_APPLICATION_ID&scope=bot+applications.commands&permissions=18432
```

- `scope=bot applications.commands` adds the bot and lets it register slash commands.
- `permissions=18432` = **Send Messages** (2048) + **Embed Links** (16384).

Pick your server and click **Authorize**. You need the "Manage Server" permission on that server.

You can also build the link in the portal: **OAuth2 → URL Generator**, tick `bot` and `applications.commands`, then tick **Send Messages** and **Embed Links**.

**Get the channel ID:** in Discord, open **User Settings → Advanced** and turn on **Developer Mode**. Then right-click your channel and choose **Copy Channel ID**. This is your `CHANNEL_ID`. You can skip this and use `/dailyred setchannel` in the channel instead.

## 3. Run it on Windows

1. **Install Python 3.10 or newer** from https://www.python.org/downloads/. In the installer, tick **"Add python.exe to PATH"**.
2. **Download the bot:** on GitHub click **Code → Download ZIP** and unzip it, e.g. to `C:\dailyred-bot`. (Or `git clone` it.)
3. **Open a terminal in that folder:** in File Explorer, open the folder, click the address bar, type `cmd` and press Enter. Then run:

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

   The last line downloads the headless browser (about 150 MB, one time).
4. **Configure it:** copy `.env.example` to `.env` (`copy .env.example .env`) and open `.env` in Notepad. Fill in:

   ```ini
   DISCORD_TOKEN=paste-your-token-here
   CHANNEL_ID=123456789012345678
   TZ=America/New_York
   POST_TIME=09:00
   ```

   `TZ` is your time zone name, from [this list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) (e.g. `Europe/London`, `Asia/Kolkata`, `Australia/Sydney`). `POST_TIME` is in 24-hour time.
5. **Check it can read the site** (no Discord needed):

   ```bat
   python -m dailyred.check
   ```

   You should see today's six Pokémon and Red's team. Compare them with https://daily-red.com/.
6. **Start the bot:**

   ```bat
   python bot.py
   ```

   You should see `logged in as Daily Red#1234; posting at 09:00 America/New_York`. Slash commands can take a minute to appear in Discord the first time; restart Discord if they don't show up.

The bot only runs while this window is open. Press `Ctrl+C` to stop it.

**When does it post?** Every day at `POST_TIME`. If you start the bot *after* today's post time and today hasn't been posted yet, it posts right away. If you start it before the post time, it waits. The posted dates are tracked in `state/state.json`, so restarting the bot never posts twice.

## 4. Start it automatically with Task Scheduler (Windows)

Use `start-bot.bat`, which comes with the bot. It runs the bot from the `.venv` you created and writes output to `bot.log`. Double-click it once to check it works, then close the window.

1. Press **Start**, type **Task Scheduler** and open it.
2. Click **Create Task…** (not "Create Basic Task").
3. **General** tab: Name `Daily Red Bot`. Tick **Run only when user is logged on**.
   - To run it even when nobody is logged in, choose **Run whether user is logged on or not** instead. Windows will ask for your password.
4. **Triggers** tab → **New…** → Begin the task: **At log on** (or **At startup** if you chose "whether user is logged on or not") → OK.
5. **Actions** tab → **New…** → Action: **Start a program**.
   - Program/script: `C:\dailyred-bot\start-bot.bat` (your path)
   - Start in: `C:\dailyred-bot`
6. **Conditions** tab: untick **Start the task only if the computer is on AC power** (for laptops).
7. **Settings** tab:
   - Untick **Stop the task if it runs longer than 3 days**.
   - Tick **If the task fails, restart every 1 minute**, attempt up to 3 times.
8. Click **OK**. To test it, right-click the task and choose **Run**, then check `bot.log`.

Or do the same from a terminal (logged-on version):

```bat
schtasks /Create /TN "Daily Red Bot" /TR "\"C:\dailyred-bot\start-bot.bat\"" /SC ONLOGON
```

To stop the bot, open Task Scheduler, right-click the task and choose **End**. To remove it, choose **Delete**.

Your PC has to be on (not asleep) at post time. If it was asleep, the bot posts as soon as it's running again that day. For a bot that's always on, use Railway.

## 5. Deploy to Railway

[Railway](https://railway.com/) runs the bot in the cloud 24/7. The repo includes a `Dockerfile` (Python and Chromium, from Microsoft's Playwright image) and a `railway.json` that tells Railway to use it.

1. Put the bot on GitHub (your own repo; **without** `.env`, which `.gitignore` already excludes).
2. On https://railway.com, sign in with GitHub and click **New Project → Deploy from GitHub repo**, then pick your repo.
3. Open the service, go to **Variables** and add:

   | Name | Value |
   |---|---|
   | `DISCORD_TOKEN` | your bot token |
   | `CHANNEL_ID` | your channel ID |
   | `TZ` | e.g. `America/New_York` |
   | `POST_TIME` | e.g. `09:00` |

   Railway keeps variables secret; this is the right place for the token, not a file.
4. **Add a volume** so the bot remembers what it posted across redeploys: right-click the service → **Attach Volume**, mount path `/app/state`.
   - Without a volume, a redeploy after post time can post today's team a second time.
   - Without a volume, a channel set with `/dailyred setchannel` is forgotten. Set `CHANNEL_ID` to avoid that.
5. Railway builds and starts the bot. Check **Deployments → View Logs** for the `logged in as …` line.

The bot doesn't serve web pages, so it doesn't need a domain or port. The `Procfile` (`worker: python bot.py`) is there for hosts that use Procfiles instead of Docker.

---

## Settings

All settings come from environment variables (or `.env` locally):

| Variable | Required | Example | Meaning |
|---|---|---|---|
| `DISCORD_TOKEN` | yes | | Bot token. Never commit it. |
| `CHANNEL_ID` | no | `123456789012345678` | Channel for the daily post. You can also (or instead) use `/dailyred setchannel` in each server. |
| `TZ` | no (default `UTC`) | `Europe/Berlin` | Time zone for the post time and for "today" (the team changes at midnight here) |
| `POST_TIME` | no (default `09:00`) | `18:30` | Daily post time, 24-hour, in `TZ` |
| `STATE_DIR` | no (default `state`) | `/app/state` | Where `state.json` and cached teams are kept |
| `DAILYRED_DAY_ONE` | no | `2026-10-11` | Date of Daily Red No. 1. Only used for the number in the title, and only if the website doesn't show its own number. If neither is available, the title is "Daily Red — <date>". |

`/dailyred setchannel` is saved per server in `state/state.json`, so the bot can post in several servers. Only members with the **Administrator** permission see and can use it.

## Troubleshooting

- **`Config error: DISCORD_TOKEN is missing`**: you haven't created `.env` (step 3.4), or the line is empty.
- **`discord.errors.LoginFailure: Improper token`**: the token is wrong or was reset. Copy a new one from the portal.
- **Slash commands don't show up**: wait a minute and restart Discord. Check the invite link included `applications.commands` (re-invite if not; it doesn't remove anything).
- **"missing Send Messages / Embed Links permission" in the log**: give the bot's role those permissions in that channel.
- **"Couldn't load today's team"**: run `python -m dailyred.check --dump debug` and look at the error and at `debug/page.png`. If the site changed its wording (e.g. the "Today's team" heading), update `TODAY_HEADING` / `RED_HEADING` in `dailyred/scraper.py`.
- **`Executable doesn't exist … chromium`**: run `python -m playwright install chromium`.
- **The team is from the wrong day**: check `TZ`. The site uses the local date, so `TZ` decides which day's team you get.

## For developers

```
bot.py                  Discord client, slash commands, daily scheduler
dailyred/scraper.py     Playwright: open the site, find the two sections
dailyred/parser.py      Section text → Pokémon (names matched against the data)
dailyred/pokedata.py    Loads data/gen3.json; name normalisation and Gen 3 aliases
dailyred/teams.py       Fetch once per day, cache in state/teams/
dailyred/embeds.py      Discord embeds
dailyred/check.py       python -m dailyred.check: print today's team from the live site
dailyred/data/gen3.json Species 1–386 (Gen 3 types), moves, abilities, items, from PokeAPI
tools/build_data.py     Rebuilds gen3.json from PokeAPI's CSVs
```

Tests:

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
pytest
```

- `tests/test_parser.py` covers the parser on hand-written text in a few layouts: name/type/item/ability/moves cards, Showdown export format, Gen 3 move spellings like "Faint Attack" and "Hi Jump Kick", and Nidoran♀ / Mr. Mime / Farfetch'd.
- `tests/test_scraper_local.py` runs the whole browser pipeline against a local page that renders its team from JavaScript after a delay. It checks the time zone and faked-clock handling, finding sections when the heading text also appears elsewhere, and the "No. X" number.

Neither test talks to daily-red.com; `python -m dailyred.check` does.

`python -m dailyred.check --date 2026-10-20 --tz Asia/Tokyo` fakes the browser clock, so you can read another day's team. That's handy for checking the bot against a friend's screenshot.

Data and sprites: [PokeAPI](https://pokeapi.co/). Daily Red is an unofficial fan game; this bot isn't affiliated with it, Nintendo, Creatures or GAME FREAK.
