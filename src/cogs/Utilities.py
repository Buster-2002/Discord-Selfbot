# -*- coding: utf-8 -*-
import asyncio
import json
import re
from collections import defaultdict
from contextlib import suppress
from datetime import datetime, timedelta
from difflib import get_close_matches
from pathlib import Path
from random import randrange
from textwrap import dedent, fill, shorten
from typing import Optional, Union

import async_cse
import chat_exporter
import pyPrivnote as pn
from discord import (Activity, ActivityType, CategoryChannel, DMChannel, Guild,
                     HTTPException, Member, Message, Role, Status, TextChannel,
                     User, VoiceChannel, utils)
from discord.ext import commands, tasks
from humanize import intcomma, naturalday, naturaldelta, precisedelta

from .utils import flags
from .utils.checks import bot_has_permissions
from .utils.converters import (CountryConverter, CurrencyConverter,
                               DateConverter, ImageConverter,
                               LanguageConverter, MultiChannelConverter,
                               TimeConverter)
from .utils.exceptions import BadTime, DataNotFound
from .utils.helpers import (default_headers, format_date, random_string,
                            self_edit)
from .utils.tokens import CURRCONV_TOKEN, GOOGLE_TOKENS, NEWSAPI_TOKEN


class Utilities(commands.Cog):
    '''Category with all utility related commands.'''

    def __init__(self, bot):
        self.bot = bot

        self._afkmode_blacklist = set()
        self._afkmode_message = str()
        self._afkmode_only_dms_enabled = bool()
        self._reminders = dict()
        self._sleep_tasks = dict()
        self._loop_tasks = dict()
        self._autodel_messages = defaultdict(list)
        self._autodel_limit = int()
        self._google_client = async_cse.Search(GOOGLE_TOKENS)


    @staticmethod
    async def _send_crypto(ctx, cd: str, amount: str = None, coin: str = None) -> None:
        cd = cd.lower()
        r = await (await ctx.bot.AIOHTTP_SESSION.get(f'https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies={cd}&include_24hr_change=true&include_last_updated_at=true')).json()
        if amount:
            value = r[coin][cd]
            msg = f"{amount}{cd} is equivalent to {amount / value:.5f} {coin}"
        else:
            data = r[coin]
            msg = dedent(f'''
                **Value (1 {coin}):** {data[cd]:.2f}{cd}
                **24h change:** {data[f'{cd}_24h_change']:.1f}%
                **Last updated:** ~{format_date(data['last_updated_at'])}
            ''')
        await ctx.respond(msg)


    @staticmethod
    async def _copy_channel(channel: Union[TextChannel, VoiceChannel], copy_to: Guild, category: CategoryChannel = None) -> None:
        if isinstance(channel, VoiceChannel):
            await copy_to.create_voice_channel(
                channel.name,
                position=channel.position,
                rtc_region=channel.rtc_region,
                user_limit=channel.user_limit,
                bitrate=channel.bitrate,
                category=category
            )
        elif isinstance(channel, TextChannel):
            await copy_to.create_text_channel(
                channel.name,
                position=channel.position,
                topic=channel.topic,
                slowmode_delay=channel.slowmode_delay,
                nsfw=channel.nsfw,
                category=category
            )


    def cog_unload(self):
        self._clear_loops()
        self._clear_reminders()


    @commands.command(aliases=['stealemote', 'getemote'])
    async def addemote(self, ctx, link: ImageConverter, roles: commands.Greedy[Role], server: Optional[Guild] = None, *, name: str):
        '''Will create an emote <name> from <link> in [server]'''
        server = server or ctx.guild
        await server.create_custom_emoji(
            name=name,
            image=await self.bot.get_bytes(link),
            roles=roles
        )
        await self.bot.log(f'Created emote {name} in {server}')


    @commands.command(aliases=['copyguild'])
    async def copyserver(self, ctx, server: Guild = None, also_copy_emotes: bool = False):
        '''Will create a new server copying <server>'''
        guild = server or ctx.guild
        init = {
            'name': guild.name,
            'icon': await guild.icon_url.read()
        }
        if guild.me.guild_permissions.manage_guild:
            templates = await guild.templates()
            if templates:
                template = templates[0]
            else:
                template = await guild.create_template(name=self.bot.user.name)
            new_guild = await template.create_guild(**init)
        else:
            new_guild = await ctx.bot.create_guild(**init)
            for category, channels in guild.by_category():
                if category:
                    cc = await new_guild.create_category_channel(category.name, position=category.position)
                    for c in channels:
                        await self._copy_channel(c, new_guild, cc)

                else:
                    await self._copy_channel(channels[0], new_guild)

            for r in guild.roles:
                await new_guild.create_role(
                    name=r.name,
                    colour=r.colour,
                    hoist=r.hoist,
                    mentionable=r.mentionable,
                    permissions=r.permissions
                )

        if also_copy_emotes:
            for e in guild.emojis:
                if not e.managed:
                    _bytes = await ctx.bot.get_bytes(str(e.url))
                    await new_guild.create_custom_emoji(name=e.name, image=_bytes)


    @commands.command(aliases=['gencc', 'generatecc'], usage='[bin=visa (can be visa mastercard amex jcb diners maestro or 6 digit bin)]')
    async def generatecreditcard(self, ctx, bin: int = 'visa'):
        '''Will generate a credit card by [bin]'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.bincodes.com/cc-gen/json/54ba9644cae569de694492a9dab5e968/{bin}/')).json()
        if r.get('error'):
            await ctx.respond(r['message'])
        else:
            msg = f"**Card:** {bin}\n**Number:** {r['number']}"
            await ctx.respond(msg)


    @flags.add_flag('--language')
    @flags.add_flag('--country')
    @flags.add_flag('query', nargs='*')
    @flags.command(
        aliases=['topnews'],
        usage='[query (leave empty for top news)] [--language=en (only with query)] [--country=US (only without query)]'
    )
    async def news(self, ctx, **options):
        '''Will show top news or news by [options...]'''
        query = ' '.join(options['query'])
        if query:
            language = 'en'
            if l := options['language']:
                language = (await LanguageConverter().convert(ctx, l)).alpha_2
            url = f"https://newsapi.org/v2/everything?q={query}&apiKey={NEWSAPI_TOKEN}&language={language}"
        else:
            country = 'US'
            if c := options['country']:
                country = (await CountryConverter().convert(ctx, c)).alpha_2
            url = f"https://newsapi.org/v2/top-headlines?country={country}&apiKey={NEWSAPI_TOKEN}"

        r = await (await self.bot.AIOHTTP_SESSION.get(url)).json()
        formatted = []
        for result in r['articles'][:5]:
            old = naturaldelta(datetime.utcnow() - datetime.strptime(result['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'))
            msg = dedent(f'''
                **{shorten(result['title'], 47)} ({old} old)**
                {shorten(utils.remove_markdown(result['description'] or 'N/A'), 250).strip()}
                [**Read further..**]({result['url']})
            ''')
            formatted.append(msg)

        await ctx.respond('\n'.join(formatted))


    @commands.command(aliases=['convertcurrency', 'currconv'])
    async def currencyconverter(self, ctx, amount: Optional[int] = 1, from_currency: CurrencyConverter = 'EUR', to_currency: CurrencyConverter = 'USD'):
        '''Will convert [amount] [from_currency] to [to_currency]'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://free.currconv.com/api/v7/convert?q={from_currency}_{to_currency}&compact=ultra&apiKey={CURRCONV_TOKEN}')).json()
        msg = f"{intcomma(amount)} {from_currency} is worth {intcomma(amount * r[f'{from_currency}_{to_currency}'], 2)} {to_currency}"
        await ctx.respond(msg)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['genemail', 'emailgenerator'])
    async def dottrick(self, ctx, gmail: str):
        '''Will "generate" emails by putting dots in between'''
        def gen_emails(e: str):
            if len(e) < 2:
                yield e
            else:
                head, tail = e[0], e[1:]
                for item in gen_emails(tail):
                    yield head + item
                    yield f'{head}.{item}'

        emails = '\n'.join(sum(map(
            lambda e: (f'{e}@gmail.com', f'{e}@googlemail.com'),
            gen_emails(gmail.split('@')[0])),
            ()
        ))
        await ctx.textfile(emails, f'{len(emails)}_emails.txt', clean=False)


    @commands.command(aliases=['trans'], brief='Utilities/translate')
    async def translate(self, ctx, targetlanguage: LanguageConverter, *, text: str):
        '''Will translate english <text> to <targetlanguage>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://translate-api.ml/translate?text={text}&lang={targetlanguage.alpha_2}')).json()
        try:
            msg = dedent(f'''
                {text}
                   ↓
                {r['translated']['text']}
                   ↓
                *{r['translated']['pronunciation'] or 'Normal pronunciation'}*
            ''')
            await ctx.respond(msg)
        except KeyError:
            raise DataNotFound(f'Text couldn\'t be translated into `{targetlanguage}`.')


    @commands.command(aliases=['charactercount', 'wordcount', 'paragraphcount'])
    async def charcount(self, ctx, *, message: str):
        '''Will return the amount of chars, words and paragraphs in your <message>'''
        nl, ws = '\n', r'\s'
        msg = dedent(f'''
            **Paragraphs:** {len(list(filter(None, message.split(nl))))}
            **Words:** {len(message.split())}
            **Characters:** {len(message)} ({len(re.sub(ws, '', message))} without whitespace)
        ''')
        await ctx.respond(msg)


    @commands.command(aliases=['pastebin'])
    async def hastebin(self, ctx, *, message: str):
        '''Will upload your <message> to a hastebin and send the link'''
        r = await (await self.bot.AIOHTTP_SESSION.post('https://hastebin.com/documents', data=message)).json()
        await ctx.send(f"https://hastebin.com/{r['key']}")


    @commands.command(aliases=['nametorid', 'resolverid'])
    async def rid(self, ctx, account_name: str):
        '''Will resolve R* ID connected to R* <account_name>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://eintim.one/ridapi.php?username={account_name}')).text()
        if r != 'User not found.':
            await ctx.respond(f"**Name:** [{account_name}](https://socialclub.rockstargames.com/member/{account_name}?id={r})\n**R* ID:** {r}")
        else:
            raise DataNotFound(f'The account {account_name} couldn\'t be found.')


    @commands.command(aliases=['calc', 'equate'])
    async def calculate(self, ctx, *, equation: str):
        '''Will solve your <equation> using Python'''
        if not any(c in equation for c in {'+', '-', '*', '/', '%', '**', '//'}):
            raise commands.BadArgument('Your equation must include arithmetic operators.')
        else:
            result = eval(equation)
            msg = f'**Input:** {utils.escape_markdown(equation)}\n**Output:** {intcomma(str(result))}'
            await ctx.respond(msg)


    @flags.add_flag('--lifetime', type=int, default=0)
    @flags.add_flag('--password', default='')
    @flags.add_flag('--confirm', type=bool, default=True)
    @flags.add_flag('--email', default='')
    @flags.add_flag('contents', nargs='+')
    @flags.command(
        aliases=['pn', 'createprivnote'],
        usage='<contents> [--lifetime=infinite] [--password=None] [--confirm=True (confirm before destroy prompt)] [--email=None (email to notify the privnote being read to)]'
    )
    async def privnote(self, ctx, **options):
        '''Will create a privnote with <contents> and [options...]'''
        link = pn.create_note(
            ' '.join(options['contents']),
            options['password'],
            options['lifetime'],
            options['confirm'],
            options['email']
        )
        await ctx.send(link)


    @commands.command(aliases=['stealpfp', 'profilepicture'])
    async def setpfp(self, ctx, link: ImageConverter):
        '''Will set your pfp to <link>'''
        image_bytes = await self.bot.get_bytes(link)
        await self_edit(ctx, avatar=image_bytes)


    @commands.command(aliases=['stealname', 'username'])
    async def setname(self, ctx, name: Union[Member, User, str]):
        '''Will set your username to <name>, can be a mention or text'''
        if isinstance(name, (Member, User)):
            name = name.name
        await self_edit(ctx, name=name)


    @commands.command()
    async def create_group(self, _, *users: User):
        '''Will create a group channel with [users...] if they are on your friendslist'''
        await self.bot.user.create_group(*list(users).append(self.bot.user))
        await self.bot.log(f"Created groupchannel with {', '.join([u.name for u in users])}")


    @commands.command(
        aliases=['discordreport'],
        usage='<message> [reason=1 (1 for Illegal Content, 2 for Harassment, 3 for Phishing, 4 for Self Harm, 5 for NSFW Content)]',
        brief='Utilities/report'
    )
    async def report(self, ctx, message: Message, reason: int = 1):
        '''Will report <message> to discord Trust & Safety'''
        info = message.split('/')[4:7]
        payload = {
            'guild_id': info[0],
            'channel_id': info[1],
            'message_id': info[2],
            'reason': reason
        }
        reasons = {
            1: 'Illegal Content',
            2: 'Harassment',
            3: 'Phishing',
            4: 'Self Harm',
            5: 'NSFW Content'
        }

        r = await self.bot.AIOHTTP_SESSION.post(f'{self.bot.API_URL}report', headers=default_headers(ctx), json=payload)
        if r.status == 201:
            r = await r.json()
            msg = dedent(f'''
                **Report ID:** {r['id']}
                **Reason:** {reasons.get(reason)}
                **Message reported:** [here]({message.jump_url})
            ''')
            await ctx.respond(msg)
        else:
            await ctx.bot.log(f'Couldn\'t send report: {r.text}', 'error')


    @commands.command(aliases=['countdown'])
    async def timer(self, ctx, time: TimeConverter = 600, update_interval: TimeConverter = 60):
        '''Will count down from [time] and update time every [update_interval]'''
        get_remaining = lambda sec: precisedelta(timedelta(seconds=sec), format='%0.0f')

        if time < update_interval:
            raise BadTime('The update_interval can\'t be bigger than the time.')

        ini = time
        msg = await ctx.respond(
            f"~{get_remaining(ini)} remaining",
            do_delete=False,
            show_speed=False
        )

        while time > 0:
            time -= 1
            if not time % update_interval and time != 0:
                remaining = f"~{get_remaining(time)} remaining"
                try:
                    if msg.embeds:
                        new = msg.embeds[0].copy()
                        new.description = remaining
                        await msg.edit(embed=new)
                    else:
                        await msg.edit(content=remaining)
                except HTTPException:
                    break
            await asyncio.sleep(1)

        else:
            await msg.delete()
            await ctx.respond(
                f"Timer for {get_remaining(ini)} has finished",
                title='Timer finished',
                send_to_log=True,
                mention_self=True,
                show_speed=False
            )


    @commands.command(aliases=['chatexport', 'savechat'])
    async def exportchat(self, ctx, limit: int = 100, channel: MultiChannelConverter = None):
        '''Will backup the latest <limit> messages to a html/txt file'''
        channel = channel or ctx.channel
        messages = await channel.history(limit=limit).flatten()
        if isinstance(channel, TextChannel):
            transcript = await chat_exporter.raw_export(channel, messages)
            await ctx.textfile(transcript, f'log-{channel}.html', clean=False)
        else:
            nl = '\n'
            formatted = [f"{ctx.channel} - saved at {datetime.utcnow()} UTC\n{'-'*90}\n"]
            for m in messages:
                if not m.embeds:
                    msg = f"{str(m.author)} at {m.created_at} UTC: {m.clean_content}"
                    if m.attachments:
                        msg += f'\n{nl.join([a.url for a in m.attachments])}'
                    formatted.append(msg)
            await ctx.textfile('\n\n'.join(reversed(formatted)), f'log-{ctx.channel}.txt', clean=False)


    @commands.command(aliases=['googlesearch', 'searchweb'])
    async def google(self, ctx, *, query: str):
        '''Will search google by <query>'''
        result = (await self._google_client.search(query))[0]
        msg = dedent(f'''
            **{shorten(result.title, 50)}**
            {result.description}
            [**Read further..**]({result.url})
        ''')
        await ctx.respond(msg, thumbnail=result.image_url)


    @commands.command(aliases=['darksearch'])
    async def tor(self, ctx, page: Optional[int] = 1, *, query: str):
        '''Will search the dark web with <query>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://darksearch.io/api/search?query={query}&page={page}')).json()
        formatted = []
        for result in r['data'][:5]:
            msg = dedent(f'''
                **{shorten(result['title'], 50)}**
                {shorten(utils.remove_markdown(result['description']), 250).strip()}
                [**Read further..**]({result['link']})
            ''')
            formatted.append(msg)

        await ctx.respond('\n'.join(formatted))


    @flags.add_flag('--channel')
    @flags.add_flag('--obfuscate', '--edit', type=bool, default=False)
    @flags.add_flag('keywords', nargs='*')
    @flags.command(
        aliases=['del', 'clear'],
        usage='[amount=20 (can also be a message link)] [keywords...] [--channel=current] [--obfuscate=False (whether to edit a message to nothing before deleting it)]',
        brief='Utilities/purge'
    )
    async def purge(self, ctx, amount: Union[int, str] = 20, **options):
        '''Will delete [amount] of messages send by you, optionally obfuscating'''
        channel = ctx.channel
        if c := options['channel']:
            channel = (await MultiChannelConverter().convert(ctx, c))
        keywords = set(options['keywords'])
        deleted = 0

        async for message in channel.history():
            if message.is_system():
                return

            if message.author == self.bot.user:
                if (
                    isinstance(amount, int)
                    and deleted == amount
                    or isinstance(amount, str)
                    and message.jump_url == amount
                ):
                    break

                with suppress(HTTPException):
                    if any(kw.casefold() in utils.remove_markdown(message.content.casefold()) for kw in keywords) if keywords else True:
                        if options['obfuscate']:
                            await message.edit(content='\u200b')

                        await message.delete()
                        deleted += 1


    @commands.command(aliases=['randomnumber'])
    async def rand(self, ctx, num1: int, num2: int):
        '''Will send a random number between <num1> and (not including) <num2>'''
        await ctx.send(randrange(num1, num2))


    @commands.command(aliases=['password', 'generatepass', 'genpass'])
    async def generatepassword(self, ctx, length: int = 12):
        '''Will generate a [length] long password'''
        await ctx.send(random_string(length))


    def _clear_loops(self):
        for d in self._loop_tasks.copy().values():
            d['task'].cancel()
        self._loop_tasks.clear()

    @commands.group(
        invoke_without_command=True,
        aliases=['loops', 'tasks'],
        brief='Utilities/loop'
    )
    async def loop(self, _):
        '''Group command for adding/removing/listing/clearing loops that send messages'''
        raise commands.CommandNotFound()

    @loop.command('add', aliases=['create', 'make', 'start'])
    async def loop_add(self, ctx, interval: TimeConverter, *, message: str):
        '''Will send <message> after <interval> untill stopped'''
        @tasks.loop(seconds=interval)
        async def loop_instance(ctx, message: str):
            await ctx.send(message)

        channel = ctx.channel.mention if ctx.guild else str(ctx.channel)
        interval = precisedelta(timedelta(seconds=interval), format='%0.0f')
        loop_instance.start(ctx, message)
        self._loop_tasks[message] = {
            'created': ctx.message.created_at,
            'channel': channel,
            'interval': interval,
            'instance': loop_instance
        }
        await self.bot.log(f'Started loop in {ctx.channel} with {interval} interval')

    @loop.command(
        'remove',
        aliases=['delete', 'cancel', 'stop'],
        usage='<query (roughly the content of the loop that you want deleted)>'
    )
    async def loop_remove(self, _, *, query: str):
        '''Will remove the loop by <query> (the message it sends)'''
        if query == 'all':
            await self._clear_loops()
            await self.bot.log('Cleared all loops')
        else:
            if closest := get_close_matches(query, self._loop_tasks.keys(), 1, 0.2):
                loop = closest[0]
                self._loop_tasks[loop]['instance'].cancel()
                self._loop_tasks.pop(loop)
                await self.bot.log(f'Removed loop `{shorten(loop, 20)}`')
            else:
                raise DataNotFound(f'Couldn\'t find `{query}` in current running loops')

    @loop.command('clear')
    async def loop_clear(self, _):
        '''Will stop all current running loops'''
        await self._clear_loops()
        await self.bot.log('Cleared all loops')

    @loop.command('list', aliases=['show'])
    async def loop_list(self, ctx):
        '''Will send the current running loops'''
        data = dict(sorted(self._loop_tasks.items(), key=lambda item: item[1]['created']))
        msg, fields = f'{len(data)} loop(s) running', []
        for i, (k, v) in enumerate(data.items(), 1):
            if i > 8:
                break

            loop = dedent(f'''
                {fill(k, width=30)}

                **Created:** {format_date(v['created'])}
                **Channel:** {v['channel']}
                **Interval:** {v['interval']}
                **Next message:** in {precisedelta(datetime.utcnow() - (v['instance'].next_iteration.replace(tzinfo=None)), format='%0.0f')}
            ''')

            fields.append((
                f'Loop {i}',
                loop
            ))
        await ctx.respond(msg, fields=fields)


    @commands.group(invoke_without_command=True, aliases=['status'])
    async def activity(self, _):
        '''Group command for changing your discord presence'''
        raise commands.CommandNotFound()

    @activity.command('streaming')
    async def activity_streaming(self, _, stream_url: str, *, message: str):
        '''Will change your activity to Streaming <message> with link <stream_url>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.streaming, name=message, url=stream_url))
        await self.bot.log(f'Changed presence to \'Streaming {message}\' with url {stream_url}')

    @activity.command('playing')
    async def activity_playing(self, _, *, message: str):
        '''Will change your activity Playing <message>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.playing, name=message))
        await self.bot.log(f'Changed presence to \'Playing {message}\'')

    @activity.command('listening', aliases=['listening_to'])
    async def activity_listening(self, _, *, message: str):
        '''Will change your activity to Listening to <message>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.listening, name=message))
        await self.bot.log(f'Changed presence to \'Listening to {message}\'')

    @activity.command('watching')
    async def activity_watching(self, _, *, message: str):
        '''Will change your activity to Watching <message>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.watching, name=message))
        await self.bot.log(f'Changed presence to \'Watching {message}\'')

    @activity.command('competing', aliases=['competing_in'])
    async def activity_competing(self, _, *, message: str):
        '''Will change your activity to Competing in <message>'''
        await self.bot.change_presence(activity=Activity(type=ActivityType.competing, name=message))
        await self.bot.log(f'Changed presence to \'Competing in {message}\'')


    @commands.group(aliases=['autodelete', 'autopurge'], invoke_without_command=True)
    async def autodel(self, _):
        '''Group command for starting and stopping autodelete'''
        raise commands.CommandNotFound()

    async def _auto_delete(self, message: Message):
        if message.author == self.bot.user:
            messages = self._autodel_messages[message.channel.id]
            messages.append(message)
            if len(messages) > self._autodel_limit:
                with suppress(HTTPException, IndexError):
                    await messages[0].delete()
                    del messages[0]

    @autodel.command('start')
    async def autodel_start(self, _, limit: int = 4):
        '''Will autodelete messages after [limit] send'''
        self._autodel_limit = limit
        self.bot.add_listener(self._auto_delete, 'on_message')
        await self.bot.log('Started autodelete listener')

    @autodel.command('stop')
    async def autodel_stop(self, _):
        '''Will stop autodeleting messages'''
        self.bot.remove_listener(self._auto_delete, 'on_message')
        await self.bot.log('Stopped autodelete listener')


    @commands.group(invoke_without_command=True, aliases=['afk'])
    async def afkmode(self, _):
        '''Group command for starting/stopping afkmode'''
        raise commands.CommandNotFound()

    async def _afkmode_respond(self, message: Message):
        if message.author.id not in self._afkmode_blacklist:
            await message.reply(self._afkmode_message, mention_author=False)
            self._afkmode_blacklist.add(message.author.id)

    async def _afk_mode(self, message: Message):
        if self._afkmode_only_dms_enabled:
            if isinstance(message.channel, DMChannel):
                if message.author != self.bot.user:
                    await self._afkmode_respond(message)
        else:
            if self.bot.user in message.mentions:
                await self._afkmode_respond(message)

    @afkmode.command('start', usage='[only_dms=False (yes if you want to only reply to dms, instead of mentions)] <message>')
    async def afkmode_start(self, _, only_dms: Optional[bool] = False, *, message: str):
        '''Will reply to dms or mentions once with <message>'''
        await self.bot.change_presence(status=Status.idle, afk=True)
        self._afkmode_message, self._afkmode_only_dms_enabled = message, only_dms
        self.bot.add_listener(self._afk_mode, 'on_message')
        await self.bot.log(f'Started afkmode listener with message {message}')

    @afkmode.command('stop')
    async def afkmode_stop(self, _):
        '''Will stop the afkmode'''
        self._afkmode_blacklist = set()
        await self.bot.change_presence(status=Status.online, afk=False)
        self.bot.remove_listener(self._afk_mode, 'on_message')
        await self.bot.log('Removed afkmode listener')


    @commands.group(invoke_without_command=True)
    async def crypto(self, _):
        '''Group command for commands regarding crypto currency'''
        raise commands.CommandNotFound()

    @crypto.command('btc')
    async def crypto_btc(self, ctx, currencycode: CurrencyConverter = 'usd'):
        '''Will show value of 1 btc in [currencycode]'''
        await self._send_crypto(ctx, currencycode, coin='bitcoin')

    @crypto.command('tobtc')
    async def crypto_tobtc(self, ctx, amount: float, currencycode: CurrencyConverter = 'usd'):
        '''Will convert provided <amount> to it's bitcoin equivalent in [currencycode]'''
        await self._send_crypto(ctx, currencycode, coin='bitcoin', amount=amount)

    @crypto.command('custom')
    async def crypto_custom(self, ctx, coin: str, currencycode: CurrencyConverter = 'usd'):
        '''Will convert the value of 1 <coin> to [currencycode]'''
        await self._send_crypto(ctx, currencycode, coin=coin)

    @crypto.command('tocustom')
    async def crypto_tocustom(self, ctx, coin: str, amount: float, currencycode: CurrencyConverter = 'usd'):
        '''Will convert <amount> <coin> to [currencycode]'''
        await self._send_crypto(ctx, currencycode, coin=coin, amount=amount)


    async def _reminder_sleep(self, delay: int, message: str) -> bool:
        coro = asyncio.sleep(delay, loop=self.bot.loop)
        task = asyncio.ensure_future(coro)
        self._sleep_tasks[message] = task
        try:
            await task
            return True
        except asyncio.CancelledError:
            return False
        finally:
            self._sleep_tasks.pop(message)

    def _clear_reminders(self):
        for task in self._sleep_tasks.values():
            task.cancel()
        self._reminders.clear()

    @commands.group(
        invoke_without_command=True,
        aliases=['remind', 'reminders'],
        brief='Utilities/reminder'
    )
    async def reminder(self, _):
        '''Group command for creating/removing/listing/clearing reminders'''
        raise commands.CommandNotFound()

    @reminder.command(
        'add',
        aliases=['create', 'make'],
        usage='<message (should contain a loose interpretation of time, e.g \'in 3 hours clean up\', \'play games with ooga tomorrow\' or \'celebrate September 11\')>',
    )
    async def reminder_add(self, ctx, *, message: DateConverter):
        '''Will add a reminder with <message>'''
        message, when = message
        created = ctx.message.created_at
        channel = ctx.channel.mention if ctx.guild else str(ctx.channel)
        self._reminders[message] = {
            'when': when,
            'created': created,
            'channel': channel
        }
        await ctx.respond(f'Added reminder for {naturalday(when)} (in ~{format_date(when)})')
        done = await self._reminder_sleep((when - datetime.now()).total_seconds(), message)
        if done:
            await ctx.respond(
                f'You, ~{format_date(created)}:\n{message}',
                title='Reminder finished',
                send_to_log=True,
                mention_self=True,
                show_speed=False
            )

    @reminder.command(
        'remove',
        aliases=['delete', 'stop', 'cancel'],
        usage='<query (roughly the content of the reminder that you want deleted)>'
    )
    async def reminder_remove(self, _, *, query: str.lower):
        '''Will remove a reminder by <query>'''
        if query == 'all':
            await self._clear_reminders()
            await self.bot.log('Cleared all reminders')
        else:
            if closest := get_close_matches(query, self._reminders.keys(), 1, 0.2):
                reminder = closest[0]
                self._reminders.pop(reminder)
                self._sleep_tasks.get(reminder).cancel()
                await self.bot.log(f'Removed reminder `{reminder}`')
            else:
                raise DataNotFound(f'Couldn\'t find `{query}` in your reminders')

    @reminder.command('clear')
    async def reminder_clear(self, _):
        '''Will clear all reminders'''
        await self._clear_reminders()
        await self.bot.log('Cleared all reminders')

    @reminder.command('list', aliases=['show'])
    async def reminder_list(self, ctx):
        '''Will show all your reminders'''
        data = dict(sorted(self._reminders.items(), key=lambda item: item[1]['when']))
        msg, fields = f'{len(data)} reminder(s)', []
        for i, (k, v) in enumerate(data.items(), 1):
            if i > 8:
                break

            reminder = dedent(f'''
               {fill(k, width=30)}

               **Ends in:** ~{format_date(v['when'])}
               **Created:** ~{format_date(v['created'])}
               **Channel:** {v['channel']}
            ''')

            fields.append((
                f'Reminder {i}',
                reminder
            ))
        await ctx.respond(msg, fields=fields)


    @commands.group(invoke_without_command=True)
    async def todo(self, _):
        '''Group command for creating/removing/listing/clearing todo's'''
        raise commands.CommandNotFound()

    @todo.command('add', aliases=['create', 'make'])
    async def todo_add(self, ctx, *, message: str):
        '''Will create a todo with <message>, and save it to a file'''
        created = datetime.timestamp(ctx.message.created_at)
        with open(Path('data/json/todo.json'), encoding='utf-8') as f:
            data = json.load(f)
            data[message] = {
                'created': created
            }
        with open(Path('data/json/todo.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        await ctx.respond(f'Added {message} to your todolist')

    @todo.command(
        'remove',
        aliases=['delete'],
        usage='<query (roughly the content of the todo that you want deleted)>'
    )
    async def todo_remove(self, _, *, query: str.lower):
        '''Will remove a todo by <query>'''
        if query == 'all':
            with open(Path('data/json/todo.json'), 'w', encoding='utf-8') as f:
                json.dump({}, f)
        else:
            with open(Path('data/json/todo.json'), encoding='utf-8') as f:
                data = json.load(f)

            if closest := get_close_matches(query, list(data.keys()), 1, 0.2):
                todo = closest[0]
                data.pop(todo)
                with open(Path('data/json/todo.json'), 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                await self.bot.log(f'Removed todo `{todo}`')
            else:
                raise DataNotFound(f'Couldn\'t find `{query}` in your todo list')

    @todo.command('clear')
    async def todo_clear(self, _):
        '''Will clear all todo's'''
        with open(Path('data/json/todo.json'), 'w', encoding='utf-8') as f:
            json.dump({}, f)
        await self.bot.log('Cleared all todo\'s')

    @todo.command('list', aliases=['show'])
    async def todo_list(self, ctx):
        '''Will show all your todo's'''
        with open(Path('data/json/todo.json'), encoding='utf-8') as f:
            todos = json.load(f)

        data, formatted = dict(sorted(todos.items(), key=lambda item: item[1]['created'])), []

        for k, v in data.items():
            formatted.append(f"• {k}, created {format_date(v['created'])}")

        await ctx.respond('\n'.join(formatted))


def setup(bot):
    bot.add_cog(Utilities(bot))
