# -*- coding: utf-8 -*-
import asyncio
import json
import string
from datetime import datetime
from pathlib import Path
from random import choice, choices, randrange
from typing import Any, Tuple, Union

from discord import NotFound, PremiumType
from discord.ext import commands

from .enums import AIDataType
from .exceptions import BadSettings, NoPasswordSet
from .tokens import DEEPAI_TOKEN
from .wizard import DEFAULT


def sentence_to_indicator(sentence: str) -> str:
    table = str.maketrans({
        'a': '๐ฆ',
        'b': '๐ง',
        'c': '๐จ',
        'd': '๐ฉ',
        'e': '๐ช',
        'f': '๐ซ',
        'g': '๐ฌ',
        'h': '๐ญ',
        'i': '๐ฎ',
        'j': '๐ฏ',
        'k': '๐ฐ',
        'l': '๐ฑ',
        'm': '๐ฒ',
        'n': '๐ณ',
        'o': '๐ด',
        'p': '๐ต',
        'q': '๐ถ',
        'r': '๐ท',
        's': '๐ธ',
        't': '๐น',
        'u': '๐บ',
        'v': '๐ป',
        'w': '๐ผ',
        'x': '๐ฝ',
        'y': '๐พ',
        'z': '๐ฟ',
        '0': '0๏ธโฃ',
        '1': '1๏ธโฃ',
        '2': '2๏ธโฃ',
        '3': '3๏ธโฃ',
        '4': '4๏ธโฃ',
        '5': '5๏ธโฃ',
        '6': '6๏ธโฃ',
        '7': '7๏ธโฃ',
        '8': '8๏ธโฃ',
        '9': '9๏ธโฃ',
        '!': 'โ',
        '?': 'โ',
        '.': 'โช๏ธ'
    })

    return sentence.lower().translate(table)


def sentence_to_enchantment(sentence: str, encode: bool) -> str:
    table = {
        'a': 'แ',
        'b': 'ส',
        'c': 'แต',
        'd': 'โธ',
        'e': 'แท',
        'f': 'โ',
        'g': 'โฃ',
        'h': 'โ',
        'i': 'โ',
        'j': 'โฎ',
        'k': '๊',
        'l': '๊',
        'm': 'แฒ',
        'n': 'ใช',
        'o': '๐น',
        'p': '!ยก',
        'q': 'แ',
        'r': 'โท',
        's': 'แญ',
        't': 'โธ',
        'u': 'โ',
        'v': 'โ',
        'w': 'โด',
        'x': 'ฬ/',
        'y': '||',
        'z': 'โจ',
    }

    if not encode:
        table = {v[0]: k for k, v in table.items()}
    return sentence.lower().translate(str.maketrans(table))


def sentence_to_superscript(sentence: str) -> str:
    table = str.maketrans({
        'a': 'แต',
        'b': 'แต',
        'c': 'แถ',
        'd': 'แต',
        'e': 'แต',
        'f': 'แถ?',
        'g': 'แต',
        'h': 'สฐ',
        'i': 'แถฆ',
        'j': 'สฒ',
        'k': 'แต',
        'l': 'หก',
        'm': 'แต',
        'n': 'โฟ',
        'o': 'แต',
        'p': 'แต',
        'q': 'แต?',
        'r': 'สณ',
        's': 'หข',
        't': 'แต',
        'u': 'แต',
        'v': 'แต',
        'w': 'สท',
        'x': 'หฃ',
        'y': 'สธ',
        'z': 'แถป',
        '1': 'ยน',
        '2': 'ยฒ',
        '3': 'ยณ',
        '4': 'โด',
        '5': 'โต',
        '6': 'โถ',
        '7': 'โท',
        '8': 'โธ',
        '9': 'โน'
    })

    return sentence.lower().translate(table)


def sentence_to_subscript(sentence: str) -> str:
    table = str.maketrans({
        'a': 'โ',
        'e': 'โ',
        'h': 'โ',
        'i': 'แตข',
        'j': 'โฑผ',
        'k': 'โ',
        'l': 'โ',
        'm': 'โ',
        'n': 'โ',
        'o': 'โ',
        'p': 'โ',
        'r': 'แตฃ',
        's': 'โ',
        't': 'โ',
        'u': 'แตค',
        'v': 'แตฅ',
        'x': 'โ',
        '1': 'โ',
        '2': 'โ',
        '3': 'โ',
        '4': 'โ',
        '5': 'โ',
        '6': 'โ',
        '7': 'โ',
        '8': 'โ',
        '9': 'โ'
    })

    return sentence.lower().translate(table)


