#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Buster#5741'
__maintainer__ = 'Buster#5741'
__version__ = '3.0.0 (beta)'

import asyncio
import json
import logging
import os
import re
import sys
import time
from contextlib import suppress
from datetime import datetime
from functools import cached_property
from io import BytesIO, StringIO
from pathlib import Path
from textwrap import fill, indent
from typing import Dict, List, Optional, Set, Tuple, Union

import pkg_resources

with open('../requirements.txt', encoding='utf-8') as f:
    dependencies = f.readlines()
try:
    pkg_resources.require(dependencies)
except pkg_resources.DistributionNotFound as not_found:
    print('-' * 105)
    m = f'\n [!] Package {not_found.req} was not found.'
    if os.name == 'nt':
        m += 'Close the cmd and run install.bat as administrator!\n'
    else:
        m += 'Run python3.8 -m pip install -r requirements.txt in console!\n'
    print(m)
    print('-' * 105)
    sys.exit()
except:
    pass

import aiohttp
from colorama import Fore, Style, init
from discord import (Attachment, ClientUser, Embed, File, Guild, HTTPException,
                     LoginFailure, Member, Message, User, Webhook,
                     WebhookMessage, utils)
from discord.ext import commands
from pypresence import Presence, PyPresenceException

from cogs.utils.effects import use_polaroid
from cogs.utils.exceptions import BadSettings
from cogs.utils.helpers import change_config
from cogs.utils.regexes import MD_URL_REGEX
from cogs.utils.tokens import DAGPI_TOKEN
from cogs.utils.wizard import config_setup, lines

init(autoreset=True)

discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.INFO)
fh = logging.FileHandler(
    filename=Path('data/logs/discord.log'),
    encoding='utf-8',
    mode='w'
)
fh.setFormatter(logging.Formatter(
    'At %(asctime)s -> %(levelname)s:%(name)s: %(message)s',
    '%H:%M:%S'
))
discord_logger.addHandler(fh)


