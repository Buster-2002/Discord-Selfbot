# -*- coding: utf-8 -*-
import asyncio
import operator
import time
from contextlib import suppress
from difflib import SequenceMatcher
from io import BytesIO
from random import choice, randrange
from string import ascii_lowercase
from textwrap import dedent, fill
from typing import Optional, Sequence, Tuple

from akinator.async_aki import Akinator
from discord import File, HTTPException, Message, User
from discord.ext import commands, tasks
from humanize import naturaldelta
from PIL import Image, ImageDraw, ImageFont

from .utils.effects import SOURCESANS
from .utils.helpers import dot_cal
from .utils.tokens import DAGPI_TOKEN


class Games(commands.Cog):
    '''Extension category for all game commands. Some of these work with other users as well as yourself.'''

    def __init__(self, bot):
        self.bot = bot

        self._gtw_message = None
        self._gtw_keyword = str()
        self._gtw_counter = 1
        self._arithmetic_operators = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul
        }
        self._hangman_stages = [
            r'''
            _________
            |/      |
            |      😵
            |      \|/
            |       |
            |      / \
         ___|___
            ''',
            r'''
            _________
            |/      |
            |      😦
            |      \|/
            |       |
            |      /
         ___|___
            ''',
            r'''
            _________
            |/      |
            |      😦
            |      \|/
            |       |
            |
         ___|___
            ''',
            r'''
            --------
            |/     |
            |     😦
            |     \|
            |      |
            |
         ___|___
            ''',
            '''
            _________
            |/      |
            |      😦
            |       |
            |       |
            |
         ___|___
            ''',
            '''
            _________
            |/      |
            |      😦
            |
            |
            |
         ___|___
            ''',
            '''
            _________
            |/      |
            |
            |
            |
            |
         ___|___
            ''',
            '''
            _________
            |/
            |
            |
            |
            |
         ___|___
            ''',
            '''
            ___
            |/
            |
            |
            |
            |
         ___|___
            '''
        ]


    @staticmethod
    def _is_similar(a: Sequence[str], b: Sequence[str], percent: float) -> Tuple[bool, float]:
        if (similarity := SequenceMatcher(None, a, b).ratio() * 100) >= percent:
            return True, similarity
        return False, similarity


    @staticmethod
    def _text_image(text: str) -> File:
        font = ImageFont.truetype(SOURCESANS, 30)
        text = fill(text, 50)
        TW, TH = font.getsize_multiline(text)
        new = Image.new('RGBA', (max(400, TW), (TH + 10)))
        W, H = new.size
        draw = ImageDraw.Draw(new)
        draw.multiline_text((0, 0), text, 'white', font)

        # add lines to counter OCR
        for i in range(W // 10, W, W // 5):
            draw.line([i, 0, i, H], (255, 255, 255, 80), 1)

        fp = BytesIO()
        new.save(fp, 'PNG')
        fp.seek(0)
        return File(fp, 'typeracer.png')


    def cog_unload(self):
        self._gtw_update.cancel()


    @commands.command(aliases=['ms'])
    async def minesweeper(self, ctx, columns: int = 9, rows: int = 9, bombs: int = 15):
        '''Will allow you to play a game of minesweeper'''
        if columns not in range(2, 13) or rows not in range(2, 13):
            raise commands.BadArgument('Both the columns and rows have to be between 2 and 13.')

        grid, count = [[0 for _ in range(columns)] for _ in range(rows)], 0
        while count <= bombs:
            x = randrange(columns)
            y = randrange(rows)
            if grid[y][x] == 0:
                grid[y][x] = 'B'
                count += 1

        pos_x, pos_y = 0, 0
        while pos_x * pos_y < columns * rows and pos_y < rows:
            adj_sum = 0
            for adj_y, adj_x in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
                with suppress(IndexError):
                    if (
                        grid[adj_y + pos_y][adj_x + pos_x] == 'B'
                        and adj_y + pos_y > -1
                        and adj_x + pos_x > -1
                    ):
                        adj_sum += 1

            if grid[pos_y][pos_x] != 'B':
                grid[pos_y][pos_x] = adj_sum
            if pos_x == columns - 1:
                pos_x = 0
                pos_y += 1
            else:
                pos_x += 1

        formatted = '\n'.join([''.join(map(str, the_rows)) for the_rows in grid])
        final = formatted.translate(
            str.maketrans({
                '0': '||:zero:||',
                '1': '||:one:||',
                '2': '||:two:||',
                '3': '||:three:||',
                '4': '||:four:||',
                '5': '||:five:||',
                '6': '||:six:||',
                '7': '||:seven:||',
                '8': '||:eight:||',
                'B': '||:bomb:||'
            })
        )
        await ctx.send(final)


    @commands.command(
        aliases=['wtif', 'whotypesitfaster'],
        usage='[accuracy=97.0 (how similar the answer has to be to the actual sentence)] [sentence=random]'
    )
    async def typeracer(self, ctx, accuracy: Optional[float] = 97.0, *, sentence: str = None):
        '''Will allow you to play a game of who types it faster'''
        if not sentence:
            r = await (await self.bot.AIOHTTP_SESSION.get('https://randomwordgenerator.com/json/sentences.json')).json()
            sentence = choice(r['data'])['sentence']

        msg = await ctx.send('The typerace sentence is...')
        await asyncio.sleep(randrange(1, 4))
        starttime = time.perf_counter()
        await msg.edit(content='Type over the following sentence:')
        _file = await self.bot.loop.run_in_executor(None, lambda: self._text_image(sentence))
        await ctx.send(file=_file)

        similarity = 0
        def check(message: Message) -> bool:
            nonlocal similarity
            b, similarity = self._is_similar(
                ' '.join(message.content.split()).casefold(),
                ' '.join(sentence.split()).casefold(),
                accuracy
            )
            return b and message.channel == ctx.channel

        done = False
        while not done:
            try:
                response = await self.bot.wait_for(
                    'message',
                    check=check,
                    timeout=120
                )
                done = True
            except asyncio.TimeoutError:
                with suppress(HTTPException):
                    await msg.delete()
                break
        else:
            await msg.delete()
            delta = time.perf_counter() - starttime
            WPM = round((len(sentence) / 5) / (delta / 60))
            await ctx.respond(f'{response.author.mention} has won by being the first to correctly type the sentence!\n(~{naturaldelta(delta)} passed with ~{WPM} WPM and {similarity:.2f}% accuracy)', show_speed=False)


    @tasks.loop(seconds=5)
    async def _gtw_update(self):
        try:
            await self._gtw_message.edit(content=f'Guess the keyword starting with (case insensitive):\n`{dot_cal(self._gtw_keyword, self._gtw_counter)}`')
            self._gtw_counter += 1
        except HTTPException:
            self._gtw_update.cancel()

    @commands.command(aliases=['gtw'])
    async def guesstheword(self, ctx, *, word: str = None):
        '''Will allow you to play a game of guess the word'''
        if not word:
            r = await (await self.bot.AIOHTTP_SESSION.get('https://randomwordgenerator.com/json/words.json')).json()
            self._gtw_keyword = choice(r['data'])['word'].casefold()

        self._gtw_message = await ctx.send('Guess the word...')
        await asyncio.sleep(randrange(1, 4))
        starttime = time.perf_counter()
        self._gtw_update.start()

        done = False
        while not done:
            try:
                response = await self.bot.wait_for(
                    'message',
                    check=lambda m: (
                        m.channel == ctx.channel
                        and m.content.casefold() == self._gtw_keyword
                    ),
                    timeout=60
                )
                done = True
            except asyncio.TimeoutError:
                with suppress(HTTPException):
                    await self._gtw_message.delete()
                self._gtw_update.cancel()
                break
        else:
            await self._gtw_message.delete()
            self._gtw_update.cancel()
            await ctx.respond(
                f'{response.author.mention} has won by being the first to correctly guess the keyword!\n(~{naturaldelta(time.perf_counter() - starttime)} passed, the answer was {self._gtw_keyword})',
                show_speed=False,
                title='Guess The Word'
            )


    @commands.command(aliases=['gtt'])
    async def guessthetiming(self, ctx, seconds: Optional[int] = 10, player: User = None):
        '''Will allow you to play a game of guess timing'''
        starttime = time.perf_counter()
        player = player or ctx.me
        if player != ctx.me:
            text = f'{player.mention}, react to this message with 👍🏻 in {seconds}s'
            event = 'reaction_add'
            thingmebob = 'Reacted'
        else:
            text = f'Remove the 👍🏻 reaction to this message in {seconds}s'
            event = 'reaction_remove'
            thingmebob = 'Unreacted'

        msg = await ctx.respond(text, show_speed=False, do_delete=False)
        await msg.add_reaction('👍🏻')

        try:
            await self.bot.wait_for(
                event,
                check=lambda r, u: (
                    r.message == msg
                    and u == player
                ),
                timeout=(seconds * 3)
            )
        except asyncio.TimeoutError:
            with suppress(HTTPException):
                await msg.delete()
            return

        await msg.delete()
        reacted_after = time.perf_counter() - starttime
        await ctx.respond(
            f"{thingmebob} after {reacted_after:.2f} seconds, which means that {player.mention} was off by {abs(((reacted_after - seconds) / seconds) * 100):.2f}% with {abs((time.perf_counter() - starttime) - seconds):.2f} seconds",
            show_speed=False,
            title='Guess The Timing'
        )


    @commands.command(aliases=['guesstheflag'])
    async def doyouknowthisflag(self, ctx):
        '''Will allow you to play a game of do you know this flag?'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://api.dagpi.xyz/data/flag', headers={'Authorization': DAGPI_TOKEN})).json()
        msg = await ctx.send('What flag is this...')
        await asyncio.sleep(randrange(1, 4))
        starttime = time.perf_counter()
        flag = await ctx.send(r['flag'])
        data = r['Data']
        possible_answers = {
            answer.casefold() for answer in
            [
                *data['altSpellings'],
                *[d['common'] for d in data['translations'].values()],
                data['name']['common']
            ]
        }

        done = False
        while not done:
            try:
                response = await self.bot.wait_for(
                    'message',
                    check=lambda m: (
                        m.channel == ctx.channel
                        and m.content.casefold() in possible_answers
                    ),
                    timeout=60
                )
                done = True
            except asyncio.TimeoutError:
                with suppress(HTTPException):
                    await msg.delete()
                    await flag.delete()
                break
        else:
            await msg.delete()
            await flag.delete()
            await ctx.respond(
                f"{response.author.mention} has won by being the first to answer correctly!\n(~{naturaldelta(time.perf_counter() - starttime)} passed, the answer was {data['name']['common']})",
                show_speed=False,
                title='Guess The Flag'
            )

    @commands.command()
    async def guessthelogo(self, ctx):
        '''Will allow you to play a game of guess the logo'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://api.dagpi.xyz/data/logo', headers={'Authorization': DAGPI_TOKEN})).json()
        msg = await ctx.send('Guess the logo...')
        await asyncio.sleep(randrange(1, 4))
        starttime = time.perf_counter()
        logo = await ctx.send(r['question'])

        done = False
        while not done:
            try:
                response = await self.bot.wait_for(
                    'message',
                    check=lambda m: (
                        m.channel == ctx.channel
                        and m.content.casefold() == r['brand'].casefold()
                    ),
                    timeout=60
                )
                done = True
            except asyncio.TimeoutError:
                with suppress(HTTPException):
                    await msg.delete()
                    await logo.delete()
                break
        else:
            await msg.delete()
            await logo.delete()
            await ctx.respond(
                f"{response.author.mention} has won by being the first to guess the logo\'s brand correctly!\n(~{naturaldelta(time.perf_counter() - starttime)} passed, the answer was {r['brand']})",
                show_speed=False,
                title='Guess The Logo'
            )


    @commands.command(aliases=['math'])
    async def solvetheequation(self, ctx):
        '''Will see who is the fastest at answering a simple math question'''
        num1, num2 = randrange(0, 13), randrange(2, 11)
        op = choice(list(self._arithmetic_operators.keys()))
        answer = str(int(self._arithmetic_operators.get(op)(num1, num2)))
        question = f'`{num1} {op} {num2}`'

        msg = await ctx.send('Solve the equation...')
        await asyncio.sleep(randrange(1, 4))
        starttime = time.perf_counter()
        await msg.edit(content=question)

        done = False
        while not done:
            try:
                response = await self.bot.wait_for(
                    'message',
                    check=lambda m: (
                        m.channel == ctx.channel
                        and m.content.strip() == answer
                    ),
                    timeout=60
                )
                done = True
            except asyncio.TimeoutError:
                with suppress(HTTPException):
                    await msg.delete()
                break
        else:
            await msg.delete()
            await ctx.respond(
                f'{response.author.mention} has won by being the first to solve the equation!\n(~{naturaldelta(time.perf_counter() - starttime)} passed, the answer was {answer})',
                show_speed=False,
                title='Solve The Equation'
            )


    @commands.command(aliases=['aki'])
    async def akinator(self, ctx, player: User = None):
        '''Will allow you to play a game of akinator'''
        player = player or ctx.author
        aki = Akinator()
        q = await aki.start_game()
        menu = dedent('''
            **{}**

            0: Yes
            1: No
            2: I don't know
            3: Probably
            4: Probably not

            *(Type the response num in chat)*
        ''')
        msg = await ctx.send(menu.format(q.strip()))
        possible_answers = {'yes', 'y', '0', 'n', 'no', '1', 'i', 'idk', '2', 'p', 'probably', '3', 'pn', 'probably not', '4'}
        while aki.progression < 81:
            try:
                response = await self.bot.wait_for(
                    'message',
                    check=lambda m: (
                        m.channel == ctx.channel
                        and m.content.strip().casefold() in possible_answers
                        and m.author == player
                    ),
                    timeout=60
                )
                try:
                    await response.delete()
                    q = await aki.answer(response.content)
                    await msg.edit(content=menu.format(q.strip()))
                except:
                    continue
            except (asyncio.TimeoutError, HTTPException):
                with suppress(HTTPException):
                    await msg.delete()
                break
        else:
            await aki.win()
            await msg.delete()
            await ctx.respond(f"I am {(float(aki.first_guess['proba']) * 100):.1f}% sure it's {aki.first_guess['name']} - {aki.first_guess['description']}!", aki.first_guess['absolute_picture_path'])


    @commands.command()
    async def hangman(self, ctx, player: User = None, lives: int = 8, *, word: str = None):
        '''Will allow you to play a game of hangman'''
        player = player or ctx.author
        if not word:
            r = await (await self.bot.AIOHTTP_SESSION.get('https://randomwordgenerator.com/json/words.json')).json()
            word = choice(r['data'])['word'].casefold()

        alpha, letters, wrong, correct, counter, guesses = set(ascii_lowercase), list(word), [], [r'\_' for _ in word], lives, 0
        lives = lambda: f"`{'❤️' * counter}`"
        menu = dedent('''
        ```
        {}
        ```
        Correct: {}
        Wrong: {}
        Lives left: {}
        ''')
        msg = await ctx.send(menu.format(
            self._hangman_stages[counter],
            ' '.join(correct),
            ', '.join(wrong),
            lives()
        ))

        done = False
        while not done:
            try:
                response = await self.bot.wait_for(
                    'message',
                    check=lambda m: (
                        m.channel == ctx.channel
                        and len(m.content) == 1
                        and (m.content.casefold() in alpha)
                        or (m.content.casefold() == word)
                        and m.author == player
                    ),
                    timeout=60
                )

                await response.delete()
                answer = response.content.casefold()
                guesses += 1

                if answer == word:
                    done = True
                else:
                    if answer in word:
                        for m in [i for i, l in enumerate(letters) if l == answer]:
                            correct[m] = answer
                    else:
                        wrong.append(answer)
                        counter -= 1

                    if ''.join(correct) == word:
                        done = True

                    if counter == 0:
                        msg = dedent(f'''
                            ```
                            {self._hangman_stages[0]}
                            ```
                            **{player.mention}, you lost!** The word was {word}.
                        ''')
                        await ctx.respond(msg, show_speed=False)
                        break

                    alpha.remove(answer)
                    await msg.edit(content=menu.format(
                        self._hangman_stages[counter],
                        ' '.join(correct),
                        ', '.join(wrong),
                        lives()
                    ))

            except (asyncio.TimeoutError, HTTPException):
                with suppress(HTTPException):
                    await msg.delete()
                break

        else:
            await msg.delete()
            await ctx.respond(f"You won! The word was {word}, and you guessed it in {guesses} tries.", show_speed=False)


def setup(bot):
    bot.add_cog(Games(bot))
