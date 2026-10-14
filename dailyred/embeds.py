from __future__ import annotations

from datetime import date as Date, datetime

import discord

from . import SITE_URL
from .models import DailyTeam, Mon, sprite_url

TYPE_COLORS = {
    "Normal": 0xA8A77A, "Fire": 0xEE8130, "Water": 0x6390F0, "Electric": 0xF7D02C,
    "Grass": 0x7AC74C, "Ice": 0x96D9D6, "Fighting": 0xC22E28, "Poison": 0xA33EA1,
    "Ground": 0xE2BF65, "Flying": 0xA98FF3, "Psychic": 0xF95587, "Bug": 0xA6B91A,
    "Rock": 0xB6A136, "Ghost": 0x735797, "Dragon": 0x6F35FC, "Dark": 0x705746,
    "Steel": 0xB7B7CE,
}
RED = 0xC0392B


def title(team: DailyTeam) -> str:
    day = Date.fromisoformat(team.date).strftime("%B %d, %Y").replace(" 0", " ")
    number = f" No. {team.number}" if team.number else ""
    return f"Daily Red{number} — {day}"


def _ts(when: datetime, style: str = "R") -> str:
    return f"<t:{int(when.timestamp())}:{style}>"


def mon_embed(mon: Mon, *, red: bool = False) -> discord.Embed:
    embed = discord.Embed(
        title=f"{'Red’s ' if red else ''}{mon.name}",
        url=f"https://bulbapedia.bulbagarden.net/wiki/{mon.name.replace(' ', '_')}_(Pok%C3%A9mon)",
        color=RED if red else TYPE_COLORS.get(mon.types[0], 0x95A5A6),
    )
    embed.set_thumbnail(url=sprite_url(mon.dex))
    embed.add_field(name="Type", value=" / ".join(mon.types), inline=True)
    embed.add_field(name="Item", value=mon.item or "—", inline=True)
    embed.add_field(name="Ability", value=mon.ability or "—", inline=True)
    embed.add_field(name="Moves", value="\n".join(f"• {m}" for m in mon.moves) or "—", inline=False)
    embed.set_footer(text=f"#{mon.dex:03d} · Lv. 100")
    return embed


def red_summary(team: DailyTeam) -> str:
    lines = []
    for mon in team.red:
        extra = " · ".join(x for x in (mon.item and f"@ {mon.item}", ", ".join(mon.moves)) if x)
        lines.append(f"**{mon.name}**" + (f" — {extra}" if extra else ""))
    return "\n".join(lines)


def daily_embeds(team: DailyTeam, next_team: datetime) -> list[discord.Embed]:
    """Header + one embed per Pokémon (7 embeds; Discord allows 10)."""
    header = discord.Embed(
        title=title(team),
        url=SITE_URL,
        color=RED,
        description=(
            "Everyone gets the same six level 100 Pokémon today. Can you beat Red?\n"
            f"**[▶ Play today's battle]({SITE_URL})** · new team {_ts(next_team)}"
        ),
    )
    header.add_field(name="Red’s team", value=red_summary(team)[:1024], inline=False)
    header.set_thumbnail(url=sprite_url(25))
    return [header] + [mon_embed(m) for m in team.team]


def team_embeds(team: DailyTeam, next_team: datetime) -> list[discord.Embed]:
    header = discord.Embed(
        title=title(team), url=SITE_URL, color=RED,
        description=f"Today's team · **[Play]({SITE_URL})** · new team {_ts(next_team)}",
    )
    return [header] + [mon_embed(m) for m in team.team]


def red_embeds(team: DailyTeam) -> list[discord.Embed]:
    header = discord.Embed(
        title="Red’s team", url=SITE_URL, color=RED,
        description="Red's team never changes. He always leads with Pikachu.",
    )
    return [header] + [mon_embed(m, red=True) for m in team.red]


def countdown_embed(next_team: datetime, next_post: datetime) -> discord.Embed:
    embed = discord.Embed(title="Daily Red countdown", url=SITE_URL, color=RED)
    embed.add_field(name="Next team", value=f"{_ts(next_team)} ({_ts(next_team, 't')})", inline=False)
    embed.add_field(name="Next daily post", value=f"{_ts(next_post)} ({_ts(next_post, 't')})", inline=False)
    return embed


def unavailable_embed(today: str) -> discord.Embed:
    return discord.Embed(
        title=f"Daily Red — {today}", url=SITE_URL, color=RED,
        description=(f"Couldn't load today's team right now, but the game is up: "
                     f"**[▶ Play today's battle]({SITE_URL})**"),
    )
