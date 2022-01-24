# -*- coding: utf-8 -*-
import asyncio
from contextlib import suppress
from pathlib import Path
from random import choice, sample
from textwrap import indent
from typing import Optional, Union

import aiohttp
from colorama import Fore
from discord import (Activity, ActivityType, Guild, HTTPException, Invite,
                     Message, Status, User, VoiceChannel)
from discord.enums import RequiredActionType
from discord.ext import commands

from .utils.converters import MultiChannelConverter
from .utils.helpers import default_headers, get_blank_message


class RaidCommands(commands.Cog):
    '''These commands can only be used by accounts logged in from <prefix>account login'''

    def __init__(self, bot):
        self.bot = bot

        self._aiohttp_session = aiohttp.ClientSession()
        with open(Path('data/assets/text/usernames.txt'), encoding='utf-8') as f:
            self._usernames = f.readlines()
        with open(Path('data/assets/text/avatars.txt'), encoding='utf-8') as f:
            self._avatars = f.readlines()
        with open(Path('data/assets/text/emotes.txt'), encoding='utf-8') as f:
            self._unicode_emotes = f.readlines()


    @property
    def _random_emotes(self) -> str:
        payload = '**'
        while len(payload) + 4 < 2000:
            payload += chr(int(choice(self._unicode_emotes), 16))
        payload += '**'
        return payload


    async def cog_check(self, ctx):
        return ctx.author.id == self.bot.owner_id


    def _raid_print(self, message: str, severity: str = 'normal'):
        colours = {
            'normal': Fore.CYAN,
            'error': Fore.RED
        }
        print(f'{colours[severity]} [r] {self.bot.user}: {message}')


    @commands.Cog.listener()
    async def on_connect(self):
        self._raid_print('Connected')


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        self._raid_print(f"Error on {ctx.command}:\n{indent(str(error), ' ')}", 'error')


    @commands.Cog.listener()
    async def on_required_action_update(self, required_action: RequiredActionType):
        actions = {
            RequiredActionType.accept_terms: 'accept the Discord TOS',
            RequiredActionType.verify_phone: 'verify your account with phone',
            RequiredActionType.verify_email: 'verify your account with email',
            RequiredActionType.captcha: 'complete a captcha'
        }
        self._raid_print(f'Disconnected from websocket: You need to {actions[required_action]}', 'error')


    @commands.command()
    async def report(self, _, message_link: str, reason: int):
        '''RAID - Will send a report to discord Trust & Safety'''
        info = message_link.split('/')[4:7]
        payload = {
            'guild_id': info[0],
            'channel_id': info[1],
            'message_id': info[2],
            'reason': reason
        }
        r = await self._aiohttp_session.post('https://discordapp.com/api/v8/report', headers=default_headers(self.bot.TOKEN), json=payload)
        if r.status == 201:
            self._raid_print('Send report')
        else:
            self._raid_print(f'Couldn\'t report {message_link}', 'error')


    @commands.command(aliases=['channellag'])
    async def channeloutage(self, _, server: Guild, amount: int = 10):
        '''RAID - Will send [amount] emote messages to every channel in <guild> causing the reader to lag'''
        notsendable = set()
        self._raid_print(f'Starting channeloutage in {server}')
        for _ in range(amount):
            for tc in server.text_channels:
                try:
                    if tc.id not in notsendable:
                        await tc.send(self._random_emotes)
                except HTTPException:
                    notsendable.add(tc.id)


    @commands.command(aliases=['send'])
    async def say(self, _, channel: MultiChannelConverter, *, message: str):
        '''RAID - Will send a <message> to <channel>'''
        await channel.send(message)
        self._raid_print(f'Send message in {channel}')


    @commands.command(aliases=['directmessage'])
    async def dm(self, _, user: User, *, message: str):
        '''RAID - Will DM <user> with <message>'''
        await user.send(message)
        self._raid_print(f'Send DM to {user}')


    @commands.command(aliases=['friendrequest'])
    async def fr(self, _, user: User):
        '''RAID - Will send a FR to <user>'''
        await user.send_friend_request()
        self._raid_print(f'Send friend request to {user}')


    @commands.command(aliases=['user'])
    async def username(self, _, *, username: str = None):
        '''RAID - Will change username to [username] or something random'''
        if not username:
            username = choice(self._usernames)
        try:
            await self.bot.user.edit(username=username, password=self.bot.PASSWORD)
            self._raid_print(f'Changed username to {username}')
        except HTTPException:
            self._raid_print('Couldn\'t change username, password for this account is not the same as password set in config.json')


    @commands.command(aliases=['pfp', 'av'])
    async def avatar(self, _, user: User = None):
        '''RAID - Will change avatar to [user]'s avatar or something random'''
        if user:
            link = str(user.avatar_url)
        else:
            link = choice(self._avatars)

        async with self._aiohttp_session.get(link) as response:
            image_bytes = await response.read()

        try:
            await self.bot.user.edit(avatar=image_bytes, password=self.bot.PASSWORD)
            self._raid_print('Changed avatar')
        except HTTPException:
            self._raid_print('Couldn\'t change username, password for this account is not the same as password set in config.json')


    @commands.command(aliases=['nick'])
    async def nickname(self, _, server: Guild, *, nickname: str = None):
        '''RAID - Will change nickname in <guild> to [nickname]'''
        if not nickname:
            nickname = choice(self._usernames)
        await server.me.edit(nick=nickname)
        self._raid_print(f'Changed nickname to {nickname}')


    @commands.command()
    async def spam(self, _, channel: MultiChannelConverter, amount: Optional[int] = 5, *, message: str):
        '''RAID - Will send <message> [amount] times in a row in <channel>'''
        for _ in range(amount):
            with suppress(HTTPException):
                await channel.send(message)


    @commands.group(invoke_without_command=True, aliases=['server'])
    async def guild(self, _):
        '''RAID - Group command for RAID accounts to join and leave guilds'''

    @guild.command('join')
    async def guild_join(self, _, invite: Union[Invite, str], delayed: bool = False):
        '''RAID - Will join server by <invite> possibly with random delay'''
        if delayed:
            await asyncio.sleep(self.bot.RANDOM_NUMBER)

        if isinstance(invite, Invite):
            invite = f'discord.gg/{invite.code}'

        await self.bot.user.join_guild(invite)
        self._raid_print(f'Joined guild by {invite}')

    @guild.command('leave')
    async def guild_leave(self, _, server_id: int):
        '''RAID - Will leave server by <server_id>'''
        await self.bot.user.leave_guild(server_id)
        self._raid_print(f'Left guild {server_id}')


    @commands.group(invoke_without_command=True)
    async def blank(self, ctx, channel: MultiChannelConverter = None, length: int = None):
        '''RAID - Group command for sending ~2000 char long whitespace messages'''
        channel = channel or ctx.channel
        await channel.send(get_blank_message(self.bot, length))

    async def _blank_guild(self, message: Message):
        if message.guild.id == self.bot._blank_guild_guildid:
            if not message.author.id in self.bot.IMMUNE:
                try:
                    await message.channel.send(get_blank_message(self.bot))
                except HTTPException:
                    self.bot.remove_listener(self._blank_guild, 'on_message')

    @blank.command('guild')
    async def blank_guild(self, _, server_id: int):
        '''RAID - Will send a blank message after each message in guild by <server_id>'''
        self.bot._blank_guild_guildid = server_id
        self.bot.add_listener(self._blank_guild, 'on_message')
        self._raid_print(f'Added blank listener on guild {server_id}')

    @blank.command('stop')
    async def blank_stop(self, _):
        '''RAID - Will stop the blank listener'''
        self.bot.remove_listener(self._blank_guild, 'on_message')
        self._raid_print('Removed blank guild listener')


    @commands.group(invoke_without_command=True)
    async def annoy(self, _):
        '''RAID - Group command for reacting to messages with emoji's'''

    async def _annoy_user(self, message: Message):
        if message.author.id == self.bot._annoy_user_userid:
            for e in self.bot.annoy_user_emojis:
                with suppress(HTTPException):
                    await message.add_reaction(e)

    @annoy.command('user')
    async def annoy_user(self, _, user_id: int, *emojis: str):
        '''RAID - Will react with [emojis...] to each message from user by <user_id>'''
        self.bot._annoy_user_userid, self.bot.annoy_user_emojis = user_id, emojis
        self.bot.add_listener(self._annoy_user, 'on_message')
        self._raid_print(f'Added annoy listener on user {user_id}')

    async def _annoy_guild(self, message: Message):
        if message.guild.id == self.bot._annoy_guild_guildid:
            if message.author.id not in self.bot.IMMUNE:
                for e in self.bot._annoy_guild_emojis:
                    with suppress(HTTPException):
                        await message.add_reaction(e)

    @annoy.command('guild', aliases=['server'])
    async def annoy_guild(self, _, server_id: int, *emojis: str):
        '''RAID - Will react with [emojis...] to each message in server by <server_id>'''
        self.bot._annoy_guild_guildid, self.bot._annoy_guild_emojis = server_id, emojis
        self.bot.add_listener(self._annoy_guild, 'on_message')
        self._raid_print(f'Added annoy listener on guild {server_id}')

    @annoy.command('stop')
    async def annoy_stop(self, _):
        '''RAID - Will stop all annoy listeners'''
        self.bot.remove_listener(self._annoy_guild, 'on_message')
        self.bot.remove_listener(self._annoy_user, 'on_message')
        self._raid_print('Stopped annoy listener(s)')


    @commands.group(aliases=['guildspam', 'raidguild'])
    async def raidserver(self, _):
        '''RAID - Group command for message/ping raiding servers'''

    @raidserver.command('start', aliases=['ping', 'message'])
    async def raidserver_start(self, _, server: Guild, *, message: str = None):
        '''RAID - Will spam every channel in <guild> with [message] or ping'''
        await server.subscribe()
        self.bot._raidserver_enabled, notsendable = True, set()
        self._raid_print(f"Starting {'message' if message else 'ping'} raid on {server}")
        while self.bot._raidserver_enabled:
            for tc in server.text_channels:
                if not self.bot._raidserver_enabled:
                    break
                try:
                    if tc.id not in notsendable:
                        await tc.send(message or ' '.join([m.mention for m in sample(server.members, 50)]))
                except HTTPException:
                    notsendable.add(tc.id)

    @raidserver.command('stop')
    async def raidserver_stop(self, _):
        '''RAID - Will stop the server raid'''
        self.bot._raidserver_enabled = False
        self._raid_print('Stopped server raid')


    @commands.group(invoke_without_command=True)
    async def activity(self, _):
        '''RAID - Group command for changing the Discord activity'''

    @activity.command('streaming')
    async def activity_streaming(self, _, stream_url: str, *, message: str):
        '''RAID - Will change the activity to Streaming <message> with <stream_url>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.streaming, name=message, url=stream_url))
        self._raid_print(f'Changed status to streaming {message} with url {stream_url}')

    @activity.command('playing')
    async def activity_playing(self, _, *, message: str):
        '''RAID - Will change the activity to Playing <message>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.playing, name=message))
        self._raid_print(f'Changed status to Playing {message}')

    @activity.command('listening')
    async def activity_listening(self, _, *, message: str):
        '''RAID - Will change the activity to Listening to <message>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.listening, name=message))
        self._raid_print(f'Changed status to Listening to {message}')

    @activity.command('watching')
    async def activity_watching(self, _, *, message: str):
        '''RAID - Will change the activity to Watching <message>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.watching, name=message))
        self._raid_print(f'Changed status to watching {message}')

    @activity.command('competing', aliases=['competing_in'])
    async def activity_competing(self, _, *, message: str):
        '''Will change the activity to Competing in <message>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.competing, name=message))
        self._raid_print(f'Changed status to Competing in {message}')


    @commands.group(invoke_without_command=True, aliases=['status'])
    async def presence(self, _):
        '''RAID - Group command for changing the Discord presence'''

    @presence.command('online')
    async def presence_online(self, _):
        '''RAID- Will set the presence to Online'''
        await self.bot.change_presence(status=Status.online)
        self._raid_print('Changed presence to online')

    @presence.command('offline')
    async def presence_offline(self, _):
        '''RAID- Will set the presence to Invisible'''
        await self.bot.change_presence(status=Status.invisible)
        self._raid_print('Changed presence to offline')

    @presence.command('idle')
    async def presence_idle(self, _):
        '''RAID- Will set the presence to Idle'''
        await self.bot.change_presence(status=Status.idle)
        self._raid_print('Changed presence to idle')

    @presence.command('dnd', aliases=['donotdisturb'])
    async def presence_dnd(self, _):
        '''RAID - Will set the presence to Do Not Disturb'''
        await self.bot.change_presence(status=Status.dnd)
        self._raid_print('Changed presence to do not disturb')


    @commands.group(invoke_without_command=True)
    async def voicechannel(self, _):
        '''RAID - Group command for joining and leaving voicechannels'''

    @voicechannel.command('join', aliases=['connect'])
    async def voicechannel_join(self, _, voicechannel: VoiceChannel):
        '''RAID - Will connect to <voicechannel>'''
        self.bot._voicechannel = await voicechannel.connect(reconnect=True)
        self._raid_print(f'Connected to {voicechannel}')

    @voicechannel.command('leave', aliases=['disconnect'])
    async def voicechannel_leave(self, _):
        '''RAID - Will disconnect from voicechannel'''
        await self.bot._voicechannel.disconnect()
        self._raid_print('Disconnected from voicechannel')


def setup(bot):
    bot.add_cog(RaidCommands(bot))
