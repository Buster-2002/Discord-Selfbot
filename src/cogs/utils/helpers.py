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
        'a': '🇦',
        'b': '🇧',
        'c': '🇨',
        'd': '🇩',
        'e': '🇪',
        'f': '🇫',
        'g': '🇬',
        'h': '🇭',
        'i': '🇮',
        'j': '🇯',
        'k': '🇰',
        'l': '🇱',
        'm': '🇲',
        'n': '🇳',
        'o': '🇴',
        'p': '🇵',
        'q': '🇶',
        'r': '🇷',
        's': '🇸',
        't': '🇹',
        'u': '🇺',
        'v': '🇻',
        'w': '🇼',
        'x': '🇽',
        'y': '🇾',
        'z': '🇿',
        '0': '0️⃣',
        '1': '1️⃣',
        '2': '2️⃣',
        '3': '3️⃣',
        '4': '4️⃣',
        '5': '5️⃣',
        '6': '6️⃣',
        '7': '7️⃣',
        '8': '8️⃣',
        '9': '9️⃣',
        '!': '❗',
        '?': '❓',
        '.': '▪️'
    })

    return sentence.lower().translate(table)


def sentence_to_enchantment(sentence: str, encode: bool) -> str:
    table = {
        'a': 'ᔑ',
        'b': 'ʖ',
        'c': 'ᓵ',
        'd': '↸',
        'e': 'ᒷ',
        'f': '⎓',
        'g': '⊣',
        'h': '⍑',
        'i': '╎',
        'j': '⋮',
        'k': 'ꖌ',
        'l': 'ꖎ',
        'm': 'ᒲ',
        'n': 'リ',
        'o': '𝙹',
        'p': '!¡',
        'q': 'ᑑ',
        'r': '∷',
        's': 'ᓭ',
        't': 'ℸ',
        'u': '⚍',
        'v': '⍊',
        'w': '∴',
        'x': '̇/',
        'y': '||',
        'z': '⨅',
    }

    if not encode:
        table = {v[0]: k for k, v in table.items()}
    return sentence.lower().translate(str.maketrans(table))


def sentence_to_superscript(sentence: str) -> str:
    table = str.maketrans({
        'a': 'ᵃ',
        'b': 'ᵇ',
        'c': 'ᶜ',
        'd': 'ᵈ',
        'e': 'ᵉ',
        'f': 'ᶠ',
        'g': 'ᵍ',
        'h': 'ʰ',
        'i': 'ᶦ',
        'j': 'ʲ',
        'k': 'ᵏ',
        'l': 'ˡ',
        'm': 'ᵐ',
        'n': 'ⁿ',
        'o': 'ᵒ',
        'p': 'ᵖ',
        'q': 'ᵠ',
        'r': 'ʳ',
        's': 'ˢ',
        't': 'ᵗ',
        'u': 'ᵘ',
        'v': 'ᵛ',
        'w': 'ʷ',
        'x': 'ˣ',
        'y': 'ʸ',
        'z': 'ᶻ',
        '1': '¹',
        '2': '²',
        '3': '³',
        '4': '⁴',
        '5': '⁵',
        '6': '⁶',
        '7': '⁷',
        '8': '⁸',
        '9': '⁹'
    })

    return sentence.lower().translate(table)


def sentence_to_subscript(sentence: str) -> str:
    table = str.maketrans({
        'a': 'ₐ',
        'e': 'ₑ',
        'h': 'ₕ',
        'i': 'ᵢ',
        'j': 'ⱼ',
        'k': 'ₖ',
        'l': 'ₗ',
        'm': 'ₘ',
        'n': 'ₙ',
        'o': 'ₒ',
        'p': 'ₚ',
        'r': 'ᵣ',
        's': 'ₛ',
        't': 'ₜ',
        'u': 'ᵤ',
        'v': 'ᵥ',
        'x': 'ₓ',
        '1': '₁',
        '2': '₂',
        '3': '₃',
        '4': '₄',
        '5': '₅',
        '6': '₆',
        '7': '₇',
        '8': '₈',
        '9': '₉'
    })

    return sentence.lower().translate(table)


def sentence_to_leet(sentence: str) -> str:
    table = str.maketrans({
        'a': choice(['4', '@', 'Д']),
        'b': choice(['ß', '13', '(3']),
        'c': choice(['¢', '(', '©']),
        'd': choice(['|)', 'I>', '[)']),
        'e': choice(['3', '€', 'ë']),
        'f': choice(['ƒ', 'ph', 'v']),
        'g': choice(['C-', 'gee', '(.']),
        'h': choice(['/-/', '|-|', '}{']),
        'i': choice(['1', '|', '!']),
        'j': choice(['_|', '._|', '._]']),
        'k': choice(['|<', '/<', '|(']),
        'l': choice(['£', '|_', '|']),
        'm': choice([r'|\/|', '{V}', 'IVI']),
        'n': choice([r'|\|', 'И', 'ท']),
        'o': choice(['0', '()', 'Ø']),
        'p': choice(['|o', '|>', '|7']),
        'q': choice(['0_', '()_']),
        'r': choice(['®', 'Я']),
        's': choice(['5', '$', '§']),
        't': choice(['†', '"|"']),
        'u': choice(['|_|', 'µ', 'บ']),
        'v': choice([r'\/', '|/', r'\|']),
        'w': choice([r'\/\/', 'Ш', 'พ']),
        'x': choice(['><', 'Ж', '×']),
        'y': choice(['Ч', r'\|/', '¥']),
        'z': choice(['-/_', 'z'])
    })

    return sentence.lower().translate(table)