def sentence_to_leet(sentence: str) -> str:
    table = str.maketrans({
        'a': choice(['4', '@', 'ะ']),
        'b': choice(['ร', '13', '(3']),
        'c': choice(['ยข', '(', 'ยฉ']),
        'd': choice(['|)', 'I>', '[)']),
        'e': choice(['3', 'โฌ', 'รซ']),
        'f': choice(['ฦ', 'ph', 'v']),
        'g': choice(['C-', 'gee', '(.']),
        'h': choice(['/-/', '|-|', '}{']),
        'i': choice(['1', '|', '!']),
        'j': choice(['_|', '._|', '._]']),
        'k': choice(['|<', '/<', '|(']),
        'l': choice(['ยฃ', '|_', '|']),
        'm': choice([r'|\/|', '{V}', 'IVI']),
        'n': choice([r'|\|', 'ะ', 'เธ']),
        'o': choice(['0', '()', 'ร']),
        'p': choice(['|o', '|>', '|7']),
        'q': choice(['0_', '()_']),
        'r': choice(['ยฎ', 'ะฏ']),
        's': choice(['5', '$', 'ยง']),
        't': choice(['โ?', '"|"']),
        'u': choice(['|_|', 'ยต', 'เธ']),
        'v': choice([r'\/', '|/', r'\|']),
        'w': choice([r'\/\/', 'ะจ', 'เธ']),
        'x': choice(['><', 'ะ', 'ร']),
        'y': choice(['ะง', r'\|/', 'ยฅ']),
        'z': choice(['-/_', 'z'])
    })

    return sentence.lower().translate(table)


def sentence_to_reverse(sentence: str) -> str:
    table = str.maketrans({
        'a': 'ษ',
        'b': 'q',
        'c': 'ษ',
        'd': 'p',
        'e': 'ว',
        'f': 'ษ',
        'g': 'ฦ',
        'h': 'ษฅ',
        'i': 'แด',
        'j': 'ษพ',
        'k': 'ส',
        'l': 'l',
        'm': 'ษฏ',
        'n': 'u',
        'o': 'o',
        'p': 'd',
        'q': 'b',
        'r': 'ษน',
        's': 's',
        't': 'ส',
        'u': 'n',
        'v': 'ส',
        'w': 'ส',
        'x': 'x',
        'y': 'ส',
        'z': 'z',
        '?': 'ยฟ',
        '!': 'ยก',
        '.': 'ห',
        '&': 'โ'
    })

    return sentence.lower().translate(table)


def sentence_to_oldenglish(sentence: str) -> str:
    table = str.maketrans({
        'a': '๐',
        'b': '๐',
        'c': '๐?',
        'd': '๐ก',
        'e': '๐ข',
        'f': '๐ฃ',
        'g': '๐ค',
        'h': '๐ท',
        'i': '๐ฆ',
        'j': '๐ง',
        'k': '๐จ',
        'l': '๐ฉ',
        'm': '๐ช',
        'n': '๐ซ',
        'o': '๐ฌ',
        'p': '๐ญ',
        'q': '๐ฎ',
        'r': '๐ฏ',
        's': '๐ฐ',
        't': '๐ฑ',
        'u': '๐ฒ',
        'v': 'v',
        'w': '๐ด',
        'x': '๐ต',
        'y': '๐ถ',
        'z': '๐ท'
    })

    return sentence.lower().translate(table)


def sentence_to_chink(sentence: str) -> str:
    table = str.maketrans({
        'a': 'ๅ',
        'b': 'ไน',
        'c': 'ๅ',
        'd': 'แช',
        'e': 'ไน',
        'f': 'ๅ',
        'g': 'แถ',
        'h': 'ๅ',
        'i': 'ไธจ',
        'j': '๏พ',
        'k': 'า',
        'l': 'ใฅ',
        'm': '็ช',
        'n': 'ๅ?',
        'o': 'ใ',
        'p': 'ๅฉ',
        'q': 'ษ',
        'r': 'ๅฐบ',
        's': 'ไธ',
        't': 'ใ',
        'u': 'ใฉ',
        'v': 'แฏ',
        'w': 'ๅฑฑ',
        'x': 'ไน',
        'y': 'ใ',
        'z': 'ไน'
    })

    return sentence.lower().translate(table)


def sentence_to_bubble(sentence: str) -> str:
    table = str.maketrans({
        'a': '๐',
        'b': '๐',
        'c': '๐',
        'd': '๐',
        'e': '๐',
        'f': '๐',
        'g': '๐',
        'h': '๐',
        'i': '๐',
        'j': '๐',
        'k': '๐',
        'l': '๐',
        'm': '๐',
        'n': '๐',
        'o': '๐',
        'p': '๐',
        'q': '๐?',
        'r': '๐ก',
        's': '๐ข',
        't': '๐ฃ',
        'u': '๐ค',
        'v': '๐ฅ',
        'w': '๐ฆ',
        'x': '๐ง',
        'y': '๐จ',
        'z': '๐ฉ',
        '1': 'โ',
        '2': 'โ',
        '3': 'โ',
        '4': 'โ',
        '5': 'โ',
        '6': 'โ',
        '7': 'โ',
        '8': 'โ',
        '9': 'โ'
    })

    return sentence.lower().translate(table)


