# -*- coding: utf-8 -*-
import asyncio
from contextlib import suppress
from datetime import datetime
from difflib import get_close_matches
from io import BytesIO
from itertools import cycle
from pathlib import Path
from random import choice, randrange, sample
from textwrap import dedent
from typing import Optional, Union
from urllib import parse

from discord import (Activity, ActivityType, Colour, Embed, File,
                     HTTPException, Message, PartialEmoji, User, utils)
from discord.ext import commands, tasks
from discord.reaction import Reaction
from gtts import gTTS
from humanize import intcomma, naturaldelta
from pycountry import countries

from .utils import flags
from .utils.checks import bot_has_permissions
from .utils.converters import (DateConverter, LanguageConverter,
                               MultiChannelConverter, TimeConverter)
from .utils.enums import JokeType
from .utils.exceptions import DataNotFound
from .utils.helpers import (animate, default_headers, format_date, random_string,
                            sentence_to_indicator)
from .utils.tokens import RAPIDAPI_TOKEN


class Fun(commands.Cog):
    '''Category with all fun commands. These are all harmless.'''

    def __init__(self, bot):
        self.bot = bot

        self._edit_nick_enabled = bool()
        self._cycle_status_enabled = bool()
        self._giveaway_react_emote = None
        self._giveaway_participants = list()
        self._giveaway_message = str()
        self._8ball_responses = (
            'It is very certain',
            'It is decidedly so',
            'Without a doubt',
            'Yes, definitely',
            'You may rely on it',
            'As i see it, yes',
            'Most likely',
            'Outlook good',
            'Yes',
            'Signs point to yes',
            'Reply hazy, try again',
            'Ask again later',
            'Hmm.. better not tell you now',
            'Can\'t predict now',
            'Concentrate and ask again',
            'Can\'t count on it',
            'My reply is no',
            'My sources say no',
            'Outlook not so good',
            'It\'s very doubtful'
        )
        self._dices = (
            'https://cdn.discordapp.com/attachments/760553482498736168/761676922060275822/dice1.png',
            'https://cdn.discordapp.com/attachments/760553482498736168/761676923294056468/dice2.png',
            'https://cdn.discordapp.com/attachments/760553482498736168/761676924375531570/dice3.png',
            'https://cdn.discordapp.com/attachments/760553482498736168/761676925608394802/dice4.png',
            'https://cdn.discordapp.com/attachments/760553482498736168/761676926967611463/dice5.png',
            'https://cdn.discordapp.com/attachments/760553482498736168/761676928549257236/dice6.png'
        )
        with open(Path('data/assets/text/wyr.txt'), encoding='utf-8') as f:
            self._would_you_rathers = f.readlines()


    @staticmethod
    async def _send_joke(ctx, joke_type: JokeType) -> None:
        r = await (await ctx.bot.AIOHTTP_SESSION.get(f'https://sv443.net/jokeapi/v2/joke/{joke_type}')).json()
        if r['type'] == 'twopart':
            msg = f"{r['setup']}\n\n{r['delivery']}"
        elif r['type'] == 'single':
            msg = r['joke']
        await ctx.respond(msg)


    def cog_unload(self):
        self._rainbow_embed.cancel()


    @flags.add_flag('--accessibility', type=float)
    @flags.add_flag('--type')
    @flags.add_flag('--participants', type=int)
    @flags.add_flag('--maxprice', type=float)
    @flags.command(
        aliases=['bored', 'getidea'],
        usage='[--accessibility (factor 0 to 1 with 0 being easy)] [--type (can be education, recreational, social, diy, charity, cooking, relaxation, music or busywork)] [--participants] [--maxprice (factor 0 to 1 with 0 being free)]'
    )
    async def idea(self, ctx, **options):
        '''Will send an idea of how to pass the time with [options...]'''
        payload = {
            'accessibility': options['accessibility'],
            'type': options['type'],
            'participants': options['participants'],
            'maxprice': options['maxprice']
        }
        parsed = parse.urlencode(dict(filter(lambda item: item[1], payload.items())))
        r = await (await self.bot.AIOHTTP_SESSION.get(f"http://www.boredapi.com/api/activity{'?' + parsed if parsed else ''}")).json()
        msg = dedent(f'''
            **Type:** {r['type'].capitalize()}
            **Participants:** {r['participants']}
            **Accessibility:** {r['accessibility']}/1
            **Price:** {r['price']}/1

            {r['activity']}
        ''') + f"[Learn more..]({r['link']})" if r['link'] else ''
        await ctx.respond(msg)


    @commands.command(aliases=['genderize', 'agify', 'nationalize', 'pbn'])
    async def predictbyname(self, ctx, *, name: str):
        '''Will predict age/gender and country by <name>'''
        r1 = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.genderize.io?name={name}')).json()
        r2 = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.agify.io?name={name}')).json()
        r3 = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.nationalize.io?name={name}')).json()
        msg = dedent(f'''
            **Name:** {name}
            **Age:** {r2['age'] or 'N/A'} (with {intcomma(r2['count'])} cases)
            **Gender:** {r1['gender'] or 'N/A'} ({(r1['probability'] or 1) * 100:.2f}% likely with {intcomma(r1['count'])} cases)
            **Countries:** {(', '.join([f"{countries.lookup(c['country_id']).name} ({c['probability'] * 100:.2f}% likely)" for c in r3['country']])) or 'N/A'}
        ''')
        await ctx.respond(msg, title='Predict By Name')


    @commands.command()
    async def chatbot(self, ctx, *, message: str):
        '''Will allow you to talk to an AI bot'''
        headers = {
            'x-rapidapi-host': 'acobot-brainshop-ai-v1.p.rapidapi.com',
            'x-rapidapi-key': RAPIDAPI_TOKEN
        }
        r = await (await self.bot.AIOHTTP_SESSION.get(
            f'https://acobot-brainshop-ai-v1.p.rapidapi.com/get?bid=178&key=sX5A2PcYZbsN5EY6&uid=mashape&msg={message}',
            headers=headers
        )).json()
        await ctx.send(r['cnt'])


    @commands.command()
    async def snipe(self, ctx, channel: MultiChannelConverter = None):
        '''Will send the latest deleted message from <channel>'''
        channel = channel or ctx.channel
        try:
            sniped_message = self.bot.MESSAGE_SNIPES[channel.id]
            location = f"In {getattr(channel, 'mention', str(channel))}"
            if channel == ctx.channel:
                location = 'Here'
        except KeyError:
            raise DataNotFound(f'No deleted messages were found in {channel.mention}.')
        else:
            msg = f"{location}, ~{format_date(sniped_message.created_at)}, from {sniped_message.author.mention}:\n{sniped_message.content}"
            await ctx.respond(msg)


    async def _giveaway(self, reaction: Reaction, user: User):
        if reaction.message == self._giveaway_message:
            if reaction.emoji == self._giveaway_react_emote:
                self._giveaway_participants.append(user)

    @commands.command(
        aliases=['give'],
        usage='<emote (emote to check reactions for)> <item (should contain a loose interpretation of time, e.g \'in 3 hours a nitro gift\')>',
        brief='Fun/giveaway'
    )
    async def giveaway(self, ctx, emote: Union[PartialEmoji, str], *, item: DateConverter):
        '''Will create a giveaway from <item>'''
        item, ends_when = item
        msg = dedent(f'''
            **Item:** {item}
            **Ends in:** ~{naturaldelta(datetime.now() - ends_when)} ({ends_when.strftime('%H:%M:%S')})

            *React with {emote} to enter.*
        ''')
        msg = await ctx.respond(
            msg,
            do_delete=False,
            show_speed=False
        )
        self._giveaway_react_emote, self._giveaway_message, self._giveaway_participants = emote, msg, []
        await msg.add_reaction(emote)
        self.bot.add_listener(self._giveaway, 'on_reaction_add')
        await asyncio.sleep((ends_when - datetime.now()).total_seconds())
        self.bot.remove_listener(self._giveaway, 'on_reaction_add')
        self._giveaway_participants = [u for u in self._giveaway_participants if u != self.bot.user]

        try:
            winner = choice(self._giveaway_participants)
        except IndexError:
            await self.bot.log('No one reacted to the giveaway message', 'error')
        else:
            won = f'{winner.mention} won {item}!'
            try:
                if msg.embeds:
                    new = msg.embeds[0].copy()
                    new.description = won
                    new.title = 'Giveaway finished!'
                    await msg.edit(embed=new)
                else:
                    await msg.edit(content=f'Giveaway finished!\n{won}')
            except HTTPException:
                await self.bot.log(f'{won}, but the message was deleted and couldn\'t be edited.', 'info')


    @commands.command(aliases=['urbandictionary'])
    async def urban(self, ctx, *, query: str.lower):
        '''Will define your <query> via urban dictionary'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'http://api.urbandictionary.com/v0/define?term={query}')).json()
        data = sorted(r['list'], key=lambda item: item['thumbs_up'], reverse=True)[0]
        try:
            fields = [
                ('Word', f"[{data['word']}]({data['permalink']})"),
                ('Author', data['author']),
                ('Date posted', datetime.strptime(data['written_on'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%c')),
                ('Upvotes', data['thumbs_up']),
                ('Downvotes', data['thumbs_down'])
            ]
            nl1 = '\r\n'
            nl2 = '\n'
            msg = dedent(f'''
                **Definition:**
                {utils.escape_markdown(data['definition'].replace(nl1, nl2).replace('[', '').replace(']', ''))}

                **Example:**
                {utils.escape_markdown(data['example'].replace(nl1, nl2).replace('[', '').replace(']', ''))}
            ''')
            await ctx.respond(msg, fields=fields)
        except KeyError:
            raise DataNotFound(f'The word `{query}` couldn\'t be found.')


    @commands.command(aliases=['meme'])
    async def reddit(self, ctx, subreddit: str = 'memes', amount: int = 1):
        '''Will send a random post from [subreddit]'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://meme-api.herokuapp.com/gimme/{subreddit}/{amount}')).json()
        try:
            results = r['memes']
        except KeyError:
            raise DataNotFound(f'The subreddit `{subreddit}` couldn\'t be found.')
        else:
            for d in results:
                msg = f"Reddit | [{d['subreddit']}]({d['postLink']})"
                fields = [
                    ('Title', d['title']),
                    ('Author', d['author']),
                    ('Upvotes', d['ups'])
                ]
                await ctx.respond(msg, d['url'], fields=fields)


    @bot_has_permissions(embed_links=True)
    @commands.command(aliases=['rembed'])
    async def rainbowembed(self, ctx, title: str, *, description: str):
        '''Will send an embed that changes colour'''
        @tasks.loop(seconds=3, count=15)
        async def edit_embed(message: Message, title: str, description: str):
            embed = Embed(
                title=title,
                description=description,
                colour=Colour.random()
            )
            await message.edit(embed=embed)

        embed = Embed(
            title=title,
            description=description,
            colour=0xDC143C
        )
        msg = await ctx.send(embed=embed)
        edit_embed.start(msg, title, description, title='Rainbow Embed')


    @commands.command(aliases=['gennitro', 'randomnitro'])
    async def nitro(self, ctx, amount: int = 5):
        '''Will generate [amount] random discord nitro codes'''
        for _ in range(amount):
            await ctx.send(f'https://discord.gift/{random_string(16)}')


    @commands.command(aliases=['geninvite', 'randominvite'])
    async def invite(self, ctx, amount: Optional[int] = 5, known_big_servers: bool = False):
        '''Will generate [amount] random or [known_big_servers] discord invite links'''
        if known_big_servers:
            r = await (await self.bot.AIOHTTP_SESSION.get(f'https://discord.com/api/v8/discoverable-guilds?offset={randrange(15, 51)}&limit={amount}', headers=default_headers(ctx))).json()
            invites = [f"discord.gg/{d['vanity_url_code']}" for d in r.get('guilds', {'vanity_url_code': 'invalid'})]
        else:
            invites = [f'https://discord.gg/{random_string(9)}' for _ in range(amount)]
        await ctx.send('\n'.join(invites))


    @commands.command()
    async def dice(self, ctx):
        '''Will send a random dice image'''
        await ctx.respond(image=choice(self._dices))


    @commands.command(aliases=['wyr'])
    async def wouldyourather(self, ctx):
        '''Will send a random wouldyourather dilemma'''
        wyr = choice(self._would_you_rathers).split(' or ')
        msg = dedent(f'''
            1️⃣ {wyr[0].lower().capitalize()}

            **OR**

            2️⃣ {wyr[1].lower().capitalize()}
        ''')
        m = await ctx.respond(msg, title='Would You Rather')
        for e in ('1️⃣', '2️⃣'):
            await m.add_reaction(e)


    @commands.command()
    async def advice(self, ctx):
        '''Will send random advice'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://api.adviceslip.com/advice')).json(content_type=None)
        msg = r['slip']['advice']
        await ctx.respond(msg)


    @commands.command()
    async def roast(self, ctx):
        '''Will send a random roast'''
        await ctx.dagpi('data/roast')


    @commands.command()
    async def quote(self, ctx):
        '''Will send a random quote'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://goquotes-api.herokuapp.com/api/v1/random?count=1')).json()
        await ctx.respond(f">>> {r['quotes'][0]['text']}\n- **{r['quotes'][0]['author']}**")


    @commands.command(aliases=['pickup'])
    async def pickupline(self, ctx):
        '''Will send a random pickupline'''
        await ctx.dagpi('data/pickupline', index=1)


    @commands.command()
    async def headline(self, ctx):
        '''Will send a random real or fake headline'''
        await ctx.dagpi('data/headline', index=0)


    @commands.command()
    async def fact(self, ctx):
        '''Will send a random fact'''
        await ctx.dagpi('data/fact')


    @bot_has_permissions(embed_links=True)
    @flags.add_flag('--deleteafter')
    @flags.add_flag('--colour', '--color', type=Colour, default=Embed.Empty)
    @flags.add_flag('--image')
    @flags.add_flag('--thumbnailurl', '--thumbnail')
    @flags.add_flag('--timestamp', type=bool)
    @flags.add_flag('--description')
    @flags.add_flag('--footertext', '--footer', default=Embed.Empty)
    @flags.add_flag('--footericon', default=Embed.Empty)
    @flags.add_flag('--titletext', '--title', default=Embed.Empty)
    @flags.add_flag('--titleurl')
    @flags.add_flag('--authorname', '--author', default=Embed.Empty)
    @flags.add_flag('--authorurl', default=Embed.Empty)
    @flags.add_flag('--authoricon', default=Embed.Empty)
    @flags.command(
        aliases=['embedbuilder', 'makeembed'],
        usage='[channel] [--deleteafter time] [--colour] [--image] [--thumbnail] [--timestamp=None] [--description] [--footertext] [--footericon] [--titletext] [--titleurl] [--authorname] [--authorurl] [--authoricon]',
        brief='Fun/embed'
    )
    async def embed(self, ctx, channel: Optional[MultiChannelConverter] = None, **options):
        '''Will allow you to specify certain embed parts'''
        channel = channel or ctx.channel
        delete_after = None
        if options['deleteafter']:
            delete_after = await TimeConverter().convert(ctx, options['deleteafter'])

        embed = Embed(
            title=options['titletext'] or '',
            colour=options['colour'],
            description=options['description'].replace(r'\n', '\n') if options['description'] else None
        )
        if options['image']:
            embed.set_image(url=options['image'])
        if options['thumbnail']:
            embed.set_thumbnail(url=options['thumbnail'])
        if options['timestamp']:
            embed.timestamp = datetime.utcnow()
        if options['titleurl']:
            embed.url = options['titleurl']
        if options['footertext']:
            embed.set_footer(text=options['footertext'], icon_url=options['footericon'])
        if options['authorname']:
            embed.set_author(name=options['authorname'], url=options['authorurl'], icon_url=options['authoricon'])
        await channel.send(embed=embed, delete_after=delete_after)


    @bot_has_permissions(attach_files=True)
    @flags.add_flag('--language', '--lan')
    @flags.add_flag('--slow', type=bool, default=False)
    @flags.add_flag('message', nargs='+')
    @flags.command(
        aliases=['tts', 'gentts', 'speak'],
        usage='<message> [--language=en] [--slow=False]'
    )
    async def texttospeech(self, ctx, **options):
        '''Will generate tts mp3 file saying <message>'''
        language = 'en'
        if l := options['language']:
            language = (await LanguageConverter().convert(ctx, l)).alpha_2

        tts = await self.bot.loop.run_in_executor(
            None,
            lambda: gTTS(
            ' '.join(options['message']),
            lang=language,
            slow=options['slow']
        ))
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        await ctx.send(file=File(fp, 'tts.mp3'))


    @bot_has_permissions(add_reactions=True)
    @commands.command()
    async def react(self, ctx, limit: Optional[int] = 10, *emojis):
        '''Will react to the last <amount> messages with [emojis..]'''
        with suppress(HTTPException):
            async for message in ctx.channel.history(limit=limit, before=ctx.message):
                for e in emojis:
                    if len(e) > 1:
                        for char in e:
                            e = sentence_to_indicator(char)
                            await message.add_reaction(e)
                    else:
                        await message.add_reaction(e)


    @commands.command(aliases=['letmegooglethatforyou'])
    async def lmgtfy(self, ctx, *, message: str):
        '''Will send a letmegooglethatforyou with <message>'''
        await ctx.send(f'<https://lmgtfy.com/?q={parse.quote_plus(message)}>')


    @commands.command(aliases=['hack'])
    async def virus(self, ctx, virusname: str = 'xtreme_KKK', destination: str = 'Guild'):
        '''Will send an editing virus message'''
        await animate(ctx, 'virus', virusname, destination, datetime.utcnow())


    @commands.command(aliases=['essay', 'swat'])
    async def killpresident(self, ctx):
        '''Essay on American government'''
        await animate(ctx, 'killpresident', self.bot.user.name, sleep=3, edit=False)


    @commands.command(aliases=['stfu'])
    async def shutthefuckup(self, ctx):
        '''Will send an editing stfu message'''
        await animate(ctx, 'stfu', sleep=1)


    @commands.command(aliases=['noc'])
    async def noonecares(self, ctx):
        '''Will send an editing no one cares message'''
        await animate(ctx, 'noonecares', sleep=1, lines=False)


    @commands.command('911', aliases=['terrorist'])
    async def _911(self, ctx):
        '''Will send an editing 911 image'''
        await animate(ctx, '911', sleep=1.8, lines=False)


    @commands.command(aliases=['coomer'])
    async def cum(self, ctx):
        '''Will send an editing cum image 😳'''
        await animate(ctx, 'cum', sleep=0.8, lines=False)


    @commands.command(aliases=['randomemojis', 'searchemotes'])
    async def emojisearch(self, ctx, amount: Optional[int] = 1, *, query: str = None):
        '''Will send [amount] emojis, random or filtered by [query]'''
        if query:
            possible = {e.name: e for e in self.bot.emojis}
            emotes = [possible.get(m) for m in get_close_matches(query, possible.keys(), amount, 0.3)]
        else:
            emotes = sample(self.bot.emojis, k=amount) # no duplicates with sample
        await ctx.send(' '.join(map(str, emotes)))


    @commands.command(aliases=['randomcomic', 'comic'], usage='[number=random]')
    async def xkcd(self, ctx, number: int = None):
        '''Will send a xkcd comic'''
        if not number:
            number = randrange(1, 2520) # Max number as of 26/09/2021
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://xkcd.com/{number}/info.0.json')).json()
        msg = f"xkcd #{r['num']} | {r['title']} ({r['year']})"
        await ctx.respond(msg, r['img'])


    @flags.add_flag('--captcha', type=bool, default=True)
    @flags.add_flag('--private', type=bool, default=True)
    @flags.add_flag('--comments', type=bool, default=True)
    @flags.add_flag('--multvotes', '--multiplevotes', type=bool, default=False)
    @flags.add_flag('--multanswer', '--multipleanswers', type=bool, default=False)
    @flags.add_flag('--vpn', type=bool, default=False)
    @flags.add_flag('--entername', type=bool, default=False)
    @flags.add_flag('answers', nargs='+')
    @flags.command(
        aliases=['createpoll', 'strawpoll'],
        usage='<title> [answers...] [--captcha=True] [--private=True] [--comments=True] [--multvotes=False] [--multanswer=False] [--vpn=False] [--entername=False]',
        brief='Fun/poll'
    )
    async def poll(self, ctx, title: str, **options):
        '''Will create a strawpoll with possible [answers...] and [options...]'''
        payload = {
            'poll': {
                'title': title,
                'priv': options['private'],
                'co': options['comments'],
                'answers': options['answers'],
                'ma': options['multanswer'],
                'mip': options['multvotes'],
                'captcha': options['captcha'],
                'enter_name': options['entername']
            }
        }

        r = await (await self.bot.AIOHTTP_SESSION.post('https://strawpoll.com/api/poll', headers={'Content-Type': 'application/json'}, json=payload)).json()
        await ctx.send(f"https://strawpoll.com/{r['content_id']}")


    @commands.command('8ball')
    async def eightball(self, ctx, *, question: str):
        '''Will send an 8ball response to your question'''
        msg = f"Question: {question}\nResponse: {choice(self._8ball_responses)}"
        await ctx.respond(msg, thumbnail='https://cdn.discordapp.com/attachments/781208734013456395/812745492236206140/8ball.png')


    @commands.group(invoke_without_command=True, aliases=['cyclenick'])
    async def editnick(self, _):
        '''Group command for starting/stopping editnick'''
        raise commands.CommandNotFound()

    @bot_has_permissions(change_nickname=True)
    @editnick.command('start', aliases=['cyclenick'])
    async def editnick_start(self, ctx, delay: Optional[TimeConverter] = 3, *, nickname: str = None):
        '''Will loop through <nickname> revealing letters'''
        await self.bot.log(f'Starting nick edit for {nickname}')
        await ctx.me.edit(nick='')
        buffer, self._edit_nick_enabled = '', True
        while self._edit_nick_enabled:
            for l in nickname:
                if not self._edit_nick_enabled:
                    await ctx.me.edit(nick=None)
                    break
                buffer += l
                await ctx.me.edit(nick=buffer)
                await asyncio.sleep(delay)
            buffer = ''

    @editnick.command('stop')
    async def editnick_stop(self, _):
        '''Will stop the editnick and return to the old nickname'''
        self._edit_nick_enabled = False
        await self.bot.log('Stopped editing nickname')


    @commands.group(invoke_without_command=True)
    async def cyclestatus(self, _):
        '''Group command for starting/stopping cyclestatus'''
        raise commands.CommandNotFound()

    @cyclestatus.command('start')
    async def cyclestatus_start(self, _, delay: Optional[TimeConverter] = 5, *statuses: str):
        '''Will cycle trough a list of <statuses> changing every <delay> sec'''
        await self.bot.log(f'Starting status cycle through {", ".join(statuses)}')
        self._cycle_status_enabled = True
        statuses = cycle(statuses)
        while self._cycle_status_enabled:
            s = next(statuses)
            await self.bot.change_presence(activity=Activity(type=ActivityType.custom, name=s, state=s))
            await asyncio.sleep(delay)

    @cyclestatus.command('stop')
    async def cyclestatus_stop(self, _):
        '''Will stop the cyclestatus listener'''
        self._cycle_status_enabled = False
        await self.bot.log('Stopped cycling through statuses')


    @commands.group(invoke_without_command=True, aliases=['funny', 'gag'])
    async def joke(self, _):
        '''Group command for sending (bad) jokes'''
        raise commands.CommandNotFound()

    @joke.command('dark')
    async def joke_dark(self, ctx):
        '''Will send a random dark joke'''
        await self._send_joke(ctx, JokeType.dark)

    @joke.command('pun')
    async def joke_pun(self, ctx):
        '''Will send a random pun joke'''
        await self._send_joke(ctx, JokeType.pun)

    @joke.command('programming')
    async def joke_programming(self, ctx):
        '''Will send a random programming related joke'''
        await self._send_joke(ctx, JokeType.programming)

    @joke.command('miscellaneous', aliases=['misc'])
    async def joke_miscellaneous(self, ctx):
        '''Will send a random miscellaneous joke'''
        await self._send_joke(ctx, JokeType.miscellaneous)

    @joke.command('christmas')
    async def joke_christmas(self, ctx):
        '''Will send a random christmas related joke'''
        await self._send_joke(ctx, JokeType.christmas)

    @joke.command('spooky')
    async def joke_spooky(self, ctx):
        '''Will send a random spooky joke'''
        await self._send_joke(ctx, JokeType.spooky)

    @joke.command('dad')
    async def joke_dad(self, ctx):
        '''Will send a random dad joke'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://icanhazdadjoke.com', headers={'Accept': 'application/json'})).json()
        msg = r['joke']
        await ctx.respond(msg)

    @joke.command('yomama')
    async def joke_yomama(self, ctx):
        '''Will send a random yomama joke'''
        await ctx.dagpi('data/yomama')


def setup(bot):
    bot.add_cog(Fun(bot))