class CustomContext(commands.Context):
    async def respond(self, message: str = '', image: str = Embed.Empty, **kwargs) -> Union[Message, WebhookMessage]:
        '''Sends a command response.
        This can be embedded or not depending on settings/perms, and be send to the current channel or the log channel.

        Args:
            message (str, optional): The primary message to send. Defaults to ''.
            image (str, optional): The image to send. Defaults to Embed.Empty.
            thumbnail (str, optional): The thumbnail to send. Defaults to Embed.Empty.
            title (str, optional): The embed title. Defaults to None.
            show_speed (bool, optional): Whether to show the process speed in the command. Defaults to True.
            mention_self (bool, optional): Whether to mention sb user in content
            send_to_log (bool, optional): Whether to send the message to the log channel instead of current. Defaults to False.
            do_delete (bool, optional): Whether to delete the message after after time provided by user setting. Defaults to True.
            fields (List[Tuple[str, str, Optional[bool]]]): The embed fields to include. Defaults to None.
            files (Union[List[File], File]): The files to upload along with the message. Defaults to None.

        Raises:
            BadSettings: Raised when the user has insufficient embed settings

        Returns:
            Union[Message, WebhookMessage]: The message that was send as a result of this function
        '''
        embeds_enabled = self.bot.EMBED_state
        colour, footer_text, footer_icon, auto_delete = self.bot.EMBED_colour, self.bot.EMBED_footer_text, self.bot.EMBED_footer_icon, self.bot.EMBED_autodelete
        if embeds_enabled is True:
            if not any((colour, footer_text, footer_icon, auto_delete)):
                raise BadSettings('You enabled embeds, but the settings are insufficient. Set them with the embedsets command.')

        thumbnail: str = kwargs.get('thumbnail', Embed.Empty)
        title: str = kwargs.get('title')
        send_to_log: bool = kwargs.get('send_to_log', False)
        mention_self: bool = kwargs.get('mention_self', False)
        show_speed: bool = kwargs.get('show_speed', True)
        if show_speed:
            if invoke_time := getattr(self.command, 'invoke_time', None):
                footer_text += f' | took {(time.perf_counter() - invoke_time) * 1000:.0f}ms'
        do_delete: bool = kwargs.get('do_delete', True)
        fields: List[Tuple[str, str, Optional[bool]]] = kwargs.get('fields')
        files: Union[List[File], File] = kwargs.get('files', [])
        files = [files] if not isinstance(files, list) else files

        me = self.guild.me if self.guild else self.bot.user
        destination = self.channel if not send_to_log else self.bot.LOG_WEBHOOK
        icon = self.bot.ICON if isinstance(destination, Webhook) else None
        delete_after = (int(auto_delete)
                       if (do_delete and (isinstance(auto_delete, int))
                       and not isinstance(destination, Webhook)) else None)

        content, embed = '', None
        if message and len(message) < 2000:
            content += f'{message}\n'
        elif message and self.channel.permissions_for(me).attach_files:
            files.append(await self.textfile(message, send=False))
            message = 'Output directed to textfile (over 2000 characters)'
        else:
            message = message[:2000]
            content += f'{message}\n'

        # Either no perms to embed, or sending in embeds is disabled
        if not self.channel.permissions_for(me).embed_links or embeds_enabled is False:
            # Add image urls, not empty or if they denote
            # a file image
            if ims := [
                    im for im in (image, thumbnail)
                    if im != Embed.Empty
                    and not str(im).startswith('attachment://')
                ]:
                for im in ims:
                    content += f'{im}\n'

            # Add fields
            if fields:
                for field in fields:
                    if field[1]:
                        content += f'**{field[0]}:**\n{field[1]}\n'

            # Extract actual URL and don't embed it from
            # markdown urls
            content = re.sub(MD_URL_REGEX, r'<\2>', content)

        # Embeds are enabled, and there are perms to use them
        else:
            content = None

            # TODO: Check for valid colour on start up
            try:
                converted_colour = await commands.ColourConverter().convert(self, colour)
            except commands.BadColourArgument:
                raise BadSettings('The colour you provided for your embed is invalid! Choose a HEX, or a name found in https://geazersb.github.io/valid_colours.png.')

            title = title or self.command.qualified_name.replace('_', ' ').title()
            image = image or f'https://singlecolorimage.com/get/{str(colour)[1:]}/400x4'

            embed = Embed(
                title=title,
                timestamp=datetime.utcnow(),
                colour=converted_colour,
                description=message
            ).set_footer(
                text=footer_text,
                icon_url=footer_icon
            ).set_image(
                url=image
            ).set_thumbnail(
                url=thumbnail
            )

            # Add fields
            if fields:
                # Pad fields to even rows of 3
                # to properly align them
                if not fields[-1][-1] is False:
                    while len(fields) % 3:
                        fields.append(('\u200b', '\u200b'))

                for field in fields:
                    if field[1] not in (None, ''):
                        try:
                            inline = field[2]
                        except IndexError:
                            inline = True

                        embed.add_field(
                            name=field[0],
                            value=field[1],
                            inline=inline
                        )

        if mention_self:
            content = f"{self.me.mention}\n{content or ''}"

        # Only pass kwargs that have values
        # to the destination.send method
        to_send = dict(filter(
            lambda item: item[1] is not None,
            {
                'content': content,
                'embed': embed,
                'files': files,
                'avatar_url': icon,
                'delete_after': delete_after
            }.items()
        ))
        return await destination.send(**to_send)


    async def dagpi(self, endpoint: str, params: dict = None, index: int = None) -> Message:
        url = f'https://api.dagpi.xyz/{endpoint}'
        if endpoint.startswith('image/'):
            url += '/'

        r = await self.bot.AIOHTTP_SESSION.get(
            url,
            headers={'Authorization': DAGPI_TOKEN},
            timeout=aiohttp.ClientTimeout(total=20),
            params=params
        )

        if endpoint.startswith('image/'):
            ctt = r.content_type.lower()
            if ctt == 'image/gif':
                ft = 'gif'
            elif ctt == 'image/png':
                ft = 'png'
            else:
                raise commands.BadArgument((await r.json())['message'])

            fp = await r.content.read()
            fn = endpoint.split('/')[1]
            _file = File(BytesIO(fp), f"{fn}.{ft}")
            return await self.respond(image=f"attachment://{fn}.{ft}", files=_file)

        return await self.respond([str(v) for v in (await r.json()).values()][index])


    async def polaroid(self, method_name: str, link: str, *args) -> Message:
        b = await self.bot.get_bytes(link)
        _file, ft = use_polaroid(b, method_name, *args)
        return await self.respond(image=f'attachment://{method_name}.{ft}', files=_file)


    async def textfile(
        self,
        content: str,
        filename: str = 'output.txt',
        *,
        send: bool = True,
        clean: bool = True
    ) -> Union[File, Message]:
        s = StringIO()
        if clean:
            content = utils.remove_markdown(content)
        s.write(content)
        s.seek(0)
        _file = File(s, filename)
        if not send:
            return _file
        return await self.send(file=_file)


class CustomBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._BotBase__cogs = commands.core._CaseInsensitiveDict() # Case insensitive cogs for help command
        self.ICON: str = 'https://geazersb.github.io/logo.gif'
        self.API_URL: str = 'https://discordapp.com/api/v8/'
        self.COMMANDS_USED: int = 0
        self.VERSION: str = __version__
        self.HELP_MESSAGE: Message = None # HelpCommand subclass does not hold state
        self.HELP_TASK: asyncio.Task = None
        self.SOCKET_STATS: dict = {
            100: { # not a real opcode
                'name': 'RAW_SEND',
                'counter': int()
            },
            101: { # not a real opcode
                'name': 'RAW_RECEIVED',
                'counter': int()
            },
            1: {
                'name': 'HEARTBEAT',
                'counter': int()
            },
            2: {
                'name': 'IDENTIFY',
                'counter': int()
            },
            3: {
                'name': 'PRESENCE_UPDATE',
                'counter': int()
            },
            4: {
                'name': 'VOICE_STATE_UPDATE',
                'counter': int()
            },
            5: {
                'name': 'VOICE_PING',
                'counter': int()
            },
            6: {
                'name': 'RESUME',
                'counter': int()
            },
            7: {
                'name': 'RECONNECT',
                'counter': int()
            },
            8: {
                'name': 'REQUEST_GUILD_MEMBERS',
                'counter': int()
            },
            9: {
                'name': 'INVALID_SESSION',
                'counter': int()
            },
            10: {
                'name': 'HELLO',
                'counter': int()
            },
            11: {
                'name': 'HEARTBEAT_ACK',
                'counter': int()
            }
        }
        self.EXTENSIONS: dict = {
            'Abuse',
            'Events',
            'Fun',
            'Help',
            'Images',
            'Info',
            'IPTools',
            'Other',
            'Raid',
            'Text',
            'Trolling',
            'Utilities',
            'Media',
            'Misc'
        }

        with open(Path('data/json/config.json'), encoding='utf-8') as config_file:
            config = json.load(config_file)

        self.TOKEN: str = config['DISCORD_TOKEN']
        self.LOGGING_GUILD_ID: int = config['LOGGING_GUILD']
        self.command_prefix: list = config['PREFIXES']
        self.PREFIXES: Tuple[str] = tuple(config['PREFIXES'])
        self.PASSWORD: str = config['PASSWORD']
        self.ERRORINFO: bool = config['ERRORINFO']
        self.GUILDLOG: bool = config['GUILDLOG']

        setting = config['SNIPING']
        self.SNIPING_nitro_state: bool = setting['nitro']['state']
        self.SNIPING_nitro_exclusions: Set[int] = set(setting['nitro']['exclusions'])
        self.SNIPING_privnote_state: bool = setting['privnote']['state']
        self.SNIPING_privnote_exclusions: Set[int] = set(setting['privnote']['exclusions'])
        self.SNIPING_token_state: bool = setting['token']['state']
        self.SNIPING_token_exclusions: Set[int] = set(setting['token']['exclusions'])
        self.SNIPING_giveaway_state: bool = setting['giveaway']['state']
        self.SNIPING_giveaway_exclusions: Set[int] = set(setting['giveaway']['exclusions'])

        setting = config['DMLOG']
        self.DMLOG_state: bool = setting['state']
        self.DMLOG_webhook_url: str = setting['webhook_url']

        setting = config['KEYWORDLOG']
        self.KEYWORDLOG_state: bool = setting['state']
        self.KEYWORDLOG_webhook_url: str = setting['webhook_url']
        self.KEYWORDLOG_keywords: Set[str] = set(setting['keywords'])

        setting = config['EMBED']
        self.EMBED_state: bool = setting['state']
        self.EMBED_showspeed: bool = setting['showspeed']
        self.EMBED_colour: str = setting['colour']
        self.EMBED_footer_text: str = setting['footer_text']
        self.EMBED_footer_icon: str = setting['footer_icon']
        self.EMBED_autodelete: int = setting['autodelete']

        setting = config['RPC']
        self.RPC_state: bool = setting['state']
        self.RPC_clientid: int = setting['clientid']
        self.RPC_name: str = setting['name']
        self.RPC_details: str = setting['details']
        self.RPC_large_text: str = setting['large_text']
        self.RPC_small_text: str = setting['small_text']
        self.RPC_large_image: str = setting['large_image']
        self.RPC_small_image: str = setting['small_image']
        self.RPC_buttons: List[Dict[str, str]] = setting['buttons']

        setting = config['EXTENSIONS']
        self.EXTENSIONS_moderation: bool = setting['moderation']
        self.EXTENSIONS_games: bool = setting['games']
        self.EXTENSIONS_nsfw: bool = setting['nsfw']

        setting = config['NOTIFICATIONS']
        self.NOTIFICATIONS_state: bool = setting['state']
        self.NOTIFICATIONS_webhook_url: str = setting['webhook_url']

        setting = config['PROTECTIONS']
        self.PROTECTIONS_webhook_url: str = setting['webhook_url']
        self.PROTECTIONS_warn_for_admin: bool = setting['warn_for_admin']
        self.PROTECTIONS_anti_spam_ping_state: bool = setting['anti_spam_ping']['state']
        self.PROTECTIONS_anti_spam_ping_exclude_friends: bool = setting['anti_spam_ping']['exclude_friends']
        self.PROTECTIONS_anti_spam_ping_calls: int = setting['anti_spam_ping']['calls']
        self.PROTECTIONS_anti_spam_ping_period: int = setting['anti_spam_ping']['period']
        self.PROTECTIONS_anti_spam_groupchat_state: bool = setting['anti_spam_groupchat']['state']
        self.PROTECTIONS_anti_spam_groupchat_calls: int = setting['anti_spam_groupchat']['calls']
        self.PROTECTIONS_anti_spam_groupchat_period: int = setting['anti_spam_groupchat']['period']
        self.PROTECTIONS_anti_spam_friend_state: bool = setting['anti_spam_friend']['state']
        self.PROTECTIONS_anti_spam_friend_calls: int = setting['anti_spam_friend']['calls']
        self.PROTECTIONS_anti_spam_friend_period: int = setting['anti_spam_friend']['period']
        self.PROTECTIONS_anti_spam_dm_state: bool = setting['anti_spam_dm']['state']
        self.PROTECTIONS_anti_spam_dm_calls: int = setting['anti_spam_dm']['calls']
        self.PROTECTIONS_anti_spam_dm_period: int = setting['anti_spam_dm']['period']


    @cached_property
    def RAID_PREFIXES(self) -> Tuple[str]:
        return tuple([p + 'r' for p in self.PREFIXES])


    def default_embed(self, **kwargs) -> Embed:
        return Embed(
            **kwargs,
            colour=0x0d1b94,
            timestamp=datetime.utcnow()
        ).set_footer(text='Geazer Selfbot', icon_url=self.ICON)


    async def get_context(self, message: Message, *, cls=None):
        return await super().get_context(message, cls=cls or CustomContext)


    async def on_socket_raw_send(self, _: bytes):
        self.SOCKET_STATS[100]['counter'] += 1


    async def on_socket_raw_receive(self, _: bytes):
        self.SOCKET_STATS[101]['counter'] += 1


    async def on_socket_response(self, message: dict):
        if event := self.SOCKET_STATS.get(message['op']):
            event['counter'] += 1


    async def get_bytes(self, item) -> bytes:
        if isinstance(item, Attachment):
            return await item.read()

        if isinstance(item, (User, Member, ClientUser)):
            item = str(item.avatar_url_as(static_format='png'))

        elif isinstance(item, Guild):
            item = str(item.icon_url_as(static_format='png'))

        async with bot.AIOHTTP_SESSION.get(item) as response:
            return await response.read()


    async def log(
        self,
        message: str,
        severity: str = 'success',
        url: str = None,
        **kwargs
    ) -> None:
        '''Will log a message to the system channel of the logging server and print it in console

        Args:
            message (str): The message to log
            severity (str, optional): The severity of the log. Defaults to success.
            url (str, optional): The URL to link the log to. Defaults to None.
        '''
        if severity == 'error':
            prefix = ' [!]'
            p_colour = Fore.RED
            e_colour = 0xCE0002
            message = message.replace('prolog\n', '') # missingrequiredarguments uses this to format colour in code block
        elif severity == 'info':
            prefix = ' [*]'
            p_colour = Fore.WHITE
            e_colour = 0x808080
        elif severity == 'success':
            prefix = ' [√]'
            p_colour = Fore.GREEN
            e_colour = 0x00FF21

        print(f"{Style.BRIGHT}{p_colour}{prefix}{indent(fill(utils.remove_markdown(message), 100), ' ')}")

        embed = Embed(
            title=severity.capitalize(),
            description=message,
            timestamp=datetime.utcnow(),
            colour=e_colour
        ).set_footer(text='Geazer Selfbot', icon_url=self.ICON)

        if url:
            embed.description += f'\n[**Jump**]({url})'

        try:
            await self.LOG_WEBHOOK.send(
                embed=embed,
                avatar_url=self.ICON,
                **kwargs
            )
        except HTTPException:
            lines('red')
            print(f'{Fore.RED}\n [!] Couldn\'t log to logging webhook.\n')
            lines('red')


