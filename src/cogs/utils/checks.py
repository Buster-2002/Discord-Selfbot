# -*- coding: utf-8 -*-
from shutil import which
from typing import Dict

from discord import DMChannel, GroupChannel, Permissions
from discord.ext import commands

from .exceptions import NoFFMPEG, OnlyDM


def bot_has_permissions(**perms: Dict[Permissions, bool]) -> commands.check:
    async def predicate(ctx) -> bool:
        ctx.command.required_perms = [p.replace('_', ' ').title() for p in perms.keys()]
        if ctx.guild:
            return await commands.has_guild_permissions(**perms).predicate(ctx)
        return True
    return commands.check(predicate)


def dm_only() -> commands.check:
    async def predicate(ctx) -> bool:
        if not isinstance(ctx.channel, (DMChannel, GroupChannel)):
            raise OnlyDM()
        return True
    return commands.check(predicate)


def check_ffmpeg() -> commands.check:
    async def predicate(_) -> bool:
        if not which('ffmpeg'):
            raise NoFFMPEG()
        return True
    return commands.check(predicate)
