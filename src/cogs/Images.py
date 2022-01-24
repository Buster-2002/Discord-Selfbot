# -*- coding: utf-8 -*-
import json
import string
import urllib.parse
from random import choices, randrange

from aiohttp import ContentTypeError
from discord import Colour, utils
from discord.ext import commands

from .utils import flags
from .utils.checks import bot_has_permissions
from .utils.converters import ImageConverter, LanguageConverter
from .utils.effects import draw_bounding_boxes, piechart
from .utils.enums import AIDataType
from .utils.exceptions import DataNotFound
from .utils.helpers import deepai, random_string
from .utils.tokens import OCRSPACE_TOKEN


class Images(commands.Cog):
    '''Category with all image commands. These either return an image or edit an existing one.'''

    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def animal(self, ctx, animal: str):
        '''Will send a random <animal> image and fact'''
        try:
            r = await (await self.bot.AIOHTTP_SESSION.get(f'https://some-random-api.ml/animal/{animal}')).json()
            await ctx.respond(r['fact'], r['image'])
        except ContentTypeError:
            r1 = await (await self.bot.AIOHTTP_SESSION.get(f'https://aussie-apis.ml/facts/{animal}')).json()
            r2 = await (await self.bot.AIOHTTP_SESSION.get(f'https://aussie-apis.ml/img/{animal}')).json()
            await ctx.respond(r1['Link'], r2['Link'])
        except:
            raise DataNotFound(f'The animal `{animal}` couldn\'t be found.')


    @commands.command(aliases=['resizeimage', 'resizegif'])
    async def resize(self, ctx, link: ImageConverter, width: int = 512, height: int = 512, keep_aspect_ratio: bool = False):
        '''Will resize your <link> to [width] [height] dimensions'''
        if keep_aspect_ratio:
            await ctx.polaroid('thumbnail', link, width, height)
        else:
            await ctx.polaroid('resize', link, width, height, 5)


    @commands.command(aliases=['compress'])
    async def liquidrescale(self, ctx, link: ImageConverter, width: int = 100, height: int = 100):
        '''Will resize your <link> in a weird way'''
        await ctx.polaroid('liquid_rescale', link, width, height)


    @commands.command()
    async def flip(self, ctx, link: ImageConverter, vertical: bool = False):
        '''Will flip your <link> vertically or horizontally'''
        await ctx.polaroid('flipv' if vertical else 'fliph', link)


    @flags.add_flag('--randomcolours', '--randomcolors', type=bool, default=True)
    @flags.add_flag('--backgroundcolour', '--backgroundcolor', type=Colour, default='#36393f')
    @flags.add_flag('data', nargs='+')
    @flags.command(
        aliases=['chart'],
        usage='<title> [data... (e.g "one 50 blue 20")] [--backgroundcolour=\'#36393f\'] [--randomcolours=True]',
        brief='Images/piechart'
    )
    async def piechart(self, ctx, title: str, **options):
        '''Will make a piechart on <title> with [data...]'''
        _file = await self.bot.loop.run_in_executor(
            None,
            lambda: piechart(
                title,
                options['data'],
                options['backgroundcolour'],
                options['randomcolours']
            )
        )
        await ctx.respond(image='attachment://piechart.png', files=_file)


    @commands.command(aliases=['nsfwcheck', 'detectnsfw'])
    async def nuditycheck(self, ctx, link: ImageConverter, confidence_threshold: float = 0.50):
        '''Will mark nudity in your <link> and score it based on that using AI'''
        r = await deepai(ctx, AIDataType.content_moderation, {'image': link})
        _file = draw_bounding_boxes(
            r,
            await self.bot.get_bytes(link),
            confidence_threshold,
            AIDataType.content_moderation
        )
        msg = f"NSFW Score: {r['output']['nsfw_score']:.4f}"
        await ctx.respond(msg, 'attachment://labeled.png', files=_file)


    @commands.command(aliases=['ainame', 'aidetect'])
    async def label(self, ctx, link: ImageConverter, confidence_threshold: float = 0.80):
        '''Will name things in your <link> using AI'''
        r = await deepai(ctx, AIDataType.densecap, {'image': link})
        _file = draw_bounding_boxes(
            r,
            await self.bot.get_bytes(link),
            confidence_threshold,
            AIDataType.densecap
        )
        await ctx.respond(image='attachment://labeled.png', files=_file)


    @commands.command(aliases=['predictgender', 'predictage'])
    async def demographic(self, ctx, link: ImageConverter, confidence_threshold: float = 0.35):
        '''Will predict age, gender and cultural appearance of people in your <link> using AI'''
        r = await deepai(ctx, AIDataType.demographic_recognition, {'image': link})
        _file = draw_bounding_boxes(
            r,
            await self.bot.get_bytes(link),
            confidence_threshold,
            AIDataType.demographic_recognition
        )
        await ctx.respond(image='attachment://labeled.png', files=_file)


    @commands.command(aliases=['optical_character_recognition'])
    async def ocr(self, ctx, link: ImageConverter, language: LanguageConverter = None):
        '''Will return the text found in your <link>s image'''
        language = language.alpha_3 if language else 'eng'
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.ocr.space/parse/imageurl?apikey={OCRSPACE_TOKEN}&language={language}&url={link}')).json()
        result = r['ParsedResults'][0]['ParsedText'].replace('\r\n', '\n')
        msg = '**No Text Detected**'
        if not r['IsErroredOnProcessing'] and result:
            msg = utils.escape_markdown(result)
        await ctx.respond(msg)


    @commands.command(aliases=['av', 'pfp', 'icon'])
    async def avatar(self, ctx, item: ImageConverter):
        '''Will send a enlarged <item> avatar/icon in chat'''
        await ctx.polaroid('thumbnail', item, 256, 256)


    @bot_has_permissions(embed_links=True)
    @commands.command(aliases=['rc'])
    async def randomscreen(self, ctx, amount: int = 1):
        '''Will send a random prnt.sc or imgur link'''
        for i in range(amount):
            if i % 2:
                msg = f"https://prnt.sc/{''.join((choices(string.ascii_letters, k=2)))}{randrange(1000, 10000)}"
            else:
                msg = f"https://imgur.com/{random_string(5)}"
            await ctx.send(msg)


    @commands.command(aliases=['pornhubcomment'])
    async def phcomment(self, ctx, username: str, pfp: ImageConverter, *, message: str):
        '''Will send a pornhub comment with <username> saying <message>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f"https://nekobot.xyz/api/imagegen?type=phcomment&image={pfp}&text={message}&username={username}")).json()
        await ctx.respond(image=r['message'])


    @commands.command(aliases=['youtubecomment'])
    async def ytcomment(self, ctx, username: str, pfp: ImageConverter, *, message: str):
        '''Will send a youtube comment with the <user> saying <message>'''
        msg = f"https://some-random-api.ml/canvas/youtube-comment?username={username}&comment={urllib.parse.quote_plus(message)}&avatar={pfp}"
        await ctx.respond(image=msg)


    @commands.group(invoke_without_command=True, aliases=['overlays'])
    async def overlay(self, _):
        '''Group command for adding overlays to images or vice-versa'''
        raise commands.CommandNotFound()

    @overlay.command(aliases=['fm'], brief='Images/overlay_fakemessage')
    async def fakemessage(self, ctx, avatar: ImageConverter, username: str, *, message: str):
        '''Will make a fake discord message'''
        await ctx.dagpi('image/discord', {'url': avatar, 'username': username, 'text': message, 'dark': True})

    @overlay.command(aliases=['motiv'], brief='Images/overlay_motivational')
    async def motivational(self, ctx, link: ImageConverter, top_text: str, *, bottom_text: str):
        '''Will generate a motivational speech image'''
        await ctx.dagpi('image/motiv', {'url': link, 'top_text': top_text, 'bottom_text': bottom_text})

    @overlay.command()
    async def america(self, ctx, link: ImageConverter):
        '''Will add a america overlay your <link>'''
        await ctx.dagpi('image/america', {'url': link})

    @overlay.command()
    async def communism(self, ctx, link: ImageConverter):
        '''Will add a communism overlay your <link>'''
        await ctx.dagpi('image/communism', {'url': link})

    @overlay.command()
    async def triggered(self, ctx, link: ImageConverter):
        '''Will add a triggered overlay to your <link>'''
        await ctx.dagpi('image/triggered', {'url': link})

    @overlay.command()
    async def wasted(self, ctx, link: ImageConverter):
        '''Will add a wasted overlay to your <link>'''
        await ctx.dagpi('image/wasted', {'url': link})

    @overlay.command()
    async def triangle(self, ctx, link: ImageConverter):
        '''Will triangle your <link>'''
        await ctx.dagpi('image/triangle', {'url': link})

    @overlay.command()
    async def rgb(self, ctx, link: ImageConverter):
        '''Will get an rgb graph your <link>s colours'''
        await ctx.dagpi('image/rgb', {'url': link})

    @overlay.command()
    async def fedora(self, ctx, link: ImageConverter):
        '''Will add your <link> to a fedora scene'''
        await ctx.dagpi('image/fedora', {'url': link})

    @overlay.command()
    async def wanted(self, ctx, link: ImageConverter):
        '''Will add a wanted overlay to your <link>'''
        await ctx.dagpi('image/wanted', {'url': link})

    @overlay.command()
    async def jail(self, ctx, link: ImageConverter):
        '''Will add a jail overlay to your <link>'''
        await ctx.dagpi('image/jail', {'url': link})

    @overlay.command(usage='<link> [option=gay (can be asexual, bisexual, gay, genderfluid, genderqueer, intersex, lesbian, nonbinary, progress, pan, trans)]')
    async def pride(self, ctx, link: ImageConverter, option: str = 'gay'):
        '''Will add a [option] overlay to your <link>'''
        await ctx.dagpi('image/pride', {'url': link, 'flag': option})

    @overlay.command()
    async def obama(self, ctx, link: ImageConverter):
        '''Will add your <link> to a obama scene'''
        await ctx.dagpi('image/obama', {'url': link})

    @overlay.command()
    async def summarize(self, ctx, link: ImageConverter):
        '''Will summarize the contents of your <link> using AI'''
        r = await deepai(ctx, AIDataType.neural_talk, {'image': link})
        await ctx.respond(r['output'], link)


    @commands.group(invoke_without_command=True, aliases=['effects'])
    async def effect(self, _):
        '''Group command for adding effects your image/gif'''
        raise commands.CommandNotFound()

    @effect.command(aliases=['copystyle', 'overlaystyle'])
    async def stylise(self, ctx, link1: ImageConverter, link2: ImageConverter):
        '''Will style <link1> like <link2> using AI'''
        r = await deepai(ctx, AIDataType.neural_style, {'content': link1, 'style': link2})
        await ctx.respond(image=r['output_url'])

    @effect.command(aliases=['deepdream'])
    async def dreamify(self, ctx, link: ImageConverter):
        '''Will dreamify your <link> using AI'''
        r = await deepai(ctx, AIDataType.deep_dream, {'image': link})
        await ctx.respond(image=r['output_url'])

    @effect.command(aliases=['colorize'])
    async def colourize(self, ctx, link: ImageConverter):
        '''Will colourize your black/white <link> using AI'''
        r = await deepai(ctx, AIDataType.colorize, {'image': link})
        await ctx.respond(image=r['output_url'])

    @effect.command(aliases=['superresolution', 'enhance'])
    async def sharpen(self, ctx, link: ImageConverter):
        '''Will sharpen your <link>'''
        await ctx.polaroid('sharpen', link)

    @effect.command(aliases=['lines', 'strips'])
    async def stripes(self, ctx, link: ImageConverter, amount: int = 5, vertical: bool = False):
        '''Will add [amount] [vertical] stripes to your <link>'''
        await ctx.polaroid('vertical_strips' if vertical else 'horizontal_strips', link, amount)

    @effect.command()
    async def unsharpen(self, ctx, link: ImageConverter, intensity: int = 10, treshhold: int = 10):
        '''Will unsharpen your <link>'''
        await ctx.polaroid('unsharpen', link, intensity, treshhold)

    @effect.command(aliases=['contrast'])
    async def adjustcontrast(self, ctx, link: ImageConverter, value: int = 10):
        '''Will adjust your <links> contrast'''
        await ctx.polaroid('adjust_contrast', link, value)

    @effect.command()
    async def solarize(self, ctx, link: ImageConverter):
        '''Will solarize your <link>'''
        await ctx.polaroid('solarize', link)

    @effect.command(aliases=['darken'])
    async def brighten(self, ctx, link: ImageConverter, threshold: int = 100):
        '''Will brighten/darken your <link>'''
        await ctx.polaroid('brighten', link, threshold)

    @effect.command()
    async def invert(self, ctx, link: ImageConverter):
        '''Will invert your <link>s colours'''
        await ctx.polaroid('invert', link)

    @effect.command(aliases=['gaussianblur', 'blurr'])
    async def blur(self, ctx, link: ImageConverter, radius: int = 3):
        '''Will blur your <link>'''
        await ctx.polaroid('gaussian_blur', link, radius)

    @effect.command()
    async def sobel(self, ctx, link: ImageConverter, vertical: bool = False):
        '''Will add a sobel effect to your <link>'''
        await ctx.polaroid(('sobel_vertical' if vertical else 'sobel_horizontal'), link)

    @effect.command(aliases=['edge'])
    async def edgedetect(self, ctx, link: ImageConverter, invert: bool = False):
        '''Will detect your <links> edges'''
        await ctx.polaroid('edge_one' if invert else 'edge_detection', link)

    @effect.command(aliases=['normalize'])
    async def reducenoise(self, ctx, link: ImageConverter):
        '''Will reduce noise in your <link>'''
        await ctx.polaroid('noise_reduction', link)

    @effect.command(aliases=['gray', 'bw'])
    async def grayscale(self, ctx, link: ImageConverter, invert: bool = False):
        '''Will convert your <link>s colours to black and white'''
        await ctx.polaroid('decompose_min' if invert else 'decompose_max', link)

    @effect.command(aliases=['colourboost'])
    async def boostcolour(self, ctx, link: ImageConverter):
        '''Will boost your <link>s colours'''
        await ctx.polaroid('primary', link)

    @effect.command()
    async def blurpify(self, ctx, link: ImageConverter):
        '''Will blurpify your <link>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://nekobot.xyz/api/imagegen?type=blurpify&image={link}')).json()
        await ctx.respond(image=r['message'])

    @effect.command()
    async def pixelate(self, ctx, link: ImageConverter):
        '''Will pixelate your <link>'''
        await ctx.dagpi('image/pixel', {'url': link})

    @effect.command()
    async def emboss(self, ctx, link: ImageConverter):
        '''Will emboss your <link>'''
        await ctx.polaroid('emboss', link)

    @effect.command()
    async def charcoal(self, ctx, link: ImageConverter):
        '''Will convert your <link> to a charcoal drawing'''
        await ctx.dagpi('image/charcoal', {'url': link})

    @effect.command()
    async def posterize(self, ctx, link: ImageConverter):
        '''Will posterize your <link>'''
        await ctx.dagpi('image/poster', {'url': link})

    @effect.command(aliases=['H.O.G'])
    async def hog(self, ctx, link: ImageConverter, intensity: int = 2, scale: int = 2):
        '''Will convert your <link> to a H.O.G'''
        await ctx.polaroid('hog', link, intensity, 1, 1, 1, scale, False)

    @effect.command(aliases=['paint', 'art'])
    async def oil(self, ctx, link: ImageConverter, intensity: int = 20, radius: int = 3):
        '''Will oil your <link>'''
        await ctx.polaroid('oil', link, radius, intensity)

    @effect.command()
    async def sepia(self, ctx, link: ImageConverter):
        '''Will sepia your <link>'''
        await ctx.polaroid('sepia', link)

    @effect.command()
    async def swirl(self, ctx, link: ImageConverter):
        '''Will add a swirl effect to your <link>'''
        await ctx.dagpi('image/swirl', {'url': link})

    @effect.command()
    async def rainbow(self, ctx, link: ImageConverter):
        '''Will add a rainbow effect to your <link>'''
        await ctx.dagpi('image/rainbow', {'url': link})

    @effect.command()
    async def magik(self, ctx, link: ImageConverter):
        '''Will add a magik effect to your <link>'''
        await ctx.dagpi('image/magik', {'url': link})

    @effect.command()
    async def night(self, ctx, link: ImageConverter):
        '''Will add a night effect to your <link>'''
        await ctx.dagpi('image/night', {'url': link})


    @commands.group('filter', invoke_without_command=True, aliases=['tint'])
    async def filter_(self, _):
        '''Group command for adding filters to your image/gif'''
        raise commands.CommandNotFound()

    @filter_.command()
    async def custom(self, ctx, link: ImageConverter, colour: Colour):
        '''Will add a custom tint your <link>'''
        await ctx.polaroid('tint', link, *colour.to_rgb())

    @filter_.command()
    async def dramatic(self, ctx, link: ImageConverter):
        '''Will add a dramatic filter to your <link>'''
        await ctx.polaroid('dramatic', link)

    @filter_.command()
    async def firenze(self, ctx, link: ImageConverter):
        '''Will add a firenze filter to your <link>'''
        await ctx.polaroid('firenze', link)

    @filter_.command()
    async def golden(self, ctx, link: ImageConverter):
        '''Will add a golden filter to your <link>'''
        await ctx.polaroid('golden', link)

    @filter_.command()
    async def lix(self, ctx, link: ImageConverter):
        '''Will add a lix filter to your <link>'''
        await ctx.polaroid('lix', link)

    @filter_.command()
    async def lofi(self, ctx, link: ImageConverter):
        '''Will add a lofi filter to your <link>'''
        await ctx.polaroid('lofi', link)

    @filter_.command()
    async def neue(self, ctx, link: ImageConverter):
        '''Will add a neue filter to your <link>'''
        await ctx.polaroid('neue', link)

    @filter_.command()
    async def obsidian(self, ctx, link: ImageConverter):
        '''Will add a obsidian filter to your <link>'''
        await ctx.polaroid('obsidian', link)

    @filter_.command()
    async def pastel(self, ctx, link: ImageConverter):
        '''Will add a pastel filter to your <link>'''
        await ctx.polaroid('pastel_pink', link)

    @filter_.command()
    async def ryo(self, ctx, link: ImageConverter):
        '''Will add a ryo filter to your <link>'''
        await ctx.polaroid('ryo', link)

    @filter_.command()
    async def oceanic(self, ctx, link: ImageConverter):
        '''Will add a oceanic filter to your <link>'''
        await ctx.polaroid('oceanic', link)

    @filter_.command()
    async def islands(self, ctx, link: ImageConverter):
        '''Will add a islands filter to your <link>'''
        await ctx.polaroid('islands', link)

    @filter_.command()
    async def marine(self, ctx, link: ImageConverter):
        '''Will add a marine filter to your <link>'''
        await ctx.polaroid('marine', link)

    @filter_.command()
    async def seagreen(self, ctx, link: ImageConverter):
        '''Will add a seagreen filter to your <link>'''
        await ctx.polaroid('seagreen', link)

    @filter_.command()
    async def flagblue(self, ctx, link: ImageConverter):
        '''Will add a flagblue filter to your <link>'''
        await ctx.polaroid('flagblue', link)

    @filter_.command()
    async def liquid(self, ctx, link: ImageConverter):
        '''Will add a liquid filter to your <link>'''
        await ctx.polaroid('liquid', link)

    @filter_.command()
    async def diamond(self, ctx, link: ImageConverter):
        '''Will add a diamond filter to your <link>'''
        await ctx.polaroid('diamante', link)

    @filter_.command()
    async def radio(self, ctx, link: ImageConverter):
        '''Will add a radio filter to your <link>'''
        await ctx.polaroid('radio', link)

    @filter_.command()
    async def twenties(self, ctx, link: ImageConverter):
        '''Will add a twenties filter to your <link>'''
        await ctx.polaroid('twenties', link)

    @filter_.command()
    async def mauve(self, ctx, link: ImageConverter):
        '''Will add a mauve filter to your <link>'''
        await ctx.polaroid('mauve', link)

    @filter_.command()
    async def bluechrome(self, ctx, link: ImageConverter):
        '''Will add a bluechrome filter to your <link>'''
        await ctx.polaroid('bluechrome', link)

    @filter_.command()
    async def vintage(self, ctx, link: ImageConverter):
        '''Will add a vintage filter to your <link>'''
        await ctx.polaroid('vintage', link)

    @filter_.command()
    async def purfume(self, ctx, link: ImageConverter):
        '''Will add a purfume filter to your <link>'''
        await ctx.polaroid('purfume', link)

    @filter_.command()
    async def serenity(self, ctx, link: ImageConverter):
        '''Will add a serenity filter to your <link>'''
        await ctx.polaroid('serenity', link)

    @filter_.command()
    async def gradient(self, ctx, link: ImageConverter):
        '''Will add a gradient filter to your <link>'''
        await ctx.polaroid('apply_gradient', link)

    @filter_.command(aliases=['addnoise'])
    async def noise(self, ctx, link: ImageConverter):
        '''Will add a noise filter to your <link>'''
        await ctx.polaroid('pink_noise', link)


def setup(bot):
    bot.add_cog(Images(bot))