bot = CustomBot(
    command_prefix='!',
    self_bot=True,
    case_insensitive=True,
    chunk_guilds_at_startup=True
)


def rcp_setup():
    if bot.RPC_state is True:
        try:
            RPC = Presence(bot.RPC_clientid)
            RPC.connect()
            RPC.update(
                state=bot.RPC_name,
                details=bot.RPC_details,
                small_image=bot.RPC_small_image,
                large_image=bot.RPC_large_image,
                small_text=bot.RPC_small_text,
                large_text=bot.RPC_large_text,
                start=datetime.now().timestamp(),
                buttons=bot.RPC_buttons
            )
        except PyPresenceException as e:
            lines('red')
            print(f'{Fore.RED}\n [!] Failed to launch RPC. Restart the bot and fix your settings.\n Error: {e}\n')
            lines('red')
            change_config(('RPC', 'state'))
            sys.exit()


def cog_setup():
    if bot.EXTENSIONS_moderation:
        bot.EXTENSIONS.add('Moderation')
    if bot.EXTENSIONS_games:
        bot.EXTENSIONS.add('Games')
    if bot.EXTENSIONS_nsfw:
        bot.EXTENSIONS.add('NSFW')

    for extension in bot.EXTENSIONS:
        with suppress(commands.ExtensionNotFound):
            bot.load_extension(f'cogs.{extension}')
            print(f'{Fore.GREEN} [*] Loaded cog {extension}')


