# -*- coding: utf-8 -*-
from discord.ext import commands

from .utils.exceptions import DataNotFound


# not willing to find some faggy porn api so just using same shit as reddit command lmao
class NSFW(commands.Cog):
    '''Extension category with all NSFW related commands.'''

    def __init__(self, bot):
        self.bot = bot


    @staticmethod
    async def _why_on_discord(ctx, amount: int, thing: str) -> None:
        r = await (await ctx.bot.AIOHTTP_SESSION.get(f'https://meme-api.herokuapp.com/gimme/{thing}/{amount}')).json()
        for d in r['memes']:
            await ctx.respond(image=d['url'])


    @commands.group(invoke_without_command=True)
    async def hentai(self, _):
        '''Group command for listing hentai options and sending hentai images'''
        raise commands.CommandNotFound()

    @hentai.command('search', aliases=['send', 'category'])
    async def hentai_search(self, ctx, category: str, amount: int = 1):
        '''Will send [amount] hentai images by <category>'''
        for _ in range(amount):
            try:
                r = await (await self.bot.AIOHTTP_SESSION.get(f'https://nekos.life/api/v2/img/{category}')).json()
                await ctx.respond(image=r['url'])
            except KeyError:
                raise DataNotFound(f'The hentai category `{category}` couldn\'t be found')

    @hentai.command('list', aliases=['options'])
    async def hentai_list(self, ctx):
        '''Will list all possible hentai commands'''
        await ctx.respond(', '.join(('feet', 'yuri', 'trap', 'futanari', 'hololewd', 'lewdkemo', 'solog', 'feetg', 'cum', 'erokemo', 'les', 'wallpaper', 'lewdk', 'ngif',  'tickle', 'lewd', 'feed', 'gecg', 'eroyuri', 'eron', 'cum_jpg', 'bj', 'nsfw_neko_gif', 'solo', 'goose', 'kemonomimi', 'nsfw_avatar', 'gasm', 'poke', 'anal', 'slap', 'hentai', 'avatar', 'erofeet', 'holo', 'keta', 'blowjob', 'pussy', 'tits', 'holoero', 'lizard', 'pussy_jpg', 'pwankg', 'classic', 'kuni', 'waifu', 'pat', 'kiss', 'femdom', 'baka', 'neko', 'spank', 'cuddle', 'erok', 'fox_girl', 'boobs', 'random_hentai_gif', 'smallboobs', 'hug', 'ero', 'smug', 'woof')))


    @commands.group(invoke_without_command=True)
    async def porn(self, _):
        '''Group command for sending porn images'''
        raise commands.CommandNotFound()

    @porn.command('ass')
    async def porn_ass(self, ctx, amount: int = 1):
        '''Will send a random ass image/gif'''
        await self._why_on_discord(ctx, amount, 'ass')

    @porn.command('tits')
    async def porn_tits(self, ctx, amount: int = 1):
        '''Will send a random tits image/gif'''
        await self._why_on_discord(ctx, amount, 'ass')

    @porn.command('pussy')
    async def porn_pussy(self, ctx, amount: int = 1):
        '''Will send a random pussy image/gif'''
        await self._why_on_discord(ctx, amount, 'pussy')

    @porn.command('gif')
    async def porn_gif(self, ctx, amount: int = 1):
        '''Will send a random porn gif'''
        await self._why_on_discord(ctx, amount, 'porngif')

    @porn.command('petite')
    async def porn_petite(self, ctx, amount: int = 1):
        '''Will send a random petite image/gif'''
        await self._why_on_discord(ctx, amount, 'PetiteGoneWild')

    @porn.command('blowjob', aliases=['bj'])
    async def porn_blowjob(self, ctx, amount: int = 1):
        '''Will send a random blowjob image/gif'''
        await self._why_on_discord(ctx, amount, 'blowjobs')


def setup(bot):
    bot.add_cog(NSFW(bot))