def sentence_to_square(sentence: str) -> str:
    table = str.maketrans({
        'a': '๐ฐ',
        'b': '๐ฑ',
        'c': '๐ฒ',
        'd': '๐ณ',
        'e': '๐ด',
        'f': '๐ต',
        'g': '๐ถ',
        'h': '๐ท',
        'i': '๐ธ',
        'j': '๐น',
        'k': '๐บ',
        'l': '๐ป',
        'm': '๐ผ',
        'n': '๐ฝ',
        'o': '๐พ',
        'p': '๐ฟ',
        'q': '๐',
        'r': '๐',
        's': '๐',
        't': '๐',
        'u': '๐',
        'v': '๐',
        'w': '๐',
        'x': '๐',
        'y': '๐',
        'z': '๐'
    })

    return sentence.lower().translate(table)


def sentence_to_cursive(sentence: str) -> str:
    table = str.maketrans({
        'a': '๐ถ',
        'b': '๐ท',
        'c': '๐ธ',
        'd': '๐น',
        'e': '๐',
        'f': '๐ป',
        'g': '๐',
        'h': '๐ฝ',
        'i': '๐พ',
        'j': '๐ฟ',
        'k': '๐',
        'l': '๐',
        'm': '๐',
        'n': '๐',
        'o': '๐',
        'p': '๐',
        'q': '๐',
        'r': '๐',
        's': '๐',
        't': '๐',
        'u': '๐',
        'v': '๐',
        'w': '๐',
        'x': '๐',
        'y': '๐',
        'z': '๐'
    })

    return sentence.lower().translate(table)


def sentence_to_from_morse(sentence: str, encode: bool) -> str:
    table = {
        'A': '.-',
        'B': '-...',
        'C': '-.-.',
        'D': '-..',
        'E': '.',
        'F': '..-.',
        'G': '--.',
        'H': '....',
        'I': '..',
        'J': '.---',
        'K': '-.-',
        'L': '.-..',
        'M': '--',
        'N': '-.',
        'O': '---',
        'P': '.--.',
        'Q': '--.-',
        'R': '.-.',
        'S': '...',
        'T': '-',
        'U': '..-',
        'V': '...-',
        'W': '.--',
        'X': '-..-',
        'Y': '-.--',
        'Z': '--..',
        '0': '-----',
        '1': '.----',
        '2': '..---',
        '3': '...--',
        '4': '....-',
        '5': '.....',
        '6': '-....',
        '7': '--...',
        '8': '---..',
        '9': '----.',
        ',': '--..--',
        '.': '.-.-.-',
        '?': '..--..',
        '/': '-..-.',
        '-': '-....-',
        '(': '-.--.',
        ')': '-.--.-'
    }

    if encode:
        return ' '.join([table.get(c.upper(), c) for c in sentence.lower()])
    return ''.join([{v: k for k, v in table.items()}.get(w) for w in sentence.split()])


def l_to_gif(character: str) -> str:
    table = {
        'a': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-a-50-transa.gif',
        'b': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-b-50-transa.gif',
        'c': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-c-50-transa.gif',
        'd': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-d-50-transa.gif',
        'e': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-e-50-transa.gif',
        'f': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-f-50-transa.gif',
        'g': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-g-50-transa.gif',
        'h': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-h-50-transa.gif',
        'i': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-i-50-transa.gif',
        'j': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-j-50-transa.gif',
        'k': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-k-50-transa.gif',
        'l': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-l-50-transa.gif',
        'm': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-m-50-transa.gif',
        'n': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-n-50-transa.gif',
        'o': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-o-50-transa.gif',
        'p': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-p-50-transa.gif',
        'q': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-q-50-transa.gif',
        'r': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-r-50-transa.gif',
        's': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-s-50-transa.gif',
        't': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-t-50-transa.gif',
        'u': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-u-50-transa.gif',
        'v': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-v-50-transa.gif',
        'w': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-w-50-transa.gif',
        'x': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-x-50-transa.gif',
        'y': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-y-50-transa.gif',
        'z': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-z-50-transa.gif',
        '0': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-0-50-transa.gif',
        '1': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-1-50-transa.gif',
        '2': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-2-50-transa.gif',
        '3': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-3-50-transa.gif',
        '4': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-4-50-transa.gif',
        '5': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-5-50-transa.gif',
        '6': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-6-50-transa.gif',
        '7': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-7-50-transa.gif',
        '8': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-8-50-transa.gif',
        '9': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-9-50-transa.gif',
        '!': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-exclaim-50-transa.gif',
        '@': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-at-50-transa.gif',
        '&': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-and-50-transa.gif',
        '$': 'https://www.artiestick.com/toons/alphabet/ralph/color_cycling/arg-dollar-50-transa.gif'
    }

    return table.get(character.lower(), character)


