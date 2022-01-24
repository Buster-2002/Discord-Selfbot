# -*- coding: utf-8 -*-
import asyncio
import base64
import re
from io import BytesIO
from math import sin
from pathlib import Path
from random import choice
from textwrap import dedent
from typing import Optional
from urllib import parse

import numpy as np
from discord import Colour, File, HTTPException, User
from discord.ext import commands
from PIL import Image
from wordcloud import WordCloud

from .utils import flags
from .utils.checks import bot_has_permissions
from .utils.converters import MultiChannelConverter
from .utils.enums import AIDataType
from .utils.exceptions import DataNotFound
from .utils.helpers import (deepai, dot_cal, l_to_gif, sentence_to_bubble,
                            sentence_to_cancer, sentence_to_chink,
                            sentence_to_cursive, sentence_to_enchantment,
                            sentence_to_from_morse, sentence_to_indicator,
                            sentence_to_leet, sentence_to_oldenglish,
                            sentence_to_reverse, sentence_to_square,
                            sentence_to_subscript, sentence_to_superscript)
from .utils.regexes import URL_REGEX


class Text(commands.Cog):
    '''Category for all text related commands.'''

    def __init__(self, bot):
        self.bot = bot

        self._available_colours = {
            'orange': {
                'language': 'css',
                'prefix': '[',
                'suffix': ']'
            },
            'blue': {
                'language': 'ini',
                'prefix': '[',
                'suffix': ']'
            },
            'bluegreen': {
                'language': 'bash',
                'prefix': '"',
                'suffix': '"'
            },
            'red': {
                'language': 'diff',
                'prefix': '- '
            },
            'green': {
                'language': 'diff',
                'prefix': '+ '
            },
            'yellow': {
                'language': 'fix'
            },
            'gray': {
                'language': 'brainfuck'
            }
        }


    @commands.command(aliases=['colortext'])
    async def colourtext(self, ctx, colour: str.lower, *, message):
        '''Will send <message> in <colour> if available'''
        if colour := self._available_colours.get(colour):
            msg = dedent(f'''
                ```{colour['language']}
                {colour.get('prefix', '')}{message}{colour.get('suffix', '')}
                ```
            ''')
            await ctx.send(msg)
        else:
            await self.bot.log(f"{colour} isn't a valid colour. Choose out of {', '.join(list(self._available_colours.keys()))}.", 'error')


    @commands.command()
    async def summarize(self, ctx, *, text: commands.clean_content(remove_markdown=True)):
        '''Will summarize <text> using AI'''
        r = await deepai(ctx, AIDataType.summarize, {'text': text})
        await ctx.send(r['output'] or text)


    @commands.command(aliases=['extractmood', 'sentimentanalysis'])
    async def detectmood(self, ctx, *, text: commands.clean_content(remove_markdown=True)):
        '''Will determine the mood of your <text> using AI'''
        r = await deepai(ctx, AIDataType.sentiment_analysis, {'text': text})
        msg = f"**Text:** {text}\n\n**Sentiment(s):** {', '.join(r['output'])}"
        await ctx.respond(msg)


    @flags.add_flag('--xsize', type=int, default=15)
    @flags.add_flag('--ysize', type=float, default=0.45)
    @flags.add_flag('message', nargs='+')
    @flags.command(
        aliases=['sinewave', 'wiggle'],
        usage='<amount> <message> [--xsize=15 (bigger num = wider)] [--ysize=0.45 (smaller num = taller)]'
    )
    async def worm(self, ctx, amount: int = 1, **options):
        '''Will send your <message> [amount] times in the form of a wave'''
        for _ in range(amount):
            msg = '\n'.join([
                ' ' * (options['xsize'] * (sin(options['ysize'] * i) + 1)) + ' '.join(options['message'])
                for i in range(29)
            ])
            await ctx.send(f'\u200b    {msg}') # because discord strips whitespace


    @commands.command(aliases=['merge'])
    async def combine(self, ctx, word1: str, word2: str):
        '''Will combine <word1> and <word2>'''
        await ctx.send(f"{word1} + {word2} = {''.join([word1[:len(word1) // 2], word2[len(word2) // 2:]])}")


    @commands.command(aliases=['devowel'])
    async def novowel(self, ctx, *, message: str):
        '''Will remove vowels from your <message>'''
        await ctx.send(''.join([l for l in message if l.lower() not in {'a', 'e', 'u', 'i', 'o'}]))


    @commands.command(aliases=['super'])
    async def superscript(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will convert your <message> to ˢᵘᵖᵉʳˢᶜʳᶦᵖᵗ'''
        await ctx.send(sentence_to_superscript(message))


    @commands.command(aliases=['sub'])
    async def subscript(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will convert your <message> to ₛᵤbₛcᵣᵢₚₜ'''
        await ctx.send(sentence_to_subscript(message))


    @commands.command(aliases=['wreplace', 'lreplace'])
    async def replaceword(self, ctx, word1: str, word2: str, *, message: str):
        '''Will replace <word1> with <word2> in <message>'''
        await ctx.send(message.replace(word1, word2))


    @commands.command(aliases=['clap', 'cap'])
    async def emojify(self, ctx, emote: str, *, message: str):
        '''Will emojify your <message>'''
        await ctx.send(message.replace(' ', f' {emote} '))


    @commands.command(aliases=['bold', 'uni'])
    async def regional(self, ctx, *, message: commands.clean_content(remove_markdown=True)  ):
        '''Will turn your <message> into bold letters'''
        await ctx.send('\u200b'.join(list(sentence_to_indicator(message))))


    @commands.command(aliases=['leet'])
    async def leetify(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will |€€†|phЧ your <message>'''
        await ctx.send(sentence_to_leet(message))


    @commands.command()
    async def reversify(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will ɹǝʌǝɹsᴉɟʎ your <message>'''
        await ctx.send(sentence_to_reverse(message))


    @commands.command(aliases=['cancerify'])
    async def furrify(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will ffuwwify :flushed: your <message>'''
        await ctx.send(sentence_to_cancer(message))


    @commands.command(aliases=['oldenglish'])
    async def oldify(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will 𝔬𝔩𝔡𝔦𝔣𝔶 your <message>'''
        await ctx.send(sentence_to_oldenglish(message))


    @commands.command(aliases=['kanji'])
    async def kanjify(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will Ҝ卂几ﾌ丨千ㄚ your <message>'''
        await ctx.send(sentence_to_chink(message))


    @commands.command(aliases=['bubble'])
    async def bubblify(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will 🅑🅤🅑🅑🅛🅘🅕🅨 your <message>'''
        await ctx.send(sentence_to_bubble(message))


    @commands.command(aliases=['square'])
    async def squarify(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will 🅂🅀🅄🄰🅁🄸🄵🅈 your <message>'''
        await ctx.send(sentence_to_square(message))


    @commands.command(aliases=['cursive'])
    async def cursify(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will 𝒸𝓊𝓇𝓈𝒾𝒻𝓎 your <message>'''
        await ctx.send(sentence_to_cursive(message))


    @commands.command(aliases=['mask', 'maskmsg'])
    async def maskmessage(self, ctx, hidden_message: str, *, message: str):
        '''Will hide <hidden_message> in <message>'''
        await ctx.send(message + ('||\u200b||' * 200) + hidden_message)


    @commands.command()
    async def gif(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will send a gif for each letter in your <message>'''
        for l in message:
            if l == ' ':
                await ctx.send('\u200b')
            else:
                await ctx.send(l_to_gif(l))
            await asyncio.sleep(0.8)


    @commands.command(aliases=['invis'])
    async def invisify(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will ||i||||n||||v||||i||||s||||i||||f||||y|| your <message>'''
        await ctx.send(''.join([re.sub(r'\S', f'||{l}||', l) for l in message]))


    @commands.command(aliases=['asciify'])
    async def ascify(self, ctx, _random: Optional[bool] = False, *, message: commands.clean_content(remove_markdown=True)):
        '''Will ascify your <message>'''
        if _random:
            r = await (await self.bot.AIOHTTP_SESSION.get("http://artii.herokuapp.com/fonts_list")).text()
            font = choice(r.splitlines())

        r = await (await self.bot.AIOHTTP_SESSION.get(f"http://artii.herokuapp.com/make?text={parse.quote_plus(message)}{f'&font={font}' if _random else ''}")).text()
        await ctx.textfile(r, clean=False)


    @commands.command(aliases=[''])
    async def mock(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will MoCk your <message>'''
        await ctx.send(''.join([e.upper() if not i % 2 else e for i, e in enumerate(message)]))


    @commands.command()
    async def edit(self, ctx, *, message: str):
        '''Will ed.. through your <message>'''
        msg, counter = await ctx.send(message), 1
        for _ in message:
            try:
                await msg.edit(content=dot_cal(message, counter))
                await asyncio.sleep(1.5)
                counter += 1
            except HTTPException:
                break


    @commands.command(aliases=['nf'])
    async def notfunny(self, ctx):
        '''Will send a not funny message (~2100 chars)'''
        await ctx.send("Not funny I didn't laugh. Your joke is so bad I would have preferred the joke went over my head and you gave up re-telling me the joke. To be honest this is a horrid attempt at trying to get a laugh out of me. Not a chuckle, not a hehe, not even a subtle burst of air out of my esophagus. Science says before you laugh your brain preps your face muscles but I didn't even feel the slightest twitch. 0/10 this joke is so bad I cannot believe anyone legally allowed you to be creative at all. The amount of brain power you must have put into that joke has the potential to power every house on Earth. Get a personality and learn how to make jokes, read a book. I'm not saying this to be funny I genuinely mean it on how this is just bottom barrel embarrassment at comedy. You've single handedly killed humor and every comedic act on the planet.")
        await ctx.send("I'm so disappointed that society has failed as a whole in being able to teach you how to be funny. Honestly if I put in all my power and time to try and make your joke funny it would require Einstein himself to build a device to strap me into so I can be connected to the energy of a billion stars to do it, and even then all that joke would get from people is a subtle scuff. You're lucky I still have the slightest of empathy for you after telling that joke otherwise I would have committed every war crime in the book just to prevent you from attempting any humor ever again. We should put that joke in text books so future generations can be weary of becoming such an absolute comedic failure. Im disappointed, hurt, and outright offended that my precious time has been wasted in my brain understanding that joke. In the time that took I was planning on helping kids who have been orphaned, but because of that you've waisted my time explaining the obscene integrity of your terrible attempt at comedy. Now those kids are suffering without meals and there's nobody to blame but you. I hope you're happy with what you have done and I truly hope you can move on and learn from this piss poor attempt")


    @commands.command(aliases=['nom'], hidden=True)
    async def niggerownermanual(self, ctx, chapter: int = 1):
        '''Very important stuff here about how to properly own and handle a nigger'''
        with open(Path('data/assets/text/manual.txt'), encoding='utf-8') as f:
            chapters = dict(enumerate(f.read().split('%'), 1))
        try:
            title, text = chapters[chapter].split('|')
            await ctx.respond(text, title=f'Chapter {chapter}: {title}')
        except KeyError:
            raise DataNotFound(f'`{chapter}` is not a valid nigger owners manual chapter.')


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['wc'])
    async def wordcloud(self, ctx, limit: int = 100, channel: MultiChannelConverter = None, *filter_users: User):
        '''Will generate a wordcloud from the latest [limit] messages in [channel]'''
        channel = channel or ctx.channel
        wc = WordCloud(
            mask=np.array(Image.open(Path('data/assets/images/discord_mask.png'))),
            contour_width=3,
            contour_color=Colour.random().value
        )
        wc.generate(' '.join([
            m.clean_content for m in
            (await channel.history(limit=limit, before=ctx.message).flatten())
            if not URL_REGEX.search(m.clean_content)
            and (m.author in filter_users if filter_users else True)
        ]))
        fp = BytesIO()
        wc.to_image().save(fp, 'PNG')
        fp.seek(0)
        _file = File(fp, 'wordcloud.png')
        await ctx.respond(image='attachment://wordcloud.png', files=_file)


    @commands.group(invoke_without_command=True, aliases=['mc', 'enchantmentlanguage'])
    async def enchantment(self, _):
        '''Group command for encoding/decoding Minecraft enchantment language'''
        raise commands.CommandNotFound()

    @enchantment.command('encode')
    async def enchantment_encode(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will encode your <message> into enchantment language'''
        await ctx.send(sentence_to_enchantment(message, True))

    @enchantment.command('decode')
    async def enchantment_decode(self, ctx, *, message: str):
        '''Will decode your enchantment language to a string'''
        await ctx.send(sentence_to_enchantment(message, False))


    @commands.group(invoke_without_command=True)
    async def morse(self, _):
        '''Group command for encoding/decoding morse'''
        raise commands.CommandNotFound()

    @morse.command('encode')
    async def morse_encode(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will encode your <message> into morse'''
        await ctx.send(sentence_to_from_morse(message, True))

    @morse.command('decode')
    async def morse_decode(self, ctx, *, message: str):
        '''Will decode your morse <message> to a string'''
        await ctx.send(sentence_to_from_morse(message, False))


    @commands.group(invoke_without_command=True)
    async def binary(self, _):
        '''Group command for encoding/decoding binary'''
        raise commands.CommandNotFound()

    @binary.command('encode')
    async def binary_encode(self, ctx, *, message: commands.clean_content(remove_markdown=True)):
        '''Will encode your <message> to binary (1s and 0s)'''
        await ctx.send(bin(int.from_bytes(message.encode(), 'big')))

    @binary.command('decode')
    async def binary_decode(self, ctx, *, message: str):
        '''Will decode your binary <message> to a string'''
        n = int(message, 2)
        await ctx.send(n.to_bytes((n.bit_length() + 7) // 8, 'big').decode())


    @commands.group(invoke_without_command=True)
    async def base64(self, _):
        '''Group command for encoding/decoding base64'''
        raise commands.CommandNotFound()

    @base64.command('encode')
    async def base64_encode(self, ctx, *, message: str):
        '''Will encode your <message> to base64'''
        await ctx.send(str(base64.b64encode(message.encode('utf-8')), 'utf-8'))

    @base64.command('decode')
    async def base64_decode(self, ctx, *, message: str):
        '''Will decode your base64 <message> to a string'''
        await ctx.send(str(base64.b64decode(message).decode('utf-8')))


    @commands.group(invoke_without_command=True)
    async def qr(self, _):
        '''Group command for encoding text to QR and decoding QR to text'''
        raise commands.CommandNotFound()

    @qr.command('encode', aliases=['create'])
    async def qr_encode(self, ctx, *, message: str):
        '''Will generate a QR code from your <message>'''
        await ctx.respond(image=f'https://api.qrserver.com/v1/create-qr-code/?size=512x512&data={parse.quote_plus(message)}')

    @qr.command('decode', aliases=['read'])
    async def qr_decode(self, ctx, *, image_url: str):
        '''Will decode your qr <image_url> to a string'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'http://api.qrserver.com/v1/read-qr-code/?fileurl={parse.quote_plus(image_url)}')).json()
        await ctx.respond(f"Decoded content: {r[0]['symbol'][0]['data']}")


def setup(bot):
    bot.add_cog(Text(bot))