def sentence_to_reverse(sentence: str) -> str:
    table = str.maketrans({
        'a': 'ɐ',
        'b': 'q',
        'c': 'ɔ',
        'd': 'p',
        'e': 'ǝ',
        'f': 'ɟ',
        'g': 'ƃ',
        'h': 'ɥ',
        'i': 'ᴉ',
        'j': 'ɾ',
        'k': 'ʞ',
        'l': 'l',
        'm': 'ɯ',
        'n': 'u',
        'o': 'o',
        'p': 'd',
        'q': 'b',
        'r': 'ɹ',
        's': 's',
        't': 'ʇ',
        'u': 'n',
        'v': 'ʌ',
        'w': 'ʍ',
        'x': 'x',
        'y': 'ʎ',
        'z': 'z',
        '?': '¿',
        '!': '¡',
        '.': '˙',
        '&': '⅋'
    })

    return sentence.lower().translate(table)


def sentence_to_oldenglish(sentence: str) -> str:
    table = str.maketrans({
        'a': '𝔞',
        'b': '𝔟',
        'c': '𝔠',
        'd': '𝔡',
        'e': '𝔢',
        'f': '𝔣',
        'g': '𝔤',
        'h': '𝔷',
        'i': '𝔦',
        'j': '𝔧',
        'k': '𝔨',
        'l': '𝔩',
        'm': '𝔪',
        'n': '𝔫',
        'o': '𝔬',
        'p': '𝔭',
        'q': '𝔮',
        'r': '𝔯',
        's': '𝔰',
        't': '𝔱',
        'u': '𝔲',
        'v': 'v',
        'w': '𝔴',
        'x': '𝔵',
        'y': '𝔶',
        'z': '𝔷'
    })

    return sentence.lower().translate(table)


def sentence_to_chink(sentence: str) -> str:
    table = str.maketrans({
        'a': '卂',
        'b': '乃',
        'c': '匚',
        'd': 'ᗪ',
        'e': '乇',
        'f': '千',
        'g': 'Ꮆ',
        'h': '卄',
        'i': '丨',
        'j': 'ﾌ',
        'k': 'Ҝ',
        'l': 'ㄥ',
        'm': '爪',
        'n': '几',
        'o': 'ㄖ',
        'p': '卩',
        'q': 'Ɋ',
        'r': '尺',
        's': '丂',
        't': 'ㄒ',
        'u': 'ㄩ',
        'v': 'ᐯ',
        'w': '山',
        'x': '乂',
        'y': 'ㄚ',
        'z': '乙'
    })

    return sentence.lower().translate(table)


def sentence_to_bubble(sentence: str) -> str:
    table = str.maketrans({
        'a': '🅐',
        'b': '🅑',
        'c': '🅒',
        'd': '🅓',
        'e': '🅔',
        'f': '🅕',
        'g': '🅖',
        'h': '🅗',
        'i': '🅘',
        'j': '🅙',
        'k': '🅚',
        'l': '🅛',
        'm': '🅜',
        'n': '🅝',
        'o': '🅞',
        'p': '🅟',
        'q': '🅠',
        'r': '🅡',
        's': '🅢',
        't': '🅣',
        'u': '🅤',
        'v': '🅥',
        'w': '🅦',
        'x': '🅧',
        'y': '🅨',
        'z': '🅩',
        '1': '➊',
        '2': '➋',
        '3': '➌',
        '4': '➍',
        '5': '➎',
        '6': '➏',
        '7': '➐',
        '8': '➑',
        '9': '➒'
    })

    return sentence.lower().translate(table)


def sentence_to_square(sentence: str) -> str:
    table = str.maketrans({
        'a': '🄰',
        'b': '🄱',
        'c': '🄲',
        'd': '🄳',
        'e': '🄴',
        'f': '🄵',
        'g': '🄶',
        'h': '🄷',
        'i': '🄸',
        'j': '🄹',
        'k': '🄺',
        'l': '🄻',
        'm': '🄼',
        'n': '🄽',
        'o': '🄾',
        'p': '🄿',
        'q': '🅀',
        'r': '🅁',
        's': '🅂',
        't': '🅃',
        'u': '🅄',
        'v': '🅅',
        'w': '🅆',
        'x': '🅇',
        'y': '🅈',
        'z': '🅉'
    })

    return sentence.lower().translate(table)


def sentence_to_cursive(sentence: str) -> str:
    table = str.maketrans({
        'a': '𝒶',
        'b': '𝒷',
        'c': '𝒸',
        'd': '𝒹',
        'e': '𝑒',
        'f': '𝒻',
        'g': '𝑔',
        'h': '𝒽',
        'i': '𝒾',
        'j': '𝒿',
        'k': '𝓀',
        'l': '𝓁',
        'm': '𝓂',
        'n': '𝓃',
        'o': '𝑜',
        'p': '𝓅',
        'q': '𝓆',
        'r': '𝓇',
        's': '𝓈',
        't': '𝓉',
        'u': '𝓊',
        'v': '𝓋',
        'w': '𝓌',
        'x': '𝓍',
        'y': '𝓎',
        'z': '𝓏'
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
