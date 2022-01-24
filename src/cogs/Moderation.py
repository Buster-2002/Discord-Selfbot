# -*- coding: utf-8 -*-
import asyncio
from contextlib import suppress
from typing import Optional, Union

from discord import (Guild, HTTPException, Member, Object, PermissionOverwrite,
                     Role, TextChannel, User, utils)
from discord.ext import commands

from .utils.checks import bot_has_permissions
from .utils.converters import TimeConverter


class Moderation(commands.Cog):
    '''Extension category for all moderation related commands.'''

    def __init__(self, bot):
        self.bot = bot

        self._slowmode_delays = dict()
        self._locked_channels = dict()


    @commands.command()
    @commands.guild_only()
    async def mpurge(self, ctx, amount: Optional[int] = 50, users: commands.Greedy[User] = None, *word_filter: str.lower):
        '''Will purge for [amount] messages filtering by [users] and/or [word_filter]'''
        await ctx.channel.purge(
            limit=(amount + 1),
            check=lambda m: (
                m.author in users if users else True
                and any([
                    kw.casefold() in utils.remove_markdown(m.content.casefold())
                    for kw in word_filter]) if word_filter else True
                and not m.pinned
            )
        )


    @bot_has_permissions(kick_members=True)
    @commands.guild_only()
    @commands.command()
    async def kick(self, ctx, user: Union[Member, Object], server: Guild = None):
        '''Will kick <member> from [server]'''
        guild = server or ctx.guild
        await guild.kick(user)
        await self.bot.log(f'Kicked {user} from {guild}')


    @bot_has_permissions(ban_members=True)
    @commands.guild_only()
    @commands.command(usage='<member> [delmsg=0 (max 7)]')
    async def ban(self, ctx, user: Union[Member, Object], delmsgs: int = 0, server: Guild = None):
        '''Will ban <member> from [server]'''
        guild = server or ctx.guild
        await guild.ban(user, delete_message_days=delmsgs)
        await self.bot.log(f'Banned {user} from {guild}')


    @commands.command(aliases=['exportbans'])
    async def copybans(self, _, fromserver: Guild, toserver: Guild, delmsgs: int = 0):
        '''Will ban people banned in <fromserver> in <toserver>'''
        banned, bans = await fromserver.bans(), 0
        for ban in bans:
            await toserver.ban(ban.user, delete_message_days=delmsgs)
            banned += 1
        await self.bot.log(f'Banned {banned} user(s) in {toserver}')


    # If I was going by my command style, these should be combined into a group command
    # But its quicker to use this way
    @bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    @commands.command(aliases=['lockchannels'])
    async def lock(self, ctx, channels: commands.Greedy[TextChannel], *excluded_roles: Role):
        '''Will make it so only [excluded_roles] (and admins) can send messages in [channels]'''
        channels = channels or [ctx.channel]
        guild = ctx.guild
        locked_roles = [r for r in guild.roles if r not in excluded_roles]
        overwrite = {r: PermissionOverwrite(send_messages=False) for r in locked_roles}
        self._locked_channels[guild.id] = {
            'roles': locked_roles,
            'channels': []
        }
        for channel in channels:
            await channel.edit(overwrites=overwrite)
            self._locked_channels[guild.id]['channels'].append(channel)

        await self.bot.log(f"Locked {len(channels)} channel(s) in {guild} for {len(locked_roles)} roles")

    @commands.command(aliases=['unlockchannels'])
    async def unlock(self, ctx, server: Guild = None):
        '''Will unlock previously locked channels in [server]'''
        guild = server or ctx.guild
        try:
            data = self._locked_channels[guild.id]
            locked_roles, channels = data['roles'], data['channels']
            overwrite = {r: PermissionOverwrite(send_messages=None) for r in locked_roles}
            for channel in channels:
                await channel.edit(overwrites=overwrite)

            await self.bot.log(f"Unlocked {len(channels)} channel(s) in {guild} for {len(locked_roles)} roles")
        except KeyError:
            await self.bot.log(f'No data available for locked channels in {guild}')


    @commands.command(aliases=['clone'])
    @commands.guild_only()
    async def nuke(self, ctx, channel: TextChannel = None):
        '''Will clone and delete a channel'''
        channel = channel or ctx.channel
        await ctx.channel.delete()
        await channel.clone()
        await self.bot.log(f'Succesfully nuked {channel}')


    @bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    @commands.command()
    async def mute(self, ctx, member: Member, time: TimeConverter = 3600, server: Guild = None):
        '''Will mute <member> for [time] in [server]'''
        guild = server or ctx.guild
        overwrite = PermissionOverwrite(send_messages=False)
        with suppress(HTTPException):
            for tc in guild.text_channels:
                await tc.set_permissions(member, overwrites=overwrite)

            await self.bot.log(f'Muted {member} for {time}s in {guild}')
            await asyncio.sleep(time)
            overwrite.send_messages = None
            for tc in guild.text_channels:
                await tc.set_permissions(member, overwrites=overwrite)

            await self.bot.log(f'Unmuted {member} in {server}', 'info')

    @bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    @commands.command()
    async def unmute(self, ctx, member: Member, server: Guild = None):
        '''Will unmute <member> in [server]'''
        guild = server or ctx.guild
        for tc in guild.text_channels:
            with suppress(HTTPException):
                overwrite = PermissionOverwrite(outgoing_messages=None)
                await tc.set_permissions(member, overwrites=overwrite)

        await self.bot.log(f'Unmuted {member} in {guild}')


    @commands.group(aliases=['slow'], invoke_without_command=True)
    async def slowmode(self, _):
        '''Group command for overwriting/resetting slowmode'''
        raise commands.CommandNotFound()

    @bot_has_permissions(manage_channels=True)
    @slowmode.command('overwrite', aliases=['start'])
    async def slowmode_overwrite(self, ctx, delay: TimeConverter = 120, server: Guild = None, *exclusions: TextChannel):
        '''Will set the slowmode for each channel in [guild] to [delay]'''
        guild = server or ctx.guild
        self._slowmode_delays[guild.id] = []
        await self.bot.log(f'Starting slowmode overwrite in {guild}')
        for tc in guild.text_channels:
            if tc not in exclusions:
                self._slowmode_delays[guild.id].append((tc, tc.slowmode_delay))
                await tc.edit(slowmode_delay=delay)

    @bot_has_permissions(manage_channels=True)
    @slowmode.command('reset', aliases=['stop'])
    async def slowmode_reset(self, ctx, server: Guild = None):
        '''Resets the slowmode of each channel back to its original'''
        guild = server or ctx.guild
        await self.bot.log(f'Resetting the slowmode back to it\'s original in {guild}')
        try:
            for tc, original_delay in self._slowmode_delays[guild.id]:
                await tc.edit(slowmode_delay=original_delay)
        except KeyError:
            await self.bot.log(f'No original slowmode delays available for {guild}', 'error')


def setup(bot):
    bot.add_cog(Moderation(bot))