def custom_command_setup():
    with open(Path('data/json/customcommands.json'), encoding='utf-8') as commands_file:
        customcommands = json.load(commands_file)

    bot.CUSTOM_COMMANDS = {}
    if not customcommands:
        print(f'{Fore.GREEN} [*] No custom commands to load')
        return

    for cc in customcommands:
        data = customcommands[cc]
        content = data.get('content', 'No message provided.')
        delete_after = data.get('delete_after')
        embedded = data.get('embedded', False)
        aliases = data.get('aliases', [])
        bot.CUSTOM_COMMANDS[cc] = {
            'content': content,
            'delete_after': delete_after,
            'embedded': embedded,
            'aliases': aliases
        }
        try:
            @bot.command(cc, hidden=True, aliases=aliases)
            async def _(ctx, content=content, delete_after=delete_after, embedded=embedded):
                if embedded:
                    await ctx.respond(content, show_speed=False)
                else:
                    await ctx.send(content, delete_after=delete_after)
            print(f'{Fore.GREEN} [*] Loaded custom command {cc}')
        except commands.CommandRegistrationError:
            lines('red')
            print(f'{Fore.RED}\n [!] {cc} already exists as an existing command name or alias. Rename it in data/json/customcommands.json\n')
            lines('red')
            sys.exit()


def run():
    config_setup()
    cog_setup()
    lines()
    custom_command_setup()
    rcp_setup()
    lines()
    print(f'{Fore.WHITE} [*] Waiting for Discord websocket...')
    lines()
    try:
        bot.run(bot.TOKEN)
    except LoginFailure:
        lines('red')
        print(f'{Fore.RED}\n [!] Invalid Discord token. Restart the bot and fix your settings.\n')
        lines('red')
        change_config(('DISCORD_TOKEN',))
        with suppress(Exception):
            sys.exit()


if __name__ == '__main__':
    run()
