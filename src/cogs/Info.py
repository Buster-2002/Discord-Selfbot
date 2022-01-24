# -*- coding: utf-8 -*-
import json
import platform
import sys
import time
import unicodedata
from contextlib import suppress
from datetime import datetime
from io import BytesIO
from os import getpid
from pathlib import Path
from textwrap import dedent, shorten
from typing import List, Optional, Tuple

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import psutil
from discord import (Colour, File, Guild, Invite, Member, Object, Role, Status,
                     User, UserFlags)
from discord import __version__ as dcversion
from discord import utils
from discord.ext import commands
from humanize import intcomma, naturalday, naturalsize, precisedelta
from pycountry import countries

from .utils import flags
from .utils.checks import bot_has_permissions
from .utils.converters import TokenConverter
from .utils.exceptions import DataNotFound
from .utils.helpers import default_headers, format_date
from .utils.tokens import (EDAMAM_TOKEN, OMDB_TOKEN, OPENWEATHER_TOKEN,
                           RAPIDAPI_TOKEN, WHOISXML_TOKEN)


class Info(commands.Cog):
    '''Category with all info commands. These commands return info on a specific subject.'''

    def __init__(self, bot):
        self.bot = bot


    async def _get_media_info(self, query: str, _type: str) -> Tuple[str, str, str, List[Tuple[str, str, Optional[bool]]]]:
        r = await (await self.bot.AIOHTTP_SESSION.get(f'http://www.omdbapi.com/?apikey={OMDB_TOKEN}&t={query}&type={_type}&r=json')).json()
        try:
            msg = f"{_type.capitalize()} Info | {r['Title']}"
            thumbnail = r['Poster'] if r['Poster'] != 'n/a' else None
            fields = []
            excluded = {'Awards', 'Writer', 'Ratings', 'Poster', 'Response', 'DVD', 'Plot', 'Actors', 'imdbID', 'Year', 'imdbVotes', 'Type'}

            for k, v in r.items():
                if v not in (None, '', 'N/A'):
                    if k not in excluded:
                        fields.append((k, v))

            fields.append(('Actors', r['Actors'], False))
            fields.append(('Plot', r['Plot'], False))
            return r['imdbRating'], msg, thumbnail, fields
        except KeyError:
            raise DataNotFound(f'The {_type} `{query}` couldn\'t be found.')


    @commands.command(aliases=['created_at', 'creationdate'])
    async def idinfo(self, ctx, _id: Object):
        '''Will show information about a Discord <id>'''
        date, _id = _id.created_at, _id.id
        msg = dedent(f'''
            **ID:** {_id}
            **ID Length:** {len(str(_id))}
            **Created:** {format_date(date)}
        ''')
        await ctx.respond(msg, title='ID Info')


    @commands.command(brief='Info/movieinfo')
    async def movieinfo(self, ctx, *, query: str.lower):
        '''Will return movie info and torrents by <query>'''
        imdbRating, msg, thumbnail, fields = await self._get_media_info(query, 'movie')
        with suppress(KeyError):
            # I added the imdb rating to be more sure we actually get the same movie here, still not perfect
            r = await (await self.bot.AIOHTTP_SESSION.get(f'https://yts.mx/api/v2/list_movies.json?limit=1&query_term={query}&minimum_rating={imdbRating}')).json()
            for torrent in r['data']['movies'][0]['torrents']:
                torrent_info = dedent(f'''
                    **Install:** [here]({torrent['url']})
                    **Size:** {naturalsize(torrent['size_bytes'])}
                    **Uploaded:** {format_date(datetime.fromtimestamp(torrent['date_uploaded_unix']))}
                    **Peers/Seeds:** {torrent['peers']}/{torrent['seeds']}
                ''')
                fields.append((
                    f"{torrent['type'].capitalize()} torrent - {torrent['quality']}",
                    torrent_info
                ))

        await ctx.respond(msg, thumbnail=thumbnail, fields=fields)


    @commands.command()
    async def seriesinfo(self, ctx, query: str.lower):
        '''Will return series info by <query>'''
        _, msg, thumbnail, fields = await self._get_media_info(query, 'series')
        await ctx.respond(msg, thumbnail=thumbnail, fields=fields)


    @commands.command(aliases=['pokeinfo', 'pokemon'])
    async def pokemoninfo(self, ctx, *, pokemon: str):
        '''Will show information about <pokemon>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://some-random-api.ml/pokedex?pokemon={pokemon}')).json()
        try:
            msg = f"Pokemon Info | {r['name'].capitalize()}\n{r['description']}"
            thumbnail = r['sprites']['animated']
            fields = [
                ('ID', r['id']),
                ('Type(s)', ', '.join(r.get('type', []))),
                ('Species', ', '.join(r.get('species', []))),
                ('Abilities', ', '.join(r.get('abilities', []))),
                ('Gender', ', '.join(r.get('gender', []))),
                ('Egg Groups', ', '.join(r.get('egg_groups', []))),
                ('Evolution', ' > '.join(r['family']['evolutionLine']))
            ]
            fields.append(('Stats', f"HP: {r['stats']['hp']}\nAttack: {r['stats']['attack']}\nDefense: {r['stats']['defense']}\nSpeed: {r['stats']['speed']}"))
            fields.append(('Other', f"Height: {r['height']}\nWeight: {r['weight']}\nExperience: {r['base_experience']}\nGeneration: {r['generation']}"))
            await ctx.respond(msg, thumbnail=thumbnail, fields=fields)
        except KeyError:
            raise DataNotFound(f'The pokemon `{pokemon}` couldn\'t be found.')


    @commands.command(aliases=['mcinfo'])
    async def minecraftinfo(self, ctx, *, username_or_uuid: str):
        '''Will return some information about a Minecraft account'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.snaz.in/v2/namemc/profile/{username_or_uuid}')).json()
        try:
            namehistory = '\n'.join((f"{d['username']} ({(format_date(datetime.strptime(d['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'))) if d['timestamp'] else 'original'})")
                            for d in sorted(r['username_history'], key=lambda item: item['order']))
            friends = '\n'.join((f"[{d['name']}]({d['url']})") for d in r['friends'])
            fav_servers = '\n'.join((f"[{d['domain']}]({d['url']})") for d in r['favorite_servers'])
            msg = f"Minecraftinfo | [{r['username']}]({r['url']})"
            location = f"{r['location']['emoji']} {r['location']['name']}" if r['location'] else None
            try:
                head = r['skins'][-1]['icon'].replace('scale=2', 'scale=30')
            except:
                head = None
            fields = [
                ('UUID', r['uuid']['dashed']),
                ('Location', location),
                ('Claimed', r['claimed']),
                ('Namehistory', namehistory),
                ('Friends', friends),
                ('Servers', fav_servers)
            ]
            await ctx.respond( msg, thumbnail=head, fields=fields)
        except KeyError:
            raise DataNotFound(f'The minecraft account `{username_or_uuid}` couldn\'t be found.')


    @commands.command()
    async def inviteinfo(self, ctx, invite: Invite):
        '''Will show information about the Discord <invite>'''
        msg = f"Inviteinfo | [{invite.code}]({invite.url})"
        fields = [
            ('Server', f"{invite.guild} ({invite.guild.id})"),
            ('Members', f"{invite.approximate_member_count} ({invite.approximate_presence_count} active)"),
            ('Inviter', f"{invite.inviter} ({invite.inviter.id})"),
            ('Channel', f"#{invite.channel} ({invite.channel.id})"),
            ('Revoked', invite.revoked),
            ('Expires', format_date(invite.expires_at or datetime.utcnow())),
        ]
        await ctx.respond(msg, fields=fields)


    @commands.command(aliases=['steam'])
    async def steaminfo(self, ctx, steam_id: str):
        '''Will show information about a steam account by <steam_id>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.snaz.in/v2/steam/user-profile/{steam_id}')).json()
        try:
            acc_id = r['steamid']['64']
            thumbnail = r.get('avatar')
            username = r['username']
            image = r.get('background_url')
            activity, level, created, bans, counts, state, description, real_name = None, None, None, None, '', 'private', '', ''

            if not r['private']:
                state = 'public'
                real_name = f"aka {r.get('real_name')}"
                activity = f"{r['recent_activity']['playtime']['formatted']} hours last 14 days"
                description = shorten(r['summary']['text'], 200)
                level = r['level']['formatted']
                created = format_date(r['created'])
                bans = '\n'.join(f"{k.replace('_', ' ').title()}: {(v.get('formatted') if isinstance(v, dict) else str(v).capitalize())}" for k, v in r['bans'].items())
                counts = ('```py\n' + '\n'.join(f"{(k.replace('_', ' ').title() + ':').ljust(22)} {v['formatted'] if v else 'none'}" for k, v in r['counts'].items()) + '\n```')

            msg = f"Steaminfo | [{username}](https://steamcommunity.com/profiles/{acc_id}) {real_name} ({state})\n{description}\n{counts}"
            fields = [
                ('ID', acc_id),
                ('Level', level),
                ('Played', activity),
                ('Bans', bans),
                ('Created', created)
            ]
            if r.get('status', 'offline') != 'offline':
                fields.append(('Status', f"Playing {r['status'].get('game')} ({r['status'].get('state')}) with ip being {r['status'].get('ip', 'unknown')}"))

            await ctx.respond(
                msg,
                fields=fields,
                thumbnail=thumbnail,
                image=image
            )
        except KeyError:
            raise DataNotFound(f'The steamaccount `{steam_id}` couldn\'t be found.')


    @commands.command()
    async def songinfo(self, ctx, *, song: str):
        '''Will return information about <song>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://some-random-api.ml/lyrics?title={song}')).json()
        try:
            msg = f"[**Link**]({r.get('links').get('genius')})\n{r['lyrics']}"
            await ctx.respond(msg, thumbnail=r.get('thumbnail').get('genius'))
        except KeyError:
            raise DataNotFound(f'The song `{song}` couldn\'t be found.')


    @commands.command(aliases=['covid'])
    async def covidinfo(self, ctx):
        '''Will return some data regarding the SARS-CoV-2 virus'''
        headers = {
            'x-rapidapi-key': RAPIDAPI_TOKEN,
            'x-rapidapi-host': 'covid-19-data.p.rapidapi.com'
        }
        r = await (await self.bot.AIOHTTP_SESSION.get(
            'https://covid-19-data.p.rapidapi.com/totals',
            headers=headers
        )).json()[0]
        msg = dedent(f'''
            **Confirmed:** {intcomma(r['confirmed'])}
            **Critical:** {intcomma(r['critical'])}
            **Deaths:** {intcomma(r['deaths'])}
            **Recovered:** {intcomma(r['recovered'])}
            **Last update:** {datetime.strptime(r['lastUpdate'], '%Y-%m-%dT%H:%M:%S%z').strftime('%c')}
        ''')
        await ctx.respond(msg)


    @flags.add_flag('--units', '--measurement', default='metric')
    @flags.add_flag('city', nargs='*')
    @flags.command(
        aliases=['weather'],
        usage='<city> [units=metric (can be metric, imperial or standard)]'
    )
    async def weatherinfo(self, ctx, **options):
        '''Will return weather info by <city>'''
        city, units = ' '.join(options['city']), options['units']
        if units == 'metric':
            tu = '°C'
            su = 'm/s'
        elif units == 'standard':
            tu = 'K'
            su = 'm/s'
        else:
            tu = '°F'
            su = 'mph'

        r = await (await self.bot.AIOHTTP_SESSION.get(f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_TOKEN}&lang=en&units={units}')).json()
        try:
            weather = ', '.join([d['main'] + f" ({d['description']})"
                      if d['main'] != d['description'] else '' for d in r['weather']])
            data = r['main']
            msg = f"Weather Info | {r['name']}"
            fields = [
                ('Location', f"{r['name']}, {countries.lookup(r['sys']['country']).name}"),
                ('Temperature', f"{data['temp']}{tu} (between {data['temp_min']} and {data['temp_max']}{tu})" if data['temp'] else None),
                ('Wind', f"{r['wind']['speed']} {su} from {r['wind']['deg']}°" if r['wind'] else None),
                ('Pressure', f"{data['pressure']} hPa" if data.get('pressure') else None),
                ('Humidity', f"{data['humidity']}%rH" if data.get('humidity') else None),
                ('Cloudiness', f"{r['clouds']['all']}%" if r.get('clouds') else None),
                ('Rain', ', '.join([f"{k}: {v}mm" for k, v in r['rain'].items()]) if r.get('rain') else None),
                ('Weather', weather, False)
            ]
            await ctx.respond(msg, fields=fields, thumbnail=f"http://openweathermap.org/img/wn/{r['weather'][0]['icon']}@2x.png")
        except KeyError:
            raise DataNotFound(f'The city `{city}` couldn\'t be found.')


    @commands.command(aliases=['pypi'])
    async def packageinfo(self, ctx, *, package: str):
        '''Will show information about the Python <package>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://pypi.org/pypi/{package}/json')).json()
        try:
            data = r['info']
            classifiers = lambda d, s: ''.join([c.split(d)[1].strip() for c in data['classifiers'] if c.startswith(s)])
            msg = f"Packageinfo | [{data['name']}]({data['package_url']})"
            dev_status = classifiers('-', 'Development Status')
            audience = classifiers('::', 'Intended Audience')
            OS = classifiers('::', 'Operating System')
            fields = [
                ('Author', f"[{data['author']}]({data['author_email']})"),
                ('Maintainer', f"{data['maintainer']}({data['maintainer_email']})" if data['maintainer'] else None),
                ('Version', data['version']),
                ('License', data['license']),
                ('Development status', dev_status),
                ('Audience', audience),
                ('Python', data['requires_python']),
                ('Operating system', OS),
                ('Docs', f"[here]({data['docs_url']})" if data['docs_url'] else None),
                ('Homepage', f"[here]({data['home_page']})" if data['home_page'] else None),
                ('Keywords', ', '.join(data['keywords'].split())),
                ('Summary', data['summary'])
            ]
            await ctx.respond(msg, fields=fields)
        except KeyError:
            raise DataNotFound(f'The PyPi package `{package}` couldn\'t be found.')


    @commands.command()
    async def foodinfo(self, ctx, *, dish: str):
        '''Will return some info about <dish>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.edamam.com/search?app_key={EDAMAM_TOKEN[0]}&app_id={EDAMAM_TOKEN[1]}&q={dish}')).json()
        try:
            data = r['hits'][0]['recipe']
            nl = '\n'
            msg = dedent(f'''
                [{data['label']}]({data['url']})
                **Calories:** {data['calories']:.2f}kcal
                **Labels:**
                {nl.join(data['healthLabels'] + data['dietLabels'] + data['cautions'])}
                **Ingredients:**
                {nl.join(data['ingredientLines'])}
            ''')
            await ctx.respond(msg, thumbnail=data['image'])
        except KeyError:
            raise DataNotFound(f'The dish `{dish}` couldn\'t be found.')


    @commands.command(aliases=['memory', 'pinfo'])
    async def processinfo(self, ctx):
        '''Will show some process info of your selfbot instance'''
        start = time.perf_counter()
        m = await ctx.send('`Resolving...`')
        end = time.perf_counter()
        process = psutil.Process(getpid())
        mem = process.memory_info()
        cc_amount = len(self.bot.CUSTOM_COMMANDS)
        c_amount = len(self.bot.commands) - cc_amount
        sc_amount = sum([(len(c.commands)) for c in self.bot.commands if isinstance(c, commands.Group)])
        msg = f'Processinfo | pid {process.pid}'
        fields = [
            ('Loaded', f'Commands: {c_amount}\nSubcommands: {sc_amount}\nCustomcommands: {cc_amount}\nTotal: {cc_amount + c_amount + sc_amount}\nCogs: {len(self.bot.cogs)}'),
            ('Versions', f'Selfbot: {self.bot.VERSION}\nPython: {".".join(map(str, sys.version_info[0:3]))}\ndiscord.py: {dcversion}'),
            ('Latencies', f'WS: {self.bot.latency * 1000:.2f}ms\nREST: {(end - start) * 1000:.2f}ms'),
            ('Usages', f'Phys. mem: {naturalsize(mem.rss)}\nVirt. mem: {naturalsize(mem.vms)}\nCPU: {process.cpu_percent():.2f}%\nThreads: {process.num_threads()}'),
            ('Events', f"Raw send: {intcomma(self.bot.SOCKET_STATS[100]['counter'])}\nRaw received: {intcomma(self.bot.SOCKET_STATS[101]['counter'])}"),
            ('Uptime', precisedelta(datetime.now() - self.bot.START_TIME, format='%0.0f'))
        ]
        await m.delete()
        await ctx.respond(msg, fields=fields)


    @commands.command(aliases=['pcinfo', 'sysinfo'])
    async def computerinfo(self, ctx):
        '''Will show information about the computer the bot is running on'''
        uname = platform.uname()
        cpufreq = psutil.cpu_freq()
        svmem = psutil.virtual_memory()
        swapmem = psutil.swap_memory()
        partitions = psutil.disk_partitions()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
        cpu_usages = ''

        for i, percentage in enumerate(psutil.cpu_percent(1, True), 1):
            cpu_usages += f"Core {i}: {percentage:.2f}%\n"

        total_space = total_used = total_free = 0
        for part in partitions:
            try:
                usg = psutil.disk_usage(part.mountpoint)
                total_space += usg.total
                total_used += usg.used
                total_free += usg.free
            except PermissionError:
                continue

        fields = [
            ('System Info', f'OS: {uname.system}\nNode: {uname.node}\nRelease: {uname.release}\nVersion: {uname.version}\nProcessor: {uname.processor}\nMachine: {uname.machine}'),
            ('Processor', f'Phys. cores: {psutil.cpu_count(logical=False)}\nLog. cores: {psutil.cpu_count(logical=True) - psutil.cpu_count(logical=False)}\nMax freq. {cpufreq.max:.1f}Mhz\nMin freq. {cpufreq.min:.1f}Mhz\nCurrent freq: {cpufreq.current:.1f}Mhz\n{cpu_usages}'),
            ('Disk', f'Total space: {naturalsize(total_space)}\nTotal used: {naturalsize(total_used)}\nTotal free: {naturalsize(total_free)}\nTotal read: {naturalsize(disk_io.read_bytes)}\nTotal write: {naturalsize(disk_io.write_bytes)}'),
            ('Memory', f'Total: {naturalsize(svmem.total)}\nAvailable: {naturalsize(svmem.available)}\nUsed: {naturalsize(svmem.used)}\nPercentage: {svmem.percent:.2f}%'),
            ('Swap memory', f'Total: {naturalsize(swapmem.total)}\nFree: {naturalsize(swapmem.free)}\nUsed: {naturalsize(swapmem.used)}\nPercentage: {swapmem.percent:.2f}%'),
            ('Network', f'Total sent: {naturalsize(net_io.bytes_sent)}\nTotal received: {naturalsize(net_io.bytes_recv)}')
        ]
        await ctx.respond(fields=fields)


    @commands.command(aliases=['cinfo'])
    async def channelinfo(self, ctx, server: Guild = None, send_to_log: bool = True):
        '''Will show all the channels in [server]'''
        guild = server or ctx.guild
        msg = f'Channel Info | {guild}'
        thumbnail = guild.icon_url
        categories = '\n'.join([c.name for c in guild.categories])
        text_channels = '\n'.join([c.name for c in guild.text_channels])
        voice_channels = '\n'.join([c.name for c in guild.voice_channels])
        stage_channels = '\n'.join([c.name for c in guild.stage_channels])
        fields = [
            ('Text Channels', text_channels),
            ('Voice Channels', voice_channels),
            ('Stage Channels', stage_channels),
            ('Categories', categories)
        ]
        await ctx.respond(
            msg,
            thumbnail=thumbnail,
            fields=fields,
            send_to_log=send_to_log
        )


    @commands.command(aliases=['rinfo'])
    @commands.guild_only()
    async def roleinfo(self, ctx, role: Role, send_to_log: bool = True):
        '''Will show information about the <role>'''
        colour = 'default' if role.colour == '#000000' else role.colour
        permissions = ', '.join(k.replace('_', ' ').title() for k, v in list(role.permissions) if v)
        msg = f'Role Info | {role}'
        thumbnail = role.guild.icon_url
        fields = [
            ('ID', role.id),
            ('Member Count', len(role.members)),
            ('Mentionable', role.mentionable),
            ('Hoist', role.hoist),
            ('Hierarchy', role.position),
            ('Colour', colour),
            ('Managed', role.managed),
            ('Created', format_date(role.created_at)),
            ('Permissions', permissions, False)
        ]

        if role.managed:
            tags = ', '.join(role.tags).casefold().replace('_', ' ').title()
            fields.append(('Tags', tags, False))

        await ctx.respond(
            msg,
            thumbnail=thumbnail,
            fields=fields,
            send_to_log=send_to_log
        )


    @commands.command()
    async def emailinfo(self, ctx, email: str):
        '''Will show some information about <email>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://emailverification.whoisxmlapi.com/api/v1?apiKey={WHOISXML_TOKEN}&emailAddress={email}&outputFormat=json')).json(content_type='text/plain')
        try:
            msg = f'Emailinfo | {email}'
            def f(s):
                if s == 'true':
                    return 'correct'
                return 'incorrect'
            fields = [
                ('Format check', f(r['formatCheck'])),
                ('SMPT check', f(r['smtpCheck'])),
                ('DNS check', f(r['dnsCheck'])),
                ('Free check', f(r['freeCheck'])),
                ('Disposable check', f(r['disposableCheck'])),
                ('Catch check', f(r['catchAllCheck'])),
                ('Created at', r['audit']['auditCreatedDate']),
                ('Updated at', r['audit']['auditUpdatedDate']),
                ('MX records', ', '.join(r['mxRecords']))
            ]
            await ctx.respond(msg, fields=fields)
        except KeyError:
            raise DataNotFound(f'The email `{email}` couldn\'t be found.')


    @commands.command(aliases=['guildinfo', 'sinfo'])
    async def serverinfo(self, ctx, server: Guild = None, send_to_log: bool = True):
        '''Will show information about [server]'''
        guild = server or ctx.guild
        nl = '\n'
        afk = ('AFK', guild.afk_channel.mention if guild.afk_channel else None)
        system = ('System', guild.system_channel.mention if guild.system_channel else None)
        rules = ('Rules', guild.rules_channel.mention if guild.rules_channel else None)
        updates = ('Updates', guild.public_updates_channel.mention if guild.public_updates_channel else None)
        msg = f'Server Info | {guild}'
        fields = [
            ('Region', str(guild.region).capitalize()),
            ('Locale', guild.preferred_locale),
            ('ID', guild.id),
            ('Owner', getattr(guild.owner, 'mention', guild.owner)),
            ('Members', f'{guild.member_count} ({guild.online_count} online)'),
            ('Emotes', f'{len(guild.emojis)} ({guild.emoji_limit - len(guild.emojis)} slots available)'),
            ('Boosts', guild.premium_subscription_count),
            ('Text Channels', f'{len(guild.text_channels)} (of which {len([c for c in guild.text_channels if c.permissions_for(guild.me).send_messages])} are accessible)'),
            ('Voice Channels', f'{len(guild.voice_channels)} (of which {len([c for c in guild.voice_channels if c.permissions_for(guild.me).connect])} are accessible)'),
            ('Created', format_date(guild.created_at)),
            ('Content Filter', str(guild.explicit_content_filter).replace('_', ' ').title()),
            ('Verification', f'Level: {str(guild.verification_level).capitalize()}\nMFA: {bool(guild.mfa_level)}')
        ]
        if guild.unavailable:
            msg += '\n\n**The server is currently unavailable**'
        if data := [c for c in (system, afk, rules, updates) if c[1]]:
            msg += f"\n\n**Special Channels**\n{nl.join([f'{c[0]}: {c[1]}' for c in data])}"
        if guild.features:
            msg += f"\n\n**Features**\n{', '.join(guild.features).casefold().replace('_', ' ').title()}"
        if guild.roles:
            msg += f"\n\n**Roles**\n{', '.join([r.name for r in guild.roles][1:21])}" + (f' (and **{len(guild.roles) - 20}** others)' if len(guild.roles) > 20 else '')

        await ctx.respond(
            msg,
            image=guild.banner_url or guild.splash_url,
            thumbnail=guild.icon_url,
            fields=fields,
            send_to_log=send_to_log
        )


    @commands.command(aliases=['uinfo'])
    async def userinfo(self, ctx, user: User, send_to_log: bool = True):
        '''Will show info about <user>s discord account'''
        if ctx.guild:
            user = ctx.guild.get_member(user.id)

        premium, mutual_servers, connected_accounts, note = None, None, None, None
        with suppress(Exception):
            profile = await self.bot.fetch_profile(user.id)
            if profile.mutual_guilds and user != self.bot.user:
                mutual_servers = ', '.join([g.name for g in profile.mutual_guilds])
            if profile.connected_accounts:
                connected_accounts = ', '.join([f"{d['type']}: {d['name']}" for d in profile.connected_accounts])
            if profile.premium:
                premium = f'Yes, since ~{format_date(profile.premium_since)}'
            if profile.note:
                note = profile.note

        statuses = {
            Status.offline: '⚫ offline',
            Status.dnd: '🔴 dnd',
            Status.idle: '🟠 idle',
            Status.online: '🟢 online'
        }
        _flags = ', '.join([n.replace('_', ' ').title() for n, v in list(user.public_flags) if v])

        guild_name, top_role, joined_ago, permissions, nick, activity, statuses = 'Global', None, None, None, None, None, None
        if isinstance(user, Member):
            guild_name = ctx.guild.name
            top_role = user.top_role.name
            joined_ago = format_date(user.joined_at)
            permissions = ', '.join([n.replace('_', ' ').title() for n, v in list(user.guild_permissions) if v])
            if user.display_name != user.name:
                nick = user.display_name
            if not getattr(user.activity, 'application_id', False):
                activity = user.activity
            if user in self.bot.user.friends:
                statuses = dedent(f'''
                    Mobile status: {statuses.get(user.mobile_status)}
                    Desktop status: {statuses.get(user.desktop_status)}
                    Web status: {statuses.get(user.web_status)}
                ''')

        msg = f'User Info | {guild_name}'
        fields = [
            ('Name#tag', str(user)),
            ('ID', user.id),
            ('Nickname', nick),
            ('Joined', joined_ago),
            ('Created', format_date(user.created_at)),
            ('Top role', top_role),
            ('Flags', _flags),
            ('Status/activity', activity),
            ('Nitro', premium),
            ('Mutual servers', mutual_servers),
            ('Connected accounts', connected_accounts),
            ('Note', note, False),
            ('Permissions', permissions, False),
            ('Statuses', statuses, False)
        ]

        await ctx.respond(
            msg,
            thumbnail=user.avatar_url,
            fields=fields,
            send_to_log=send_to_log
        )


    @commands.command(aliases=['dox'])
    async def tokeninfo(self, ctx, token: TokenConverter, send_to_log: bool = True):
        '''Will show information about <token>'''
        try:
            headers = default_headers(token)
            r1 = await (await self.bot.AIOHTTP_SESSION.get(f'{self.bot.API_URL}users/@me', headers=headers)).json()
            r2 = await (await self.bot.AIOHTTP_SESSION.get(f'{self.bot.API_URL}users/@me/billing/payment-sources', headers=headers)).json()
            r3 = await (await self.bot.AIOHTTP_SESSION.get(f'{self.bot.API_URL}users/@me/settings', headers=headers)).json()
            user_id = r1['id']
            if isinstance(r2, list):
                verified = True
            elif r2.get('code') == 40002:
                verified = False

        except:
            raise DataNotFound(f'The token `{token}` couldn\'t be found.')

        else:
            file = []
            premium_types = {
                1: 'Nitro Classic',
                2: 'Nitro'
            }
            thumbnail = f"https://cdn.discordapp.com/avatars/{user_id}/{r1['avatar']}"
            flags = UserFlags(r1['flags']).name.replace('_', ' ').title() if r1['flags'] in [e.value for e in UserFlags] else None
            msg = f"Tokeninfo | {r1['username']}#{r1['discriminator']}"
            fields = [
                ('ID', r1['id']),
                ('Created', format_date(utils.snowflake_time(int(user_id)))),
                ('Token', token),
                ('Email', r1['email']),
                ('Phone', r1['phone']),
                ('Locale', r1['locale']),
                ('Flags', flags),
                ('MFA', r1['mfa_enabled']),
                ('Verified', r1['verified']),
                ('Premium', premium_types.get(r1.get('premium_type'), 'N/A'))
            ]

            if verified:
                # Extract payment methods
                paymentmethods = []
                excluded = {'id', 'type', 'country', 'default'}
                for payment_source in r2:
                    for k, v in payment_source.items():
                        print(k)
                        if k not in excluded:
                            if isinstance(v, dict):
                                for sk, sv in v.items():
                                    paymentmethods.append(f'{sk}: {sv}')
                            else:
                                paymentmethods.append(f'{k}: {v}')

                    paymentmethods.append('\n')

                fields.append(('Payment methods', '\n'.join(paymentmethods), False))

                # Formatted json settings file
                formatted_json = json.dumps(
                    r3, 
                    indent=4, 
                    sort_keys=True
                )
                file = await ctx.textfile(
                    formatted_json, 
                    'settings.json', 
                    send=False, 
                    clean=False
                )

            await ctx.respond(
                msg,
                thumbnail=thumbnail,
                fields=fields,
                send_to_log=send_to_log,
                files=file
            )


    @commands.command()
    async def charinfo(self, ctx, *, message: str):
        '''Will show info about chars in your <message>'''
        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Not Found')
            return f'`\\U{digit:>08}` ({c}): [{name}](http://www.fileformat.info/info/unicode/char/{digit})'

        msg = '\n'.join(map(to_string, message))
        await ctx.respond(msg)


    @commands.command(aliases=['colorinfo', 'color', 'colour'], usage='[colour=random (can be RGB, HEX, or a name like magenta)]')
    async def colourinfo(self, ctx, colour: Colour = None):
        '''Will show information about your hex/rgb [colour]'''
        colour = colour or Colour.random()
        rgb = ','.join(map(str, colour.to_rgb()))
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://www.thecolorapi.com/id?rgb={rgb}')).json()
        msg = f"Colour Info | {r['name']['value']}"
        fields = [
            ('HEX', r['hex']['value']),
            ('RGB', r['rgb']['value']),
            ('HSL', r['hsl']['value']),
            ('HSV', r['hsv']['value']),
            ('CMYK', r['cmyk']['value']),
            ('XYZ', r['XYZ']['value']),
            ('Decimal', str(colour.value))
        ]
        image = f"https://singlecolorimage.com/get/{r['hex']['clean']}/400x400"
        await ctx.respond(msg, thumbnail=image, fields=fields)


    @commands.command(aliases=['emotes'])
    async def emojiinfo(self, ctx, server: Guild = None, send_to_log: bool = True):
        '''Will list all the emotes in [server]'''
        guild = server or ctx.guild
        emotes = '\n'.join([(f'{e.name}: {e}') for e in (guild.emojis if guild.emojis else await guild.fetch_emojis())])
        await ctx.respond(emotes, send_to_log=send_to_log)


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['metrics'], usage='[amount_commands=10 (amount of commands to graph)]')
    async def usageinfo(self, ctx, amount_commands: int = 10):
        '''Will show usage data and metricy'''
        with open(Path('data/json/metrics.json'), encoding='utf-8') as f:
            data = json.load(f)

        nl = '\n'
        # This actually fails when the first thing someone does upon launching the selfbot
        # is using this command, but I find that an incredibly rare edge case so not gonna bother
        total_send = sum(self.bot.MESSAGE_COUNT.values())
        top_used = list(sorted(self.bot.MESSAGE_COUNT.items(), key=lambda item: item[1]))[-1]
        most_popular = str(self.bot.get_guild(top_used[0]) or self.bot.get_channel(top_used[0]))
        percentage = (top_used[1] / total_send) * 100

        msg = f'''
**Command Usage**
In total you have invoked **{intcomma(sum(list(data.values())))}** commands, **{intcomma(self.bot.COMMANDS_USED + 1)}** were invoked in this session alone.

**Discord Usage**
Since **{self.bot.START_TIME.strftime('%H:%M:%S')} {naturalday(self.bot.START_TIME)}** you have send **{intcomma(total_send)}** messages, of which **{percentage:.2f}%** were send in **{most_popular}**.

**Socket Stats**
```py
SOCKET NAME                    AMOUNT
{nl.join([(f"{(e['name'] + ' ').ljust(30, '.')} {intcomma(e['counter'])}") for e in self.bot.SOCKET_STATS.values()])}
```
        '''
        fig, ax = plt.subplots(facecolor='#36393f')
        ax.set_facecolor('#4f535c')
        x, y = zip(*list(sorted(data.items(), key=lambda x: x[1], reverse=True))[:amount_commands])
        ax.bar(x, y, align='center', color='w')
        ax.tick_params(labelcolor='w')
        ax.set_xlabel(
            'Command Name',
            fontsize=15,
            color='w'
        )
        ax.set_ylabel(
            'Times Used',
            fontsize=15,
            color='w'
        )
        ax.set_title(
            f'Top {amount_commands} Most Used Commands',
            fontsize=24,
            color='w'
        ).set_path_effects([
            path_effects.Stroke(linewidth=2, foreground='black'),
            path_effects.Normal()
        ])
        fig.autofmt_xdate()
        plt.tight_layout()

        fp = BytesIO()
        plt.savefig(fp, format='png')
        plt.close()
        fp.seek(0)
        _file = File(fp, 'metrics.png')
        await ctx.respond(msg, 'attachment://metrics.png', files=_file)


def setup(bot):
    bot.add_cog(Info(bot))
