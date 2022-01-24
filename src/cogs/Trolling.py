# -*- coding: utf-8 -*-
import asyncio
from base64 import b64encode
from contextlib import suppress
from datetime import datetime
from functools import reduce
from itertools import cycle
from pathlib import Path
from random import choice, choices
from textwrap import dedent
from typing import Optional, Union

from discord import (Embed, Forbidden, GroupChannel, Guild, HTTPException,
                     Member, Message, PartialEmoji, TextChannel, User,
                     VoiceState, utils)
from discord.ext import commands

from .utils.checks import bot_has_permissions, dm_only
from .utils.converters import MultiChannelConverter, TimeConverter
from .utils.helpers import (get_blank_message, random_string, self_edit,
                            sentence_to_cancer)
from .utils.tokens import GINGER_TOKEN


class Trolling(commands.Cog):
    '''Category will all trolling related commands. Most of these are listeners that perform actions on certain events.'''

    def __init__(self, bot):
        self.bot = bot

        self._cloneuser_settings = dict()
        self._automove_enabled = bool()
        self._massping_enabled = bool()
        self._blank_guild_guildid = int()
        self._automute_memberids = set()
        self._autodeafen_memberids = set()
        self._autodisconnect_memberids = set()
        self._autopin_userids = set()

        self._noleave_userids = set()
        self._noleave_channelid = int()

        self._nojoin_userids = set()
        self._nojoin_channelid = int()

        self._annoy_user_userids = set()
        self._annoy_user_emotes = tuple()
        self._annoy_channel_channelid = int()
        self._annoy_channel_emotes = tuple()

        self._grammarnazi_check = None
        self._grammarnazi_cooldown = commands.CooldownMapping.from_cooldown(1, 8, commands.BucketType.guild)
        self._grammarnazi_platitudes = cycle((
            '\n> {wrong}\nlol, do you mean "{corrected}"??',
            'spelling "{corrected}" like "{wrong}" :joy:',
            'its "{corrected}" :clown:',
            '{corrected}\*, not {wrong} :rolling_eyes:'
        ))
        self._grammarnazi_connectors = cycle((
            ' and ',
            ' also ',
            ' not to mention ',
            ', '
        ))

        self._autorespond_user_userid = int()
        self._autorespond_channel_channelid = int()
        self._autorespond_channel_message = str()
        self._autorespond_user_message = str()

        self._step_userid = int()
        self._step_message = None

        self._autonick_memberids = set()
        self._autonick_nickname = str()

        self._invisible_username = str()
        self._invisible_avatar = bytes()

        self._mee6_username = str()
        self._mee6_avatar = bytes()

        self._imitate_user_userids = int()
        self._imitate_channel_channelid = int()
        self._imitate_user_cancerify_enabled = bool()
        self._imitate_channel_cancerify_enabled = bool()


    async def _check_grammar(self, text: str) -> Optional[str]:
        text = utils.remove_markdown(text)
        params = {
            'lang': 'US',
            'clientVersion': '2.0',
            'text': text,
            'apiKey': GINGER_TOKEN
        }
        r = await (await self.bot.AIOHTTP_SESSION.get(
            "https://services.gingersoftware.com/Ginger/correct/jsonSecured/GingerTheTextFull",
            params=params
        )).json()

        if not r['Sentences'][0]['IsEnglish'] or not r['Corrections']:
            return

        formatted = []
        for suggestion in r['Corrections']:
            start, end = suggestion['From'], suggestion['To']
            if suggestion['Suggestions']:
                suggest = suggestion['Suggestions'][0]
                if suggest.get('Text'):
                    formatted.append(
                        next(self._grammarnazi_platitudes).format(
                            corrected=suggest['Text'],
                            wrong=text[start:end + 1]
                    ))

        if formatted:
            # Have to do this to actually get the next in cycle
            # for each item in formatted, with join it will just
            # use the same
            return reduce(
                lambda a, b: next(self._grammarnazi_connectors).join((a, b)),
                formatted
            )

        return None


    @commands.command(aliases=['gp'])
    async def ghostping(self, ctx, user: User, all_channels: bool = False):
        '''Will ghostping <user> optionally in [all_channels]'''
        gp = lambda c: (await (await c.send(user.mention)).delete() for _ in '_').__anext__()
        await gp(ctx.channel)
        if all_channels and ctx.guild:
            for tc in ctx.guild.text_channels:
                await gp(tc)


    @commands.command(aliases=['expose', 'tokencalc'])
    async def calculatetoken(self, ctx, user: User):
        '''Will calculate someones discord token (last parts random)'''
        p1 = str(b64encode(str(user.id).encode('utf-8')), 'utf-8')
        p2, p3 = random_string(5), random_string(27)
        msg = dedent(f'''
            **Token:** {p1}.{p2}.{p3}
            **User:** {user.mention}
            **ID:** {user.id}
        ''')
        await ctx.respond(msg, title='Calculate Token')


    @commands.command(aliases=['longmention'])
    async def glitchmention(self, ctx, length: int = 1900):
        '''Will send a [length] long mention looking message'''
        await ctx.respond(f"<@{''.join(choices('0123456789', k=length))}>")


    @commands.command(aliases=['faketype', 'triggertyping'])
    async def typing(self, ctx, time: TimeConverter = 60, channel: MultiChannelConverter = None):
        '''Will make it look like you are typing in [channel] for [time]'''
        channel = channel or ctx.channel
        max_time = datetime.utcnow().timestamp() + time
        async with channel.typing():
            while datetime.utcnow().timestamp() < max_time:
                await asyncio.sleep(10)


    @bot_has_permissions(embed_links=True)
    @commands.command(
        aliases=['fakegif', 'fakenitro'],
        usage='<customurl (the url that shows)> <gifurl (the url that is send through favourites)>',
        brief='Trolling/freenitro'
    )
    async def freenitro(self, ctx, channel: Optional[TextChannel], customurl: str = 'https://cdn.discordapp.com/attachments/758068250943684718/759918983524384799/tenor-min.gif', gifurl: str = 'https://cdn.discordapp.com/attachments/758041075855392860/759911640170364938/wumpus.gif'):
        '''Will send an embedded Discord CDN gif that if added to favourites will send the customurl gif instead.'''
        channel = channel or ctx.channel
        msg = dedent('''
            *React fast! This event won't last forever!*

            1. Hover over the top right of the GIF image

            2. Click the star ⭐ that says 'Add to favorites'

            3. Open the Discord GIF menu and navigate to Favorites

            4. Send the newly added GIF by clicking 🖱️ on it

            5. All done! You'll receive your free nitro subscription soon after 🥳!
        ''')
        embed = Embed(
            title='Free Nitro Event!',
            url=customurl,
            description=msg,
            colour=7506394
        ).set_image(url=gifurl)
        if channel.permissions_for(ctx.me).manage_webhooks:
            wh = await channel.create_webhook(name='Wumpus Webhook')
            await wh.send(embed=embed, username='Wumpus', avatar_url='https://cdn.discordapp.com/attachments/812282759150174228/895624783767691274/wumpus.gif')
            await wh.delete()
        else:
            await channel.send(embed=embed)


    @commands.command(aliases=['leftedit'])
    async def editpos(self, ctx, *, message: str):
        '''Will send a <message> with glitched edited tag'''
        message = f'\u202b {message} \u202b'
        msg = await ctx.send(message)
        await msg.edit(content=' ' + message)


    @commands.command()
    async def spam(self, ctx, amount: Optional[int] = 10, *, message: str):
        '''Will send <message> [amount] times in a row'''
        for _ in range(amount):
            await ctx.send(message)


    @commands.command(aliases=['pin'])
    async def spampins(self, ctx, limit: Optional[int] = 10, channel: MultiChannelConverter = None):
        '''Will pin latest [limit] messages in [channel]'''
        channel = channel or ctx.channel
        async for message in channel.history(before=ctx.message, limit=limit):
            with suppress(HTTPException):
                await message.pin()


    @commands.group(invoke_without_command=True, aliases=['uclone'])
    async def cloneuser(self, _):
        '''Group command for starting/stopping cloneuser'''
        raise commands.CommandNotFound()

    @cloneuser.command('start')
    async def cloneuser_start(self, ctx, user: Union[Member, User]):
        '''Will copy <user>'s pfp/username in DM + role if in a guild'''
        avatar = await user.avatar_url.read()
        self._cloneuser_settings = {
            'avatar': await ctx.me.avatar_url.read(),
            'nick': ctx.me.display_name,
            'username': ctx.me.name
        }
        if isinstance(user, Member):
            activity = user.activity if not getattr(user.activity, 'application_id', False) else None
            await self.bot.change_presence(activity=activity, status=user.status)
            await self_edit(ctx, avatar=avatar, nick=user.display_name)
        else:
            await self_edit(ctx, avatar=avatar, username=user.name)

    @cloneuser.command('stop', aliases=['revert', 'cancel', 'reset'])
    async def cloneuser_stop(self, ctx):
        '''Will revert back to original pfp/nick/username'''
        await self_edit(ctx, **self._cloneuser_settings)


    @commands.group(invoke_without_command=True, aliases=['spamping', 'massmention'])
    async def massping(self, _):
        '''Group command for starting/stopping massping in servers'''
        raise commands.CommandNotFound()

    @commands.guild_only()
    @massping.command('start')
    async def massping_start(self, ctx):
        '''Will start masspinging everybody in current server'''
        await ctx.guild.subscribe()
        chunked = [ctx.guild.members[i:i + 50] for i in range(len(ctx.guild.members), 50)]
        await self.bot.log(f'Starting massping in {ctx.guild}...')
        self._massping_enabled = True
        while self._massping_enabled:
            for group in chunked:
                if not self._massping_enabled:
                    break
                try:
                    await ctx.send(' '.join(map(lambda m: m.mention, group))[:1999])
                except HTTPException:
                    await self.bot.log('Couldn\'t find online people to ping', 'error')
                    self._massping_enabled = False
                    break

    @massping.command('stop', aliases=['cancel'])
    async def massping_stop(self, _):
        '''Will stop masspinging'''
        self._massping_enabled = False
        await self.bot.log('Stopped massping')


    @commands.group(invoke_without_command=True)
    async def autopin(self, _):
        '''Group command for starting/stopping autopin'''
        raise commands.CommandNotFound()

    async def _auto_pin(self, message: Message):
        if message.author.id in self._autopin_userids:
            try:
                await message.pin()
            except Forbidden:
                self.bot.remove_listener(self._auto_pin, 'on_message')

    @bot_has_permissions(manage_messages=True)
    @autopin.command('start', aliases=['user'])
    async def autopin_start(self, _, *users: User):
        '''Will start pinning every message by [users...]'''
        self._autopin_userids = {u.id for u in users}
        self.bot.add_listener(self._auto_pin, 'on_message')
        await self.bot.log(f"Started autopin listener for user(s): {', '.join([str(u) for u in users])}")

    @autopin.command('stop')
    async def autopin_stop(self, _):
        '''Will stop the autopin listener'''
        self.bot.remove_listener(self._auto_pin, 'on_message')
        await self.bot.log('Stopped autopin listener')


    @commands.group(invoke_without_command=True)
    async def autodeafen(self, _):
        '''Group command for starting/stopped autodeafen'''
        raise commands.CommandNotFound()

    async def _auto_deafen(self, member: Member, before: VoiceState, after: VoiceState):
        if member.id in self._autodeafen_memberids:
            if before.deaf and not after.deaf:
                try:
                    await member.edit(deafen=True)
                except Forbidden:
                    self.bot.remove_listener(self._auto_deafen, 'on_voice_state_update')

    @commands.guild_only()
    @bot_has_permissions(deafen_members=True)
    @autodeafen.command('start', aliases=['user'])
    async def autodeafen_start(self, _, *members: Member):
        '''Will automatically deafen [members...] after undeafening'''
        self._autodeafen_memberids = {m.id for m in members}
        for m in members:
            await m.edit(deafen=True)
        self.bot.add_listener(self._auto_deafen, 'on_voice_state_update')
        await self.bot.log(f"Started autodeafen listener for member(s): {', '.join([str(m) for m in members])}")

    @autodeafen.command('stop')
    async def autodeafen_stop(self, _):
        '''Will stop the autodeafen listener'''
        self.bot.remove_listener(self._auto_deafen, 'on_voice_state_update')
        await self.bot.log('Stopped autodeafen listener')


    @commands.group(invoke_without_command=True)
    async def autodisconnect(self, _):
        '''Group command for starting/stopping autodisconnect'''
        raise commands.CommandNotFound()

    async def _auto_disconnect(self, member: Member, before: VoiceState, after: VoiceState):
        if member.id in self._autodisconnect_memberids:
            if after is not before and after.channel:
                try:
                    await member.move_to(None)
                except Forbidden:
                    self.bot.remove_listener(self._auto_disconnect, 'on_voice_state_update')

    @commands.guild_only()
    @bot_has_permissions(move_members=True)
    @autodisconnect.command('start', aliases=['user'])
    async def autodisconnect_start(self, _, *members: Member):
        '''Will automatically kick [members...] from a voicechannel on joining'''
        self._autodisconnect_memberids = {m.id for m in members}
        for m in members:
            await m.move_to(None)
        self.bot.add_listener(self._auto_disconnect, 'on_voice_state_update')
        await self.bot.log(f"Started autodisconnect listener for member(s): {', '.join([str(m) for m in members])}")

    @autodisconnect.command('stop')
    async def autodisconnect_stop(self, _):
        '''Will stop the autodisconnect listener'''
        self.bot.remove_listener(self._auto_disconnect, 'on_voice_state_update')
        await self.bot.log('Stopped autodisconnect listener')


    @commands.group(invoke_without_command=True)
    async def automove(self, _):
        '''Group command for starting/stopping automove'''
        raise commands.CommandNotFound()

    @commands.guild_only()
    @bot_has_permissions(move_members=True)
    @automove.command('start', aliases=['user'])
    async def automove_start(self, ctx, members: commands.Greedy[Member], delay: TimeConverter = 1):
        '''Will start moving [members...] to random voice channels every [delay]s'''
        self._automove_enabled = True
        await self.bot.log(f"Started automove for member(s): {', '.join([str(m) for m in members])}")
        while self._automove_enabled:
            for m in members:
                channel = choice(ctx.guild.voice_channels)
                await m.move_to(channel)
            await asyncio.sleep(delay)

    @automove.command('stop')
    async def automove_stop(self, _):
        '''Will stop automoving'''
        self._automove_enabled = False
        await self.bot.log('Stopped automove')


    @commands.group(invoke_without_command=True)
    async def automute(self, _):
        '''Group command for starting/stopping automute'''
        raise commands.CommandNotFound()

    async def _auto_mute(self, member: Member, before: VoiceState, after: VoiceState):
        if member.id in self._automute_memberids:
            if before.mute and not after.mute:
                try:
                    await member.edit(mute=True)
                except Forbidden:
                    self.bot.remove_listener(self._auto_mute, 'on_voice_state_update')

    @commands.guild_only()
    @bot_has_permissions(mute_members=True)
    @automute.command('start', aliases=['user'])
    async def automute_start(self, _, *members: Member):
        '''Will automatically mute [member...] after unmuting'''
        self._automute_memberids = {m.id for m in members}
        for m in members:
            await m.edit(mute=True)
        self.bot.add_listener(self._auto_mute, 'on_voice_state_update')
        await self.bot.log(f"Started automute listener for member(s): {', '.join([str(m) for m in members])}")

    @automute.command('stop')
    async def automute_stop(self, _):
        '''Will stop the automute listener'''
        self.bot.remove_listener(self._auto_mute, 'on_voice_state_update')
        await self.bot.log('Stopped automute listener')


    @commands.group(invoke_without_command=True)
    async def blank(self, ctx, length: int = None):
        '''Group command for sending ~2000 char long whitespace message'''
        await ctx.send(get_blank_message(self.bot, length))

    async def _blank_guild(self, message: Message):
        if message.guild.id == self._blank_guild_guildid:
            if message.author != self.bot.user:
                try:
                    await message.channel.send(get_blank_message(self.bot))
                except HTTPException:
                    self.bot.remove_listener(self._blank_guild, 'on_message')

    @blank.command('guild')
    async def blank_guild(self, ctx, server: Guild = None):
        '''Will send a ~2000 blank after every message in [server]'''
        guild = server or ctx.guild
        self._blank_guild_guildid = guild.id
        self.bot.add_listener(self._blank_guild, 'on_message')
        await self.bot.log(f'Started blank listener for server {ctx.guild}')

    @blank.command('stop')
    async def blank_stop(self, _):
        '''Will stop the blank listener'''
        self.bot.remove_listener(self._blank_guild, 'on_message')
        await self.bot.log('Stopped blank guild listener')


    @commands.group(invoke_without_command=True, aliases=['autoadd'])
    async def noleave(self, _):
        '''Group command for starting/stopping noleave'''
        raise commands.CommandNotFound()

    async def _no_leave(self, channel: GroupChannel, user: User):
        if user.id in self._noleave_userids:
            if channel.id == self._noleave_channelid:
                try:
                    await channel.add_recipients(user)
                except HTTPException:
                    self._noleave_userids.discard(user.id)

    @dm_only()
    @noleave.command('start', aliases=['user'])
    async def noleave_start(self, ctx, *users: User):
        '''Will add [users...] back to the group channel on leaving'''
        if users := [u for u in users if u.is_friend()]:
            self._noleave_userids = {u.id for u in users}
            self._noleave_channelid = ctx.channel.id
            await ctx.channel.add_recipients(*users)
            self.bot.add_listener(self._no_leave, 'on_group_remove')
            await self.bot.log(f"Started noleave listener for user(s): {', '.join([str(u) for u in users])}")
        else:
            await self.bot.log('Couldn\'t start noleave, none of the user(s) are friends with you', 'error')

    @noleave.command('stop')
    async def noleave_stop(self, _):
        '''Will stop the noleave listener'''
        self.bot.remove_listener(self._no_leave, 'on_group_remove')
        await self.bot.log('Stopped noleave listener')


    @commands.group(invoke_without_command=True, aliases=['autokick'])
    async def nojoin(self, _):
        '''Group command for starting/stopping nojoin'''
        raise commands.CommandNotFound()

    async def _no_join(self, channel: GroupChannel, user: User):
        if user.id in self._nojoin_userids:
            if channel.id == self._nojoin_channelid:
                try:
                    await channel.remove_recipients(user)
                except HTTPException:
                    self._nojoin_userids.discard(user.id)

    @dm_only()
    @nojoin.command('start', aliases=['user'])
    async def nojoin_start(self, ctx, *users: User):
        '''Will kick [users...] from the group channel on joining'''
        if users := [u for u in users if u.is_friend()]:
            self._nojoin_userids = {u.id for u in users}
            self._nojoin_channelid = ctx.channel.id
            await ctx.channel.remove_recipients(*users)
            self.bot.add_listener(self._no_join, 'on_group_join')
            await self.bot.log(f"Started nojoin listener for user(s): {', '.join([str(u) for u in users])}")
        else:
            await self.bot.log('Couldn\'t start nojoin, none of the user(s) are friends with you', 'error')

    @nojoin.command('stop')
    async def nojoin_stop(self, _):
        '''Will stop the nojoin listener'''
        self.bot.remove_listener(self._no_join, 'on_group_join')
        await self.bot.log('Stopped nojoin listener')


    @commands.group(invoke_without_command=True, aliases=['autoreact'])
    async def annoy(self, _):
        '''Group command for starting/stopping annoy'''
        raise commands.CommandNotFound()

    async def _annoy_user(self, message: Message):
        if message.author.id in self._annoy_user_userids:
            for e in self._annoy_user_emotes:
                with suppress(HTTPException):
                    await message.add_reaction(e)

    @bot_has_permissions(add_reactions=True)
    @annoy.command('user', brief='Trolling/annoy_user')
    async def annoy_user(self, _, users: commands.Greedy[User], *emojis: Union[PartialEmoji, str]):
        '''Will react with [emojis...] to every message by [users]...'''
        self._annoy_user_userids = {u.id for u in users}
        self._annoy_user_emotes = emojis or ('🤡',)
        self.bot.add_listener(self._annoy_user, 'on_message')
        await self.bot.log(f"Started annoy listener for user(s): {', '.join([str(u) for u in users])}")

    async def _annoy_channel(self, message: Message):
        if message.channel.id == self._annoy_channel_channelid:
            if message.author != self.bot.user:
                for e in self._annoy_channel_emotes:
                    with suppress(HTTPException):
                        await message.add_reaction(e)

    @bot_has_permissions(add_reactions=True)
    @annoy.command('channel')
    async def annoy_channel(self, ctx, channel: MultiChannelConverter = None, *emojis: Union[PartialEmoji, str]):
        '''Will react with [emojis...] to every message in [channel]'''
        self._annoy_channel_channelid = channel.id or ctx.channel.id
        self._annoy_channel_emotes = emojis or ('🤡',)
        self.bot.add_listener(self._annoy_channel, 'on_message')
        await self.bot.log(f'Started annoy listener for channel {channel}')

    @annoy.command('stop')
    async def annoy_stop(self, _):
        '''Will stop all annoy listeners'''
        self.bot.remove_listener(self._annoy_user, 'on_message')
        self.bot.remove_listener(self._annoy_channel, 'on_message')
        await self.bot.log('Stopped annoy listener(s)')


    @commands.group(invoke_without_command=True, aliases=['autocorrect'])
    async def grammarnazi(self, _):
        '''Group command for starting/stopping grammarnazi'''
        raise commands.CommandNotFound()

    async def _grammarnazi_event(self, message: Message):
        if self._grammarnazi_check(message):
            bucket = self._grammarnazi_cooldown.get_bucket(message)
            if not bucket.update_rate_limit():
                if corrected := await self._check_grammar(message.clean_content):
                    await message.reply(corrected)
                else:
                    self._grammarnazi_cooldown._cache.clear()

    @bot_has_permissions(add_reactions=True)
    @grammarnazi.command('user')
    async def grammarnazi_user(self, _, *users: User):
        '''Will correct grammar and spelling for every message by [users...]'''
        self._grammarnazi_check = lambda m: m.author in users
        self.bot.add_listener(self._grammarnazi_event, 'on_message')
        await self.bot.log(f"Started grammarnazi listener for user(s): {', '.join([str(u) for u in users])}")

    @bot_has_permissions(add_reactions=True)
    @grammarnazi.command('channel')
    async def grammarnazi_channel(self, ctx, channel: MultiChannelConverter = None):
        '''Will correct grammar and spelling for every message in [channel]'''
        self._grammarnazi_check = lambda m: m.channel == channel or ctx.channel
        self.bot.add_listener(self._grammarnazi_event, 'on_message')
        await self.bot.log(f'Started grammarnazi listener for channel {channel}')

    @grammarnazi.command('stop')
    async def grammarnazi_stop(self, _):
        '''Will stop all grammarnazi listeners'''
        self.bot.remove_listener(self._grammarnazi_event, 'on_message')
        await self.bot.log('Stopped grammarnazi listener(s)')


    @commands.group(invoke_without_command=True, aliases=['autoreply'])
    async def autorespond(self, _):
        '''Group command for starting/stopping autorespond'''
        raise commands.CommandNotFound()

    async def _auto_respond_user(self, message: Message):
        if message.author.id == self._autorespond_user_userid:
            with suppress(HTTPException):
                await message.reply(self._autorespond_user_message)

    @autorespond.command('user', brief='Trolling/autorespond_user')
    async def autorespond_user(self, _, user: User, *, message: str):
        '''Will autorespond to every <users>'s message with <message>'''
        self._autorespond_user_userid, self._autorespond_user_message = user.id, message
        self.bot.add_listener(self._auto_respond_user, 'on_message')
        await self.bot.log(f'Started autorespond listener for user {user}')

    async def _auto_respond_channel(self, message: Message):
        if message.channel.id == self._autorespond_channel_channelid:
            if message.author != self.bot.user:
                with suppress(HTTPException):
                    await message.channel.send(self._autorespond_channel_message)

    @autorespond.command('channel')
    async def autorespond_channel(self, _, channel: MultiChannelConverter, *, message: str):
        '''Will autorespond to everybody in <channel> with <message>'''
        self._autorespond_channel_channelid, self._autorespond_channel_message = channel.id, message
        self.bot.add_listener(self._auto_respond_channel, 'on_message')
        await self.bot.log(f'Started autorespond listener for channel {channel}')

    @autorespond.command('stop')
    async def autorespond_stop(self, _):
        '''Will stop all autorespond listeners'''
        self.bot.remove_listener(self._auto_respond_user, 'on_message')
        self.bot.remove_listener(self._auto_respond_channel, 'on_message')
        await self.bot.log('Stopped autorespond listener(s)')


    @commands.group(
        invoke_without_command=True,
        aliases=['stepthrough'],
        brief='Trolling/step'
    )
    async def step(self, _):
        '''Group command for starting/stopping step'''
        raise commands.CommandNotFound()

    async def _step_user(self, message: Message):
        if message.author.id == self._step_userid:
            await message.channel.send(next(self._step_message))

    @step.command('start', aliases=['user'])
    async def step_start(self, _, user: User, *message: str):
        '''Will step through <message> by sending it word for word after every message by <user>'''
        self._step_userid, self._step_message = user.id, cycle(message)
        self.bot.add_listener(self._step_user, 'on_message')
        await self.bot.log(f'Started step listener for user {user}')

    @step.command('stop')
    async def step_stop(self, _):
        '''Will stop all step listeners'''
        self.bot.remove_listener(self._step_user, 'on_message')
        await self.bot.log('Stopped step listener')


    @commands.group(invoke_without_command=True)
    async def autonick(self, _):
        '''Group command for starting/stopping autonick'''
        raise commands.CommandNotFound()

    async def _auto_nick(self, before: Member, after: Member):
        if before.id in self._autonick_memberids:
            if before.nick != after.nick and after.nick != self._autonick_nickname:
                try:
                    await after.edit(nick=self._autonick_nickname)
                except Forbidden:
                    self.bot.remove_listener(self._auto_nick, 'on_member_update')

    @commands.guild_only()
    @bot_has_permissions(manage_nicknames=True)
    @autonick.command('start', aliases=['user'])
    async def autonick_start(self, _, members: commands.Greedy[Member], *, nickname: str):
        '''Will automatically nick [members...] after changing'''
        self._autonick_memberids = {m.id for m in members}
        self._autonick_nickname = nickname
        for m in members:
            await m.edit(nick=nickname)
        self.bot.add_listener(self._auto_nick, 'on_member_update')
        await self.bot.log(f"Added autonick listener for member(s): {', '.join([str(m) for m in members])}")

    @autonick.command('stop')
    async def autonick_stop(self, _):
        '''Will stop the autonick listener'''
        self.bot.remove_listener(self._auto_nick, 'on_member_update')
        await self.bot.log('Removed autonick listener')


    @commands.group(invoke_without_command=True)
    async def invisible(self, _):
        '''Group command for starting/stopping invisible'''
        raise commands.CommandNotFound()

    @invisible.command('start')
    async def invisible_start(self, ctx):
        '''Will change your username and pfp to be blank'''
        with open(Path('data/assets/images/empty.png'), 'rb') as f:
            image_bytes = f.read()

        self._invisible_username = self.bot.user.name
        self._invisible_avatar = await self.bot.user.avatar_url.read()
        await self_edit(ctx, avatar=image_bytes, username=('\U00001cbc' * 32))

    @invisible.command('stop')
    async def invisible_stop(self, ctx):
        '''Will change your username and pfp back to original'''
        await self_edit(ctx, avatar=self._invisible_avatar, username=self._invisible_username)


    @commands.group(invoke_without_command=True)
    async def mee6(self, _):
        '''Group command for starting/stopping mee6'''
        raise commands.CommandNotFound()

    @mee6.command('start')
    async def mee6_start(self, ctx):
        '''Will change your username and pfp to mee6'''
        with open(Path('data/assets/images/mee6.png'), 'rb') as f:
            image_bytes = f.read()

        self._mee6_username = self.bot.user.name
        self._mee6_avatar = await self.bot.user.avatar_url.read()
        await self_edit(ctx, avatar=image_bytes, username='MEE6\U00001cbc')

    @mee6.command('stop')
    async def mee6_stop(self, ctx):
        '''Will change your username and pfp back to original'''
        await self_edit(ctx, avatar=self._mee6_avatar, username=self._mee6_username)


    @commands.group(aliases=['mimic', 'copy'], invoke_without_command=True)
    async def imitate(self, _):
        '''Group command for starting/stopping imitate'''
        raise commands.CommandNotFound()

    async def _imitate_user(self, message: Message):
        if message.author.id in self._imitate_user_userids:
            with suppress(HTTPException):
                content = message.content
                if self._imitate_user_cancerify_enabled:
                    content = sentence_to_cancer(content)
                await message.channel.send(content)

    @imitate.command('user', brief='Trolling/imitate_user')
    async def imitate_user(self, _, users: commands.Greedy[User], cancerify: bool = False):
        '''Will copy every message by [users]...'''
        self._imitate_user_userids = {u.id for u in users}
        self._imitate_user_cancerify_enabled = cancerify
        self.bot.add_listener(self._imitate_user, 'on_message')
        await self.bot.log(f"Started imititate listener on user(s): {', '.join(map(str, users))}{' and cancerifying it' if cancerify else ''}")

    async def _imitate_channel(self, message: Message):
        if message.channel.id == self._imitate_channel_channelid:
            if message.author != self.bot.user:
                with suppress(HTTPException):
                    msg = sentence_to_cancer(message.content) if self._imitate_channel_cancerify_enabled else message.content
                    await message.channel.send(msg)

    @imitate.command('channel')
    async def imitate_channel(self, ctx, channel: MultiChannelConverter = None, cancerify: bool = False):
        '''Will copy everybody in [channel]'''
        self._imitate_channel_channelid = channel.id or ctx.channel.id
        self._imitate_channel_cancerify_enabled = cancerify
        self.bot.add_listener(self._imitate_channel, 'on_message')
        await self.bot.log(f'Started imitate listener on channel {channel}')

    @imitate.command('stop')
    async def imitate_stop(self, _):
        '''Will stop all imitate listeners'''
        self.bot.remove_listener(self._imitate_user, 'on_message')
        self.bot.remove_listener(self._imitate_channel, 'on_message')
        await self.bot.log('Stopped imitate listener(s)')


def setup(bot):
    bot.add_cog(Trolling(bot))