def sentence_to_cancer(sentence: str) -> str:
    if sentence.startswith('http'):
        return sentence
    return ' '.join(map(str.strip, list((f'{w} ' + choices(*zip(*{k: v for k, v in zip(('', '^_^', ':3', '> <', '~', 'OwO', 'UwU', ':heart:', ':flushed:', ':pleading_face:', '*daddy*', '*nuzzles*', '*rawr*'), [150] + [10] * 12)}.items()))[0]) if len(w) > 3 else w for w in list((w.translate(str.maketrans({'l': 'w', 'r': 'w', 's': 'ws'}))) if len(w) > 3 else w for w in list((w[0] + '-' * choices(*zip(*{k:v for k, v in zip(range(3), (50, 25, 10))}.items()))[0] + w) if len(w) > 2 else w for w in sentence.split())))))


def dot_cal(message: str, counter: int = 0) -> str:
    return ''.join(c if (i < counter or c == ' ') else '.' for i, c in enumerate(message))


def random_string(amount: int) -> str:
    return ''.join((choices(string.ascii_letters + string.digits, k=amount)))


def get_blank_message(_bot: commands.Bot, length: int = None) -> str:
    if length:
        limit = length
    else:
        premium, limit = _bot.user.premium_type, 2000
        if premium in {PremiumType.nitro, PremiumType.nitro_classic}:
            limit = 4000
    return '\u200c' + '\n' * (limit - 2) + '\u200c'


async def animate(
    ctx,
    filename: str,
    *args,
    sleep: int = None,
    edit: bool = True,
    lines: bool = True
):
    with open(Path(f'data/assets/text/{filename}.txt'), encoding='utf-8') as f:
        if lines:
            animation = f.read().format(*args).splitlines()
        else:
            animation = f.read().split('%')

    base = await ctx.send(animation[0])
    for line in animation[1:]:
        await asyncio.sleep(sleep or randrange(1, 4))
        if edit:
            try:
                await base.edit(content=line)
            except NotFound:
                break
        else:
            await ctx.send(line)

    if edit:
        await base.delete(delay=sleep or randrange(1, 4))


async def self_edit(ctx, **kwargs):
    if ctx.bot.PASSWORD:
        try:
            await ctx.bot.user.edit(**kwargs, password=ctx.bot.PASSWORD)
        except:
            raise BadSettings(f"Couldn't change {', '.join(kwargs.keys())}, probably due to an invalid password in the config.")
    else:
        raise NoPasswordSet()


def change_config(keys: Tuple[str], val: Any = 'PLACEHOLDER') -> str:
    with open(Path('data/json/config.json'), 'r+', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            f.seek(0)
            f.truncate(0)
            json.dump(DEFAULT, f, indent=4)
            data = DEFAULT

    with open(Path('data/json/config.json'), 'w', encoding='utf-8') as f:
        data_cur = data
        for key in keys[:-1]:
            data_cur = data_cur[key]
        data_cur[keys[-1]] = val
        json.dump(data, f, indent=4)
        return val


def default_headers(instance: Union[commands.Context, commands.Bot, str]) -> dict:
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Origin': 'https://discord.com',
        'Pragma': 'no-cache',
        'Referer': 'https://discord.com/channels/@me',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Authorization': instance
    }
    if isinstance(instance, commands.Context):
        http = instance.bot.http
    elif isinstance(instance, commands.Bot):
        http = instance.http
    if isinstance(instance, (commands.Bot, commands.Context)):
        headers['Authorization'] = http.token
        headers['User-Agent'] = http.user_agent
        headers['X-Super-Properties'] = http.encoded_super_properties
        headers['Sec-CH-UA'] = '"Google Chrome";v="{0}", "Chromium";v="{0}", ";Not A Brand";v="99"'.format(http.browser_version.split('.')[0])

    return headers


def format_date(dt: datetime) -> str:
    return f'<t:{int(dt.timestamp())}:R>'


async def deepai(
    ctx,
    name: AIDataType,
    data: dict
) -> dict:
    return await (await ctx.bot.AIOHTTP_SESSION.post(
        f'https://api.deepai.org/api/{name}',
        data=data,
        headers={'api-key': DEEPAI_TOKEN}
    )).json()
