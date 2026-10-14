"""Daily Red Discord bot. Run with:  python bot.py

Posts today's https://daily-red.com/ team every day and answers
/dailyred team, /dailyred red, /dailyred countdown and /dailyred setchannel.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Optional

import discord
from discord import app_commands
from discord.ext import tasks

from dailyred import embeds
from dailyred.config import ConfigError, load_config
from dailyred.state import State
from dailyred.teams import TeamService

log = logging.getLogger("dailyred")

# Retries when the site can't be read at post time: 1, 5 and 15 minutes.
RETRY_DELAYS = [60, 300, 900]


class DailyRedBot(discord.Client):
    def __init__(self, config):
        super().__init__(intents=discord.Intents.default())
        self.config = config
        self.state = State(config.state_dir / "state.json")
        self.teams = TeamService(config)
        self.tree = app_commands.CommandTree(self)
        self.tree.add_command(DailyRedCommands(self))
        self._post_lock = asyncio.Lock()
        # Fires at POST_TIME in the configured time zone every day.
        self.daily_post = tasks.loop(time=config.post_time)(self._daily_post)

    async def setup_hook(self) -> None:
        await self.tree.sync()
        self.daily_post.start()
        asyncio.create_task(self._catch_up())

    async def on_ready(self) -> None:
        log.info("logged in as %s; posting at %s %s", self.user, self.config.post_time.strftime("%H:%M"),
                 self.config.tz_name)

    def channel_ids(self) -> set[int]:
        ids = set(self.state.channels().values())
        if self.config.channel_id:
            ids.add(self.config.channel_id)
        return ids

    async def _catch_up(self) -> None:
        """On startup: if today's post time has passed and it wasn't posted yet, post now."""
        await self.wait_until_ready()
        if self.config.post_time_passed():
            await self.post_today()

    async def _daily_post(self) -> None:
        await self.post_today()

    async def post_today(self, only: int | None = None) -> None:
        async with self._post_lock:
            today = self.config.today()
            targets = [c for c in ([only] if only else self.channel_ids())
                       if self.state.posted(c) != today]
            if not targets:
                return

            team = None
            for attempt, delay in enumerate([0] + RETRY_DELAYS):
                await asyncio.sleep(delay)
                try:
                    team = await self.teams.today()
                    break
                except Exception:  # noqa: BLE001 - logged, then retried
                    log.exception("couldn't fetch today's team (attempt %d)", attempt + 1)

            for channel_id in targets:
                channel = self.get_channel(channel_id)
                if channel is None:
                    try:
                        channel = await self.fetch_channel(channel_id)
                    except discord.DiscordException:
                        log.error("can't see channel %s; invite the bot there or run /dailyred setchannel",
                                  channel_id)
                        continue
                try:
                    if team:
                        await channel.send(embeds=embeds.daily_embeds(team, self.config.next_midnight()))
                    else:
                        await channel.send(embed=embeds.unavailable_embed(today))
                    self.state.mark_posted(channel_id, today)
                    log.info("posted %s to channel %s", today, channel_id)
                except discord.Forbidden:
                    log.error("missing Send Messages / Embed Links permission in channel %s", channel_id)
                except discord.DiscordException:
                    log.exception("couldn't post to channel %s", channel_id)


class DailyRedCommands(app_commands.Group):
    def __init__(self, bot: DailyRedBot):
        super().__init__(name="dailyred", description="Today's Daily Red team (daily-red.com)")
        self.bot = bot

    async def _team_or_error(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            return await self.bot.teams.today()
        except Exception:  # noqa: BLE001 - user gets a friendly message, details go to the log
            log.exception("couldn't fetch today's team")
            await interaction.followup.send(embed=embeds.unavailable_embed(self.bot.config.today()))
            return None

    @app_commands.command(name="team", description="Today's six Pokémon")
    async def team(self, interaction: discord.Interaction) -> None:
        team = await self._team_or_error(interaction)
        if team:
            await interaction.followup.send(embeds=embeds.team_embeds(team, self.bot.config.next_midnight()))

    @app_commands.command(name="red", description="Red's team")
    async def red(self, interaction: discord.Interaction) -> None:
        team = await self._team_or_error(interaction)
        if team:
            await interaction.followup.send(embeds=embeds.red_embeds(team))

    @app_commands.command(name="countdown", description="Time until the next team and the next daily post")
    async def countdown(self, interaction: discord.Interaction) -> None:
        cfg = self.bot.config
        await interaction.response.send_message(embed=embeds.countdown_embed(cfg.next_midnight(), cfg.next_post()))

    @app_commands.command(name="setchannel", description="Post the daily team in this channel (admins only)")
    @app_commands.describe(channel="Channel for the daily post (default: this one)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def setchannel(self, interaction: discord.Interaction,
                         channel: Optional[discord.TextChannel] = None) -> None:
        # Optional[...] rather than "| None": discord.py evaluates this
        # annotation at runtime, and Python 3.9 doesn't support "X | None".
        channel = channel or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Pick a text channel.", ephemeral=True)
            return
        perms = channel.permissions_for(interaction.guild.me)
        if not (perms.send_messages and perms.embed_links):
            await interaction.response.send_message(
                f"I need **Send Messages** and **Embed Links** in {channel.mention}.", ephemeral=True)
            return
        self.bot.state.set_channel(interaction.guild_id, channel.id)
        cfg = self.bot.config
        await interaction.response.send_message(
            f"Daily Red will post in {channel.mention} every day at "
            f"**{cfg.post_time.strftime('%H:%M')} ({cfg.tz_name})**.", ephemeral=True)
        if cfg.post_time_passed() and self.bot.state.posted(channel.id) != cfg.today():
            asyncio.create_task(self.bot.post_today(only=channel.id))

    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "Only server admins can use this command."
        else:
            log.exception("command failed", exc_info=error)
            message = "Something went wrong. Check the bot's console for details."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        config = load_config()
    except ConfigError as exc:
        sys.exit(f"Config error: {exc}")
    if not config.channel_id:
        log.warning("CHANNEL_ID isn't set: use /dailyred setchannel in your server to pick a channel")
    DailyRedBot(config).run(config.token, log_handler=None)


if __name__ == "__main__":
    main()
