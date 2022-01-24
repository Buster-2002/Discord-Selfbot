# -*- coding: utf-8 -*-
import json
import re
import traceback
from contextlib import redirect_stdout, suppress
from datetime import datetime
from difflib import get_close_matches
from io import StringIO
from pathlib import Path
from textwrap import dedent, indent
from typing import Optional, Tuple, Union

from discord import (GroupChannel, Guild, HTTPException, Member,
                     RelationshipAction, RelationshipType, TextChannel, User,
                     VoiceChannel, utils)
from discord.ext import commands
from humanize import intcomma, naturaldelta, naturaltime, ordinal, precisedelta

from .utils import flags
from .utils.checks import bot_has_permissions
from .utils.converters import (CountryConverter, LanguageConverter,
                               MultiChannelConverter)
from .utils.enums import ServerLogType
from .utils.exceptions import (CommandDoesntExist, CommandExists, DataNotFound,
                               NotEnabled)
from .utils.regexes import TWITCH_REGEX
from .utils.sherlock import Sherlock


class Other(commands.Cog):
    '''Category with all commands that couldn't be placed in a distinct category.'''

    def __init__(self, bot):
        self.bot = bot


    @staticmethod
    async def _serverlogs(ctx, log_type: ServerLogType, amount: int, guild: Guild) -> None:
        if not 0 < amount < 1501:
            amount = 100

        if not ctx.bot.GUILDLOG:
            raise NotEnabled('Serverlogging is not enabled! Enable it with the generalsettings command.')

        deletes_or_edits = getattr(ctx.bot, f'GUILD_{str(log_type).upper()}_LOG')
        if guild:
            data = list(filter(lambda d: d['guild_id'] == guild.id, list(deletes_or_edits)))[:amount]
            fn = f'{len(data)}_guild_{log_type}s_{guild}.log'
        else:
            data = list(deletes_or_edits)[:amount]
            fn = f'{len(data)}_guild_{log_type}s_global.log'

        if not data:
            raise DataNotFound(f"There are no recorded deleted messages {f'in `{guild}`' if guild else ''}.")

        formatted = [f"Deleted by: {d['author_name']} | Server: {d['guild_name']} | Channel: #{d['channel_name']} | Deleted: ~{naturaltime(d['created_at'])}\n{'-' * 150}\n" + d['clean_content'] if log_type == 'delete' else f"{d['clean_content_before']}\n| To\n{d['clean_content_after']}"
                    for d in data]
        await ctx.textfile('\n\n\n'.join(formatted), fn)


    @staticmethod
    async def _scrape_files(ctx, channel: TextChannel, limit: int, file_extensions: Tuple[str]) -> int:
        scraped = 0
        async for m in channel.history(before=ctx.message, limit=limit):
            if m.attachments:
                for f in m.attachments:
                    if f.filename.endswith(file_extensions):
                        await f.save(Path(f'data/scrapedfiles/{f.filename}'))
                        scraped += 1

        return scraped


    @staticmethod
    def _format_code(content: str) -> str:
        if content.startswith('```') and content.endswith('```'):
            content = '\n'.join(content.split('\n')[1:-1])
        return f"async def func():\n{indent(content, ' ' * 4)}"


    @commands.command(
        'eval',
        aliases=['run', 'evaluate'],
        brief='Other/eval'
    )
    async def _eval(self, ctx, *, body: str):
        '''Will evaluate python code'''
        if ctx.message.attachments:
            return

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message
        }

        env.update(globals())
        to_compile = self._format_code(body)
        stdout = StringIO()

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.respond(f'```py\n{type(e).__name__}: {e}\n```'.replace(self.bot.TOKEN, '[REDACTED]'), send_to_log=True)
        func = env['func']
        try:
            value = stdout.getvalue()
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.respond(f'```py\n{value}{traceback.format_exc()}\n```'.replace(self.bot.TOKEN, '[REDACTED]'), send_to_log=True)
        else:
            value = stdout.getvalue()
            if ret is None:
                if value:
                    await ctx.respond(f'```py\n{value}\n```'.replace(self.bot.TOKEN, '[REDACTED]'))


    @commands.command(aliases=['guildfriends', 'friendsin'])
    async def serverfriends(self, ctx, server: Guild = None):
        '''Will show your friends in [server]'''
        await self.bot.log(f'Getting friends in {server}... (this may take a while)')
        friends = []
        guild = server or ctx.guild
        for f in self.bot.user.friends:
            profile = await self.bot.fetch_profile(f.id, fetch_note=False)
            if guild in profile.mutual_guilds:
                friends.append(str(f))

        msg = f"Friends in {server} are {', '.join(friends)}"
        await ctx.respond(msg)


    @commands.command(aliases=['streamerearnings'], usage='<streamer (twitch link or name)>')
    async def twitchpayouts(self, ctx, streamer: str.lower):
        '''Will show gross earning of <streamer> from Twitch'''
        if match := re.match(TWITCH_REGEX, streamer):
            streamer = match.group('channel')
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://twitchpayouts.com/api/payouts')).json()
        try:
            data = [d for d in r['default'] if d['username'].lower() == streamer][0]
            msg = dedent(f'''
                **Streamer:** [{data['username']}](https://twitch.tv/{data['username']})
                **Rank:** {ordinal(data['rank'])}/{r['length']}
                **ID:** {data['user_id']}
                **Gross payout:** {intcomma(data['gross_earning'])}$
            ''')
            await ctx.respond(msg, thumbnail=data['pfp'])
        except KeyError:
            raise DataNotFound(f'The streamer `{streamer}` couldn\'t be found.')


    @commands.command(aliases=['fm'])
    async def firstmessage(self, ctx, channel: MultiChannelConverter = None):
        '''Will link to the first message send in [channel]'''
        channel = channel or ctx.channel
        async for m in await channel.history(limit=1, oldest_first=True):
            await ctx.send(m.jump_url)


    @commands.command(aliases=['countwords', 'timesused'])
    async def wordusage(self, ctx, channel: MultiChannelConverter = None, most_common: Optional[int] = None, *words):
        '''Will show how many times [words...] have been used in <channel> or show <most_common>'''
        channel = channel or ctx.channel
        if data := self.bot.WORD_COUNTER[channel.id]:
            if not most_common and not words:
                most_common = 10
            if most_common and not words:
                data = data.most_common(most_common)
                msg = f'Top {len(dict(data))} most commonly used words in {channel} are:'
            else:
                data = sorted([(k, v) for k, v in dict(filter(lambda item: item[0] in words, dict(data).items())).items()], key=lambda item: item[1], reverse=True)
                if data:
                    msg = f"{', '.join(words)} ranked by usage:"
                else:
                    raise DataNotFound(f"Couldn\'t find any of {', '.join(words)} used in {channel}.")
            top = '\n'.join([f"{i}. {w[0]} ({intcomma(w[1])}x)" for i, w in enumerate(data, 1)])
            await ctx.respond(f'{msg}\n\n{top}')
        else:
            raise DataNotFound(f'Couldn\'t find any words logged in {channel}.')


    @commands.command(aliases=['sherlock', 'searchusername'])
    async def searchaccounts(self, ctx, workers: Optional[int] = 20, *, username: Union[User, str]):
        '''Will check if <username> exists on a multitude of social media platforms'''
        if isinstance(username, User):
            username = username.name
        await self.bot.log(f'Checking username {username}... (this may take a while)')
        results = await self.bot.loop.run_in_executor(
            None,
            lambda: Sherlock(username, workers).start()
        )
        data, meta = results['data'], results['meta']
        nl = '\n'
        msg = f'''
CHECKED {meta['websites_checked']} WEBSITES IN {precisedelta(meta['time_elapsed']).upper()}


USERNAME HAS BEEN REGISTERED ON THE FOLLOWING PLATFORMS:
{nl.join(data['claimed'])}


USERNAME HAS NOT YET BEEN CLAIMED ON THE FOLLOWING PLATFORMS:
{nl.join(data['available'])}


USERNAME STATUS UNKNOWN ON THE FOLLOWING PLATFORMS:
{nl.join(data['unknown'])}
        '''
        await ctx.textfile(msg, 'search_results.txt', clean=False)


    @bot_has_permissions(move_members=True)
    @commands.command(aliases=['moveto', 'multimove'])
    async def move(self, _, voice_channels: commands.Greedy[VoiceChannel], *members: Member):
        '''Will move [members...] to [voice_channels]...'''
        moved = 0
        for vc in voice_channels:
            with suppress(HTTPException):
                for m in members:
                    await m.move_to(vc)
                    moved += 1

        await self.bot.log(f'Moved member(s) {moved} times')


    @commands.command(aliases=['declinefriendrequests'])
    async def declineall(self, _):
        '''Will decline all incoming friend requests'''
        declined = 0
        for fr in self.bot.user.relationships:
            if fr.type == RelationshipType.incoming_request:
                declined += 1
                await fr.delete()

        await self.bot.log(f'Declined {declined} incoming friend requests')


    @commands.command(aliases=['leavegroups'])
    async def leaveall(self, _, *exclusions: int):
        '''Will leave all groupchannels excluding [exclusions...]'''
        left = 0
        for gc in self.bot.private_channels:
            if isinstance(gc, GroupChannel) and gc.id not in exclusions:
                left += 1
                await gc.leave()

        await self.bot.log(f'Left {left} group chats')


    @commands.command(aliases=['readmessages'])
    async def readall(self, _):
        '''Will mark all messages in all servers as read'''
        for g in self.bot.guilds:
            await g.ack()


    @commands.command(aliases=['genperson'])
    async def fakeperson(self, ctx, sex: str.lower = 'male', language: LanguageConverter = None, country: CountryConverter = None):
        '''Will generate a random [sex] from [country]'''
        country = country.name.replace(' ', '-').lower() if country else 'random'
        language = language.name.lower() if language else 'random'
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.namefake.com/{language}-{country}/{sex}')).json(content_type=None)
        msg = f"Fake Person | [{sex.capitalize()} living in {country}]({r['url']})"
        age = naturaldelta(datetime.utcnow() - datetime.strptime(r['birth_data'], '%Y-%m-%d'))
        fields = [
            ('Name', f"{r['name']} (maiden name {r['maiden_name']})"),
            ('Address', r['address']),
            ('Born/age', f"{r['birth_data']} / {age} old"),
            ('Phone', r['phone_w']),
            ('Email URL', f"[Link](https:{r['email_url']}.com/)"),
            ('Username / Password', f"{r['username']} / {utils.escape_markdown(r['password'])}"),
            ('IPv4/Mac', f"{r['ipv4']} / {r['macaddress']}"),
            ('CC/CCexp', f"{r['plasticcard']} / {r['cardexpir']}"),
            ('Company', r['company']),
            ('Hair/Eye/Blood', f"{r['hair']} / {r['eye']} / {r['blood']}"),
            ('Height/Weight', f"{r['height']}cm / {r['weight']}kg"),
            ('Fav Sport/Colour', f"{r['sport']} / {r['color']}")
        ]
        await ctx.respond(msg, fields=fields)


    @commands.command(aliases=['copyavatars', 'scrapeavatars'])
    async def getavatars(self, ctx, server: Guild = None):
        '''Will scrape all avatars in a guild for the random avatars list'''
        guild = server or ctx.guild
        await guild.subscribe()
        avatars, amount = [], 0
        for m in guild.members:
            if not m.is_guild_avatar_animated():
                avatars.append(str(m.avatar_url))
                amount += 1

        with open(Path('data/assets/text/avatars.txt'), 'a', encoding='utf-8') as f:
            f.write(avatars)

        await self.bot.log(f'Scraped {amount} avatars from {guild}')


    @commands.command(aliases=['copyemotes', 'scrapeemojis'], brief='Other/getemojis')
    async def stealemotes(self, _, fromserver: Guild, toserver: Guild, *_filter: str):
        '''Will scrape emojis from <fromserver> and add them to <toserver>'''
        copied = 0
        await self.bot.log(f'Copying emotes from {fromserver} to {toserver}')
        emotes = fromserver.emojis
        if not emotes:
            emotes = await fromserver.fetch_emojis()

        for n, e in [
            (e.name, await e.url.read())
            for e in emotes if e.is_usable()
            and (e.name in _filter if _filter else True)
        ]:
            await toserver.create_custom_emoji(name=n, image=e)
            copied += 1

        await self.bot.log(f'Finished copying {copied} emotes from {fromserver} to {toserver}')


    @commands.command(aliases=['copyfiles', 'scrapefiles'], usage='[limit=10] [server (leave empty to scrape from just current channel)] [filetypes=png,mp4,gif,jpg,mp3]')
    async def getfiles(self, ctx, limit: Optional[int] = 10, server: Optional[Guild] = None, *filetypes: str):
        '''Will scan [limit] messages for files with [filetypes...] and save them'''
        filetypes = filetypes or ('png', 'mp4', 'gif', 'jpg', 'mp3')
        if server:
            scraped = 0
            for tc in server.text_channels:
                scraped += await self._scrape_files(ctx, tc, limit, filetypes)
        else:
            scraped = await self._scrape_files(ctx, ctx.channel, limit, filetypes)
        await self.bot.log(f'Finished scraping {scraped} files')


    @commands.group(invoke_without_command=True, aliases=['customcommand'])
    async def cc(self, _):
        '''Group command for adding/removing/listing custom commands'''
        raise commands.CommandNotFound()

    @flags.add_flag('--deleteafter', '--autodelete', type=int, default=None)
    @flags.add_flag('--embedded', '--embed', type=bool, default=False)
    @flags.add_flag('content', nargs='+')
    @cc.command(
        'add',
        aliases=['make', 'create', 'update'],
        cls=flags.FlagCommand,
        usage='<command_name> <content> [--deleteafter=None] [--embedded=False]',
        brief='Other/cc_add'
    )
    async def cc_add(self, ctx, command_name: str.lower, **options):
        '''Will add the custom command named <command_name> sending <content>'''
        self.bot.ExistingCommandsList = [x for c in self.bot.walk_commands() for x in (c.name, ' '.join(c.aliases)) if x]
        if command_name in self.bot.ExistingCommandsList:
            raise CommandExists(command_name)

        content = ' '.join(options['content'])
        delete_after = options['deleteafter']
        embedded = options['embedded']
        with open(Path('data/json/customcommands.json'), encoding='utf-8') as f:
            data = json.load(f)

        with open(Path('data/json/customcommands.json'), 'w', encoding='utf-8') as f:
            self.bot.CUSTOM_COMMANDS[command_name] = data[command_name] = {
                'content': content,
                'delete_after': delete_after,
                'embedded': embedded,
                'aliases': []
            }
            json.dump(data, f, indent=4)

        @self.bot.command(command_name, hidden=True)
        async def _(ctx, content=content, delete_after=delete_after, embedded=embedded):
            if embedded:
                await ctx.respond(content)
            else:
                await ctx.send(content, delete_after=delete_after)

        await ctx.respond(f"Added custom command `{command_name}`", title='CC Add')

    @cc.command('remove', aliases=['delete'])
    async def cc_remove(self, ctx, command_name: str.lower):
        '''Will remove the custom command named <command_name> '''
        if command_name not in self.bot.CUSTOM_COMMANDS.keys():
            raise CommandDoesntExist(command_name)

        self.bot.remove_command(command_name)
        self.bot.CUSTOM_COMMANDS.pop(command_name)

        with open(Path('data/json/customcommands.json')) as f:
            data = json.load(f)

        with open(Path('data/json/customcommands.json'), 'w', encoding='utf-8') as f:
            data.pop(command_name)
            await ctx.respond(f'Custom command `{command_name}` removed', title='CC Remove')
            json.dump(data, f, indent=4)

    @cc.command('list')
    async def cc_list(self, ctx):
        '''Will show all your custom commands'''
        msg = f"{len(self.bot.CUSTOM_COMMANDS)} customcommands(s)\n\n{', '.join(self.bot.CUSTOM_COMMANDS.keys())}"
        await ctx.respond(msg, title='CC List')

    @cc.command('info')
    async def cc_info(self, ctx, *, query: str.lower):
        '''Will show info about a custom command by <query>'''
        if closest := get_close_matches(query, self.bot.CUSTOM_COMMANDS.keys(), 1, 0.2):
            name = closest[0]
            command = self.bot.CUSTOM_COMMANDS[name]
            msg = f'CC Info | {name}'
            with open(Path('data/json/metrics.json'), encoding='utf-8') as f:
                data = json.load(f)
                times_used = data.get(name, 0)
            fields = [
                ('Content length', len(command['content'])),
                ('Delete after', precisedelta(command['delete_after'], format='%0.0f') or 'never'),
                ('Embedded', 'yes' if command['embedded'] else 'no'),
                ('Aliases', ', '.join(command['aliases']) or 'none'),
                ('Times used', times_used)
            ]
            await ctx.respond(msg, fields=fields, title='CC Info')
        else:
            raise CommandDoesntExist(query)


    @commands.group(
        invoke_without_command=True,
        aliases=['serverlog', 'guildlogs', 'guildlog'],
        brief='Other/serverlogs'
    )
    async def serverlogs(self, _):
        '''Group command for sending edited/deleted messages from servers in files'''
        raise commands.CommandNotFound()

    @bot_has_permissions(attach_files=True)
    @serverlogs.command('edits', aliases=['edited', 'edit'])
    async def serverlogs_edits(self, ctx, amount: int = 100, server: Guild = None):
        '''Will send the latest [amount=10] (max 1500) edited messages from [server] (or global)'''
        await self._serverlogs(ctx, ServerLogType.edit, amount, server)

    @bot_has_permissions(attach_files=True)
    @serverlogs.command('deletes', aliases=['deleted', 'delete'])
    async def serverlogs_deletes(self, ctx, amount: int = 100, server: Guild = None):
        '''Will send the latest [amount=10] (max 1500) deleted messages from [server] (or global)'''
        await self._serverlogs(ctx, ServerLogType.delete, amount, server)


    @commands.group(invoke_without_command=True)
    async def backup(self, _):
        '''Group command for making/loading backups'''
        raise commands.CommandNotFound()

    @backup.group('make', aliases=['create', 'add'], invoke_without_command=True)
    async def backup_make(self, _):
        '''Sub-Group command for backing up friends, blocked users, settings and joined servers'''
        raise commands.CommandNotFound()

    @backup_make.command('friends')
    async def backup_make_friends(self, _):
        '''Will backup friends'''
        await self.bot.log('Creating friends backup...')
        friended = [str(u.id) for u in self.bot.user.friends]
        await self.bot.log('Done backing up friends')
        with open(Path('data/backups/friends.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(friended))

    @backup_make.command('blocked')
    async def backup_make_blocked(self, _):
        '''Will backup blocked users'''
        await self.bot.log('Creating blocked users backup...')
        blocked = [str(u.id) for u in self.bot.user.blocked]
        await self.bot.log('Done backing up blocked users')
        with open(Path('data/backups/blocks.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(blocked))

    @backup_make.command('servers', aliases=['guilds'])
    async def backup_make_servers(self, _):
        '''Will backup joined servers'''
        await self.bot.log('Creating servers backup... (this may take a while)')
        with open(Path('data/backups/guilds.txt'), 'w', encoding='utf-8') as f:
            f.seek(0)
            f.truncate(0)

        codes = []
        for g in self.bot.guilds:
            with suppress(Exception):
                for tc in g.text_channels:
                    if tc.permissions_for(g.me).create_instant_invite:
                        invite = await g.system_channel.create_invite(unique=False)
                        codes.append(invite.code)
                        break

        with open(Path('data/backups/guilds.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(codes))

        await self.bot.log('Done backing up servers')

    @backup_make.command('settings')
    async def backup_make_settings(self, _):
        '''Will backup your Discord settings'''
        with open(Path('data/backups/settings.json'), 'w', encoding='utf-8') as f:
            json.dump(self.bot.user.settings.raw, f, indent=4)

        await self.bot.log('Done backing up settings')

    @backup.group('load', aliases=['use'], invoke_without_command=True)
    async def backup_load(self, _):
        '''Sub-Group command for adding backed up friends, blocking blocked users and joining servers'''
        raise commands.CommandNotFound()

    @backup_load.command('friends')
    async def backup_load_friends(self, _):
        '''Will add previously backed up friends'''
        await self.bot.log('Adding friends from backup... (this may take a while)', 'info')
        with open(Path('data/backups/friends.txt'), encoding='utf-8') as f:
            ids = f.readlines()

        already_friended = [str(u.id) for u in self.bot.user.friends]
        for user_id in ids:
            if user_id in already_friended:
                continue

            await self.bot.http.add_relationship(
                user_id,
                type=RelationshipType.outgoing_request.value,
                action=RelationshipAction.send_friend_request
            )

        await self.bot.log('Done adding friends')

    @backup_load.command('blocked')
    async def backup_load_blocked(self, _):
        '''Will block previously backed up users'''
        await self.bot.log('Blocking users from backup... (this may take a while)', 'info')
        with open(Path('data/backups/blocks.txt'), encoding='utf-8') as f:
            ids = f.readlines()

        already_blocked = [str(u.id) for u in self.bot.user.blocked]
        for user_id in ids:
            if user_id in already_blocked:
                continue

            await self.bot.http.add_relationship(
                user_id,
                type=RelationshipType.blocked.value,
                action=RelationshipAction.block
            )

        await self.bot.log('Done blocking users')

    @backup_load.command('servers')
    async def backup_load_servers(self, _):
        '''Will join previously backed up servers'''
        await self.bot.log('Joining servers from backup... (this may take a while)', 'info')
        with open(Path('data/backups/guilds.txt'), encoding='utf-8') as f:
            codes = f.readlines()

        for code in codes:
            with suppress(Exception):
                await self.bot.join_guild(f'discord.gg/{code}')

        await self.bot.log('Done joining servers')

    @backup_load.command('settings')
    async def backup_load_settings(self, ctx):
        '''Will load previously backed up Discord settings'''
        await self.bot.log('Changing settings from backup...', 'info')
        with open(Path('data/backups/settings.json'), encoding='utf-8') as f:
            settings = json.load(f)

        await self.bot.user.edit_settings(**settings)

def setup(bot):
    bot.add_cog(Other(bot))
