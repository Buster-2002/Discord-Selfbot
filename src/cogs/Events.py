# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import time
from collections import Counter, defaultdict, deque
from contextlib import suppress
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from random import randrange
from textwrap import fill, shorten
from typing import Union

import aiohttp
import pyPrivnote as pn
from colorama import Fore, Style, init
from discord import (AsyncWebhookAdapter, DMChannel, Forbidden, FriendFlags,
                     GroupChannel, Guild, HTTPException, Message, NotFound,
                     Relationship, RelationshipType, User, Webhook, utils)
from discord.enums import RequiredActionType
from discord.ext import commands
from humanize import precisedelta
from urllib3 import PoolManager

from .utils.exceptions import (CommandDoesntExist, CommandExists,
                               InvalidExtension, NoFFMPEG, NoPasswordSet,
                               OnlyDM)
from .utils.helpers import change_config, default_headers
from .utils.ratelimit import RateLimit
from .utils.regexes import GIFT_REGEX, PRIVNOTE_REGEX, TOKEN_REGEX
from .utils.wizard import cls, lines

init()


class Events(commands.Cog):
    '''Category with all selfbot events. No commands are in this category.'''

    def __init__(self, bot):
        self.bot = bot
        self.bot.after_invoke(self._metrics)
        self.bot.MESSAGE_SNIPES = dict()
        self.bot.WORD_COUNTER = defaultdict(Counter)
        self.bot.GUILD_DELETE_LOG = deque(maxlen=1500)
        self.bot.GUILD_EDIT_LOG = deque(maxlen=1500)
        self.bot.MESSAGE_COUNT = defaultdict(int)
        self._known_selfbot = set()
        self._known_tokens = set()
        self._known_nitro = set()
        self._known_privnote = set()
        self._urllib3_session = PoolManager(maxsize=10)
        self._been_ready = False

        self._known_admins = set()

        # Some protections have since creating this already been incorporated into Discord itself
        if self.bot.PROTECTIONS_anti_spam_ping_state is True:
            self._anti_spam_ping_cds = defaultdict(lambda: RateLimit(
                self.bot.PROTECTIONS_anti_spam_ping_calls,
                self.bot.PROTECTIONS_anti_spam_ping_period
            ))
        if self.bot.PROTECTIONS_anti_spam_groupchat_state is True:
            self._anti_spam_group_cds = defaultdict(lambda: RateLimit(
                self.bot.PROTECTIONS_anti_spam_groupchat_calls,
                self.bot.PROTECTIONS_anti_spam_groupchat_period
            ))
        if self.bot.PROTECTIONS_anti_spam_friend_state is True:
            self._anti_spam_friend_cd = RateLimit(
                self.bot.PROTECTIONS_anti_spam_friend_calls,
                self.bot.PROTECTIONS_anti_spam_friend_period
            )
        if self.bot.PROTECTIONS_anti_spam_dm_state is True:
            self.anti_spam_dm_cd = RateLimit(
                self.bot.PROTECTIONS_anti_spam_dm_calls,
                self.bot.PROTECTIONS_anti_spam_dm_period
            )


    async def _metrics(self, ctx):
        ctx.bot.COMMANDS_USED += 1
        with open(Path('data/json/metrics.json'), 'r+', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                f.seek(0)
                f.truncate(0)
                json.dump({}, f, indent=4)
                data = {}

        with open(Path('data/json/metrics.json'), 'w', encoding='utf-8') as f:
            if ctx.command.parent:
                if ctx.invoked_subcommand:
                    if ctx.command.parent.name not in data.keys():
                        data[ctx.command.parent.name] = 0
                    data[ctx.command.parent.name] += 1
            else:
                if ctx.command.name not in data.keys():
                    data[ctx.command.name] = 0
                data[ctx.command.name] += 1
            json.dump(data, f, indent=4)


    def _update_all_commands(self):
        # This code sucks, no doubt it can be done better and shorter
        self.bot.available_command_combinations = set()
        for base_command in self.bot.commands:
            if isinstance(base_command, commands.Group):
                if not base_command.invoke_without_command:
                    self.bot.available_command_combinations.add(base_command.name)
                    for a in base_command.aliases:
                        self.bot.available_command_combinations.add(a)

                def recurse(c):
                    for sc in c.commands:
                        self.bot.available_command_combinations.add(f'{c.name} {sc.name}')
                        for a in sc.aliases:
                            self.bot.available_command_combinations.add(f'{c.name} {a}')
                        if isinstance(sc, commands.Group):
                            recurse(sc)

                recurse(base_command)

            else:
                self.bot.available_command_combinations.add(base_command.name)
                for a in base_command.aliases:
                    self.bot.available_command_combinations.add(a)


    async def _send_to_webhook(self, webhook_url: str, webhook_name: str, **embed_kwargs) -> None:
        webhook = Webhook.from_url(webhook_url, adapter=AsyncWebhookAdapter(self.bot.AIOHTTP_SESSION))
        await webhook.send(
            embed=self.bot.default_embed(**embed_kwargs),
            avatar_url=self.bot.ICON,
            username=webhook_name
        )


    @commands.Cog.listener('on_message')
    async def snipe(self, message: Message):
        if (
            not self._been_ready
            or message.author == self.bot.user
            or message.channel == self.bot.LOG_CHANNEL
        ):
            return

        guild = message.guild.id if message.guild else None
        content = message.content

        with suppress(HTTPException):
            start = time.perf_counter()
            if self.bot.SNIPING_nitro_state:
                if guild in self.bot.SNIPING_nitro_exclusions:
                    return

                nitro_code = GIFT_REGEX.search(content)
                if nitro_code:
                    nitro_code = nitro_code.group(2)
                    if nitro_code in self._known_nitro:
                        return

                    r = self._urllib3_session.request('POST', f'{self.bot.API_URL}entitlements/gift-codes/{nitro_code}/redeem', headers=default_headers(self.bot))
                    r = json.loads(r.data.decode('utf-8'))
                    elapsed = round((time.perf_counter() - start) * 1000, 2)

                    if r['code'] == 50050:
                        await self.bot.log(f'{elapsed}ms - Nitro snipe failed: already redeemed', 'info', url=message.jump_url)
                    elif r['code'] == 10038:
                        await self.bot.log(f'{elapsed}ms - Nitro snipe failed: invalid nitro code', 'info', url=message.jump_url)
                    elif r.get('subscription_plan'):
                        data = r['subscription_plan']
                        price = str(data['price'])[0] + ','+ str(data['price'])[1:] + data['currency']
                        await self.bot.log(f'{elapsed}ms - Nitro snipe successful: {price} nitro redeemed', url=message.jump_url)

                    self._known_nitro.add(nitro_code)

            if self.bot.SNIPING_token_state:
                if guild in self.bot.SNIPING_token_exclusions:
                    return

                discord_token = TOKEN_REGEX.search(content)
                if discord_token:
                    discord_token = discord_token.group()
                    if discord_token in self._known_tokens:
                        return

                    elapsed = round((time.perf_counter() - start) * 1000, 2)
                    await self.bot.log(f'{elapsed}ms - Token sniped: {discord_token}', url=message.jump_url)
                    self._known_tokens.add(discord_token)

            if self.bot.SNIPING_privnote_state:
                privnote_code = PRIVNOTE_REGEX.search(content)
                if guild in self.bot.SNIPING_privnote_exclusions:
                    return

                if privnote_code:
                    privnote_code = privnote_code.group(2)
                    if privnote_code in self._known_privnote:
                        return

                    note_content = pn.read_note(f'https://privnote.com/{privnote_code}')
                    with open(Path(f'data/privnotes/privnote-{privnote_code}.txt'), 'w', encoding='utf-8') as f:
                        f.write(note_content)

                    elapsed = round((time.perf_counter() - start) * 1000, 2)
                    await self.bot.log(f'{elapsed}ms - Privnote sniped. Contents have been stored in `data//privnotes//privnote-{privnote_code}.txt`', url=message.jump_url)
                    self._known_privnote.add(privnote_code)

            if self.bot.SNIPING_giveaway_state:
                if message.embeds and message.author.bot:
                    content = (content + (str(message.embeds[0].to_dict()))).lower()
                    if 'giveaway' in content and not 'ban' in content:
                        if guild in self.bot.SNIPING_giveaway_exclusions:
                            return

                        await asyncio.sleep(randrange(80, 100))
                        if message.reactions:
                            # Choose emote that was most reacted
                            emote = max(
                                [(r.emoji, (await r.users().flatten())) for r in message.reactions],
                                key=lambda item: len(item[1])
                            )[0]
                            await message.add_reaction(emote)
                            elapsed = round((time.perf_counter() - start) / 60, 2)
                            await self.bot.log(f'{elapsed}m (delayed) - Giveaway joined with emote {emote}', url=message.jump_url)


    @commands.Cog.listener()
    async def on_required_action_update(self, required_action: RequiredActionType):
        actions = {
            RequiredActionType.accept_terms: 'accept the Discord TOS',
            RequiredActionType.verify_phone: 'verify your account with phone',
            RequiredActionType.verify_email: 'verify your account with email',
            RequiredActionType.captcha: 'complete a captcha'
        }
        cls()
        lines('red')
        print(f'{Fore.RED}\n [!] Disconnected from websocket: You need to {actions[required_action]}.\n')
        lines('red')
        sys.exit()


    @commands.Cog.listener()
    async def on_command(self, ctx):
        ctx.command.invoke_time = time.perf_counter()


    def _should_dm_log(self, message: Message) -> bool:
        return self.bot.DMLOG_state and self.bot.DMLOG_state and isinstance(message.channel, (GroupChannel, DMChannel)) and not message.author.bot and message.content and message.author != self.bot.user

    @commands.Cog.listener('on_message_edit')
    async def dm_edit_log(self, before: Message, after: Message):
        if self._should_dm_log(before):
            beforec = utils.remove_markdown(before.content)
            afterc = utils.remove_markdown(after.content)
            if beforec != afterc:
                await self._send_to_webhook(
                    self.bot.DMLOG_webhook_url,
                    'DM Logger',
                    title=f'Message edited by: {str(before.author)}',
                    description=f'**Before:** ```{shorten(beforec, 950)}```\n**After:** ```{shorten(afterc, 950)}```\n[**Jump**]({after.jump_url})'
                )

    @commands.Cog.listener('on_message_delete')
    async def dm_delete_log(self, message: Message):
        if self._should_dm_log(message):
            await self._send_to_webhook(
                self.bot.DMLOG_webhook_url,
                'DM Logger',
                title=f'Message deleted by: {str(message.author)}',
                description=f'**Content:** ```{shorten(message.clean_content, 1900)}```\n[**Jump**]({message.jump_url})'
            )


    def _should_guild_log(self, message: Message) -> bool:
        return self.bot.GUILDLOG and message.guild and not message.author.bot and message.author != self.bot.user and message.content

    @commands.Cog.listener('on_message_edit')
    async def guild_edit_log(self, before: Message, after: Message):
        if self._should_guild_log(before):
            beforec = utils.remove_markdown(before.clean_content)
            afterc = utils.remove_markdown(after.clean_content)
            if beforec != afterc:
                data = {
                    'author_name': str(after.author),
                    'channel_name': after.channel.name,
                    'guild_name': after.guild.name,
                    'guild_id': after.guild.id,
                    'created_at': after.created_at,
                    'clean_content_before': fill(beforec, width=150),
                    'clean_content_after': fill(afterc, width=150)
                }
                self.bot.GUILD_EDIT_LOG.append(data)

    @commands.Cog.listener('on_message_delete')
    async def guild_delete_log(self, message: Message):
        if self._should_guild_log(message):
            data = {
                'author_name': str(message.author),
                'channel_name': message.channel.name,
                'guild_name': message.guild.name,
                'guild_id': message.guild.id,
                'created_at': message.created_at,
                'clean_content': fill(utils.remove_markdown(message.clean_content), width=150)
            }
            self.bot.GUILD_DELETE_LOG.append(data)


    @commands.Cog.listener('on_message')
    async def keyword_log(self, message: Message):
        if message.author == self.bot.user:
            return

        if self.bot.KEYWORDLOG_state:
            if any(keywords := [kw for kw in self.bot.KEYWORDLOG_keywords if kw.casefold() in utils.remove_markdown(message.content.casefold())]):
                await self._send_to_webhook(
                    self.bot.KEYWORDLOG_webhook_url,
                    'Keyword Logger',
                    title=f'Keyword detected from {str(message.author)}',
                    description=f"**Keyword(s):** {', '.join(keywords)}\n[**Jump**]({message.jump_url})"
                )


    @commands.Cog.listener()
    async def on_relationship_update(self, before: Relationship, after: Relationship):
        if self.bot.NOTIFICATIONS_state:
            if before.type in {RelationshipType.outgoing_request, RelationshipType.incoming_request} and after.type is RelationshipType.friend:
                await self._send_to_webhook(
                    self.bot.NOTIFICATIONS_webhook_url,
                    'Notifications',
                    title='Friend Added',
                    description=f'You are now friends with {after.user}'
                )

    @commands.Cog.listener()
    async def on_relationship_remove(self, relationship: Relationship):
        if self.bot.NOTIFICATIONS_state:
            if not relationship.user.is_friend() and relationship.type is RelationshipType.friend:
                await self._send_to_webhook(
                    self.bot.NOTIFICATIONS_webhook_url,
                    'Notifications',
                    title='Friend Removed',
                    description=f'You are no longer friends with {relationship.user}'
                )

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        if self.bot.NOTIFICATIONS_state:
            await self._send_to_webhook(
                self.bot.NOTIFICATIONS_webhook_url,
                'Notifications',
                title='Guild Joined',
                description=f'You are now in the server {guild}'
            )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        if self.bot.NOTIFICATIONS_state:
            await self._send_to_webhook(
                self.bot.NOTIFICATIONS_webhook_url,
                'Notifications',
                title='Guild Removed',
                description=f'You are no longer in the server {guild}'
            )


    @commands.Cog.listener('on_message')
    async def auto_delete_prefixed(self, message: Message):
        if message.author != self.bot.user:
            return

        if message.content.startswith(self.bot.PREFIXES + self.bot.RAID_PREFIXES):
            with suppress(HTTPException):
                await message.delete()


    @commands.Cog.listener('on_message')
    async def count_words(self, message: Message):
        self.bot.WORD_COUNTER[message.channel.id].update(message.content.split())
        if message.author == self.bot.user:
            if guild := message.guild:
                self.bot.MESSAGE_COUNT[guild.id] += 1
            elif channel := message.channel:
                self.bot.MESSAGE_COUNT[channel.id] += 1


    def _should_mark(self, message: Message) -> bool:
        return message.author != self.bot.user and message.embeds and message.content == '' and not message.author.bot and message.author.id not in self._known_selfbot

    @commands.Cog.listener('on_message')
    async def mark_selfbot_user(self, message: Message):
        if self._should_mark(message):
            await self.bot.log(
                f'{str(message.author)} has been detected as a selfbot user',
                'info',
                url=message.jump_url
            )
            self._known_selfbot.add(message.author.id)


    @commands.Cog.listener('on_guild_channel_delete')
    async def snipe_delete_channel(self, channel):
        with suppress(KeyError):
            del self.bot.MESSAGE_SNIPES[channel.id]

    @commands.Cog.listener('on_message_delete')
    async def snipe_delete_message(self, message: Message):
        if not message.author.bot:
            if message.content:
                if message.author != self.bot.user:
                    self.bot.MESSAGE_SNIPES[message.channel.id] = message

    @commands.Cog.listener('on_message')
    async def protections_warn_for_admin(self, message: Message):
        if message.author == self.bot.user:
            return

        author = message.author
        if author.public_flags.staff:
            if self.bot.PROTECTIONS_warn_for_admin:
                if author.id not in self._known_admins:
                    await self._send_to_webhook(
                        self.bot.PROTECTIONS_webhook_url,
                        'Admin Protection',
                        description=f'{message.author.mention} is a Discord employee\n[**Jump**]({message.jump_url})'
                    )
                    self._known_admins.add(author.id)

    @commands.Cog.listener('on_message')
    async def protections_anti_ping(self, message: Message):
        if message.author == self.bot.user:
            return

        author = message.author
        if self.bot.PROTECTIONS_anti_spam_ping_state:
            if self.bot.user in message.mentions:
                if not (author.is_friend() if self.bot.PROTECTIONS_anti_spam_ping_exclude_friends else False):
                    if not author.is_blocked():
                        if self._anti_spam_ping_cds[author.id].is_ratelimited():
                            calls = self.bot.PROTECTIONS_anti_spam_ping_calls
                            period = self.bot.PROTECTIONS_anti_spam_ping_period
                            await author.block()
                            await self._send_to_webhook(
                                self.bot.PROTECTIONS_webhook_url,
                                'Ping Protection',
                                description=f'{author} exceeded the allowed rate of {int(calls / period * 60)} pings per minute, and has been blocked'
                            )

    @commands.Cog.listener('on_group_join')
    async def protections_anti_spam_groupchat(self, channel: GroupChannel, user: User):
        author = channel.owner
        if self.bot.PROTECTIONS_anti_spam_groupchat_state:
            if user == self.bot.user:
                if not author.is_blocked():
                    if self._anti_spam_group_cds[author.id].is_ratelimited():
                        calls = self.bot.PROTECTIONS_anti_spam_groupchat_calls
                        period = self.bot.PROTECTIONS_anti_spam_groupchat_period
                        await author.block()
                        await self._send_to_webhook(
                            self.bot.PROTECTIONS_webhook_url,
                            'Spam Group Protection',
                            description=f'{author} exceeded the allowed rate of {int(calls / period * 60)} group adds per minute, and has been blocked'
                        )

    @commands.Cog.listener('on_relationship_add')
    async def protections_anti_spam_friend(self, relationship: Relationship):
        if self.bot.PROTECTIONS_anti_spam_friend_state:
            if relationship is RelationshipType.incoming_request:
                if not self.bot.user.settings.friend_source_flags is FriendFlags.noone:
                    if self._anti_spam_friend_cd.is_ratelimited():
                        calls = self.bot.PROTECTIONS_anti_spam_friend_calls
                        period = self.bot.PROTECTIONS_anti_spam_friend_period
                        await self.bot.user.edit_settings(friend_source_flags=FriendFlags.noone)
                        await self._send_to_webhook(
                            self.bot.PROTECTIONS_webhook_url,
                            'Spam Friend Protection',
                            description=f'Exceeded the allowed rate of {int(calls / period * 60)} friend adds per minute. Changed settings to not allow anybody to add you'
                        )

    @commands.Cog.listener('on_private_channel_create')
    async def protections_anti_spam_dm(self, channel: Union[GroupChannel, DMChannel]):
        if self.bot.PROTECTIONS_anti_spam_dm_state:
            if isinstance(channel, DMChannel):
                if not channel.recipient.is_friend():
                    if not self.bot.user.settings.default_guilds_restricted and not self.bot.user.settings.restricted_guilds:
                        if self.anti_spam_dm_cd.is_ratelimited():
                            calls = self.bot.PROTECTIONS_anti_spam_dm_calls
                            period = self.bot.PROTECTIONS_anti_spam_dm_period
                            await self.bot.user.edit_settings(default_guilds_restricted=True, restricted_guilds=[g.id for g in self.bot.guilds])
                            await self._send_to_webhook(
                                self.bot.PROTECTIONS_webhook_url,
                                'Spam DM Protection',
                                description=f'Exceeded the allowed rate of {int(calls / period * 60)} new dm channels made per minute. Changed settings to not allow anybody to send you dms'
                            )


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error: Exception):
        exc = None
        if isinstance(error, commands.MissingRequiredArgument):
            par = error.param.name
            sig = ctx.command.signature
            arr = (sig.index(par) + len(par) // 2) * ' ' + '^'
            exc = f'`{par}`\n```prolog\n{sig.replace(par, par.capitalize())}\n{arr}```'

        elif isinstance(error, commands.CommandNotFound):
            s = ctx.message.content

            for p in ctx.bot.PREFIXES:
                s = s.replace(p, '')

            c = s.split()

            if isinstance(ctx.command, commands.Group):
                c = ' '.join(c[0:2])
            else:

                c = c[0]
            exc = f'The command `{c}` was not found'
            if closest := get_close_matches(c, self.bot.available_command_combinations, 1):
                exc += f'\nDid you mean `{closest[0]}`?'

        elif isinstance(error, commands.MissingPermissions):
            exc = ', '.join([p.replace('_', ' ').title() for p in error.missing_perms])

        elif isinstance(error, commands.NoPrivateMessage):
            exc = 'This command can only be used in a guild.'

        elif isinstance(error, commands.MaxConcurrencyReached):
            exc = f'You can only run {error.num} instance(s) of this command at once.'

        elif isinstance(error, NoPasswordSet):
            exc = 'No password was set in the config file, which is required to use this command.'

        elif isinstance(error, OnlyDM):
            exc = 'This command can only be used in a group channel or direct message.'

        elif isinstance(error, CommandExists):
            exc = f'The command `{error.name}` already exists as a commandname/alias, so can\'t be used as a custom command name.'

        elif isinstance(error, CommandDoesntExist):
            exc = f'The command `{error.name}` doesn\'t exist as a custom command.'

        elif isinstance(error, NoFFMPEG):
            exc = f'FFMPEG wasn\'t found on your computers PATH environment. Install it to be able to use this command.'

        elif isinstance(error, InvalidExtension):
            exc = f'The extension `{error.name}` doesn\'t exist; choose `nsfw`, `moderation`, `games` or `all`.'

        elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            exc = f'The member/user {error.argument} was not found in the bot\'s cache (Discord limitation).'

        elif isinstance(error, commands.ConversionError):
            exc = f'In {error.converter.__name__}: {str(error.original)}'

        elif isinstance(error, Forbidden):
            exc = '403: You don\'t have the permissions to do this.'

        elif isinstance(error, NotFound):
            exc = '404: Something was not found (maybe it was deleted?).'

        else:
            exc = shorten(str(error), 1999) or 'Something went wrong'

        arrow = '\u279F'
        error_message = f"{f'On {ctx.command.qualified_name} {arrow}  ' if ctx.command else ''}{type(error).__name__}: {exc}"
        await self.bot.log(error_message, 'error')

        if self.bot.ERRORINFO:
            await ctx.respond(error_message, title='Error')

        with open(Path('data/logs/error.log'), 'a', encoding='utf-8') as f:
            f.write(f"At {datetime.now().strftime('%H:%M:%S')} {error_message}\n")


    @commands.Cog.listener()
    async def on_connect(self):
        if not self._been_ready:
            self._been_ready = True
            # Globally used variables that require state to be set
            self.bot.AIOHTTP_SESSION = aiohttp.ClientSession(connector=aiohttp.TCPConnector(loop=self.bot.loop, ssl=False))
            self.bot.START_TIME = datetime.now()
            [self.bot.DEFAULT_LISTENERS] = list(filter(None, [c.get_listeners() for c in self.bot.cogs.values()]))
            self.bot.LOG_GUILD = self.bot.get_guild(int(self.bot.LOGGING_GUILD_ID))
            cls()

            if not self.bot.LOG_GUILD:
                cls()
                lines('red')
                print(f'{Fore.RED}\n [!] Invalid logging server ID. Restart the bot and fix your settings.\n')
                lines('red')
                change_config(('LOGGING_GUILD',))
                sys.exit()

            if not self.bot.LOG_GUILD.system_channel:
                cls()
                lines('red')
                print(f'{Fore.RED}\n [!] No systemchannel was found in the logging guild. Set one in the guilds settings.\n')
                lines('red')
                sys.exit()

            if not any((self.bot.EMBED_colour, self.bot.EMBED_footer_text, self.bot.EMBED_footer_icon, self.bot.EMBED_autodelete)) and self.bot.EMBED_state:
                cls()
                lines('red')
                print(f'{Fore.RED}\n [!] Insufficient embed settings. Restart the bot and fix your settings.\n')
                lines('red')
                change_config(('EMBED', 'state'))
                sys.exit()

            try:
                self.bot.LOG_CHANNEL = self.bot.LOG_GUILD.system_channel
                for wh in await self.bot.LOG_CHANNEL.webhooks():
                    await wh.delete()
                self.bot.LOG_WEBHOOK = await self.bot.LOG_CHANNEL.create_webhook(name=f'{self.bot.user.name} logging')
            except HTTPException:
                cls()
                lines('red')
                print(f'{Fore.RED}\n [!] Something went wrong when trying to create/delete the logging webhook! (Do you own your logging server?)\n')
                lines('red')
                sys.exit()

            print(Style.BRIGHT + Fore.MAGENTA + '''
                ██████╗ ███████╗ █████╗ ███████╗███████╗██████╗     ███████╗██████╗
               ██╔════╝ ██╔════╝██╔══██╗╚══███╔╝██╔════╝██╔══██╗    ██╔════╝██╔══██╗
               ██║  ███╗█████╗  ███████║  ███╔╝ █████╗  ██████╔╝    ███████╗██████╔╝
               ██║   ██║██╔══╝  ██╔══██║ ███╔╝  ██╔══╝  ██╔══██╗    ╚════██║██╔══██╗
               ╚██████╔╝███████╗██║  ██║███████╗███████╗██║  ██║    ███████║██████╔╝
                ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝    ╚══════╝╚═════╝''' + Style.DIM + Fore.MAGENTA + f'   {self.bot.VERSION}')
            lines()

            get_state = lambda s: f'{Fore.GREEN}enabled' if s else f'{Fore.RED}disabled'
            top = f' {Style.BRIGHT + Fore.MAGENTA}•{Fore.WHITE} '
            sub = f'     {Style.DIM + Fore.MAGENTA}▪{Fore.WHITE} '

            print(f'{top}Logged in as: {self.bot.user}')
            print(f'{top}Logging to: {self.bot.LOG_GUILD} > #{self.bot.LOG_CHANNEL}')
            print(f'{top}Commands: {len(list(self.bot.walk_commands()))}')
            print(f'{top}Prefix(es): {shorten(", ".join(self.bot.PREFIXES), 90)}')
            print(f'{top}Error info: {get_state(self.bot.ERRORINFO)}')
            print(f'{top}Notifications: {get_state(self.bot.NOTIFICATIONS_state)}')
            print(f'{top}DM Log: {get_state(self.bot.DMLOG_state)}')
            print(f'{top}Guild Log: {get_state(self.bot.GUILDLOG)}')
            print(f'{top}Keyword Log: {get_state(self.bot.KEYWORDLOG_state)}')

            print(f'{top}RPC: {get_state(self.bot.RPC_state)}')
            if self.bot.RPC_state:
                print(f'{sub}Status: {shorten(self.bot.RPC_name, 90)}')
                print(f'{sub}Details: {shorten(self.bot.RPC_details, 90)}')
                print(f'{sub}Large tooltip: {shorten(self.bot.RPC_large_text, 90)}')
                print(f'{sub}Small tooltip: {shorten(self.bot.RPC_small_text, 90)}')
                print(f'{sub}Large image: {shorten(self.bot.RPC_large_image, 90)}')
                print(f'{sub}Small image: {shorten(self.bot.RPC_small_image, 90)}')

            print(f'{top}Embed: {get_state(self.bot.EMBED_state)}')
            if self.bot.EMBED_state:
                print(f'{sub}Colour: {self.bot.EMBED_colour}')
                print(f'{sub}Autodelete: {precisedelta(self.bot.EMBED_autodelete, format="%0.0f")}')
                print(f'{sub}Footer text: {shorten(self.bot.EMBED_footer_text, 90)}')
                print(f'{sub}Showspeed: {get_state(self.bot.EMBED_showspeed)}')

            em, eg, en = self.bot.EXTENSIONS_moderation, self.bot.EXTENSIONS_games, self.bot.EXTENSIONS_nsfw
            exts = any((em, eg, en))
            print(f'{top}Extensions: {get_state(exts)}')
            if exts:
                print(f'{sub}Moderation: {get_state(em)}')
                print(f'{sub}Games: {get_state(eg)}')
                print(f'{sub}NSFW: {get_state(en)}')

            sns, sps, sgs, sts = self.bot.SNIPING_nitro_state, self.bot.SNIPING_privnote_state, self.bot.SNIPING_giveaway_state, self.bot.SNIPING_token_state
            sniping = any((sns, sps, sgs, sts))
            print(f'{top}Sniping: {get_state(sniping)}')
            if sniping:
                print(f'{sub}Nitro: {get_state(sns)}')
                print(f'{sub}Privnote: {get_state(sps)}')
                print(f'{sub}Giveaway: {get_state(sgs)}')
                print(f'{sub}Token: {get_state(sts)}')

            pwfa, pasps, pasgs, pasfs, pasds = self.bot.PROTECTIONS_warn_for_admin, self.bot.PROTECTIONS_anti_spam_ping_state, self.bot.PROTECTIONS_anti_spam_groupchat_state, self.bot.PROTECTIONS_anti_spam_friend_state, self.bot.PROTECTIONS_anti_spam_dm_state
            protections = any((pwfa, pasps, pasgs, pasfs, pasds))
            print(f'{top}Protections: {get_state(protections)}')
            if protections:
                print(f'{sub}Admin: {get_state(pwfa)}')
                print(f'{sub}Ping: {get_state(pasps)}')
                print(f'{sub}Groupchat: {get_state(pasgs)}')
                print(f'{sub}Friend: {get_state(pasfs)}')
                print(f'{sub}DM: {get_state(pasds)}')

            lines()
            await self.bot.log(f'Selfbot logged in. Welcome {self.bot.user.name}!')
            self._update_all_commands()


def setup(bot):
    bot.add_cog(Events(bot))
