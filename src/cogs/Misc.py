# -*- coding: utf-8 -*-
import asyncio
import os
import sys
from contextlib import suppress
from pathlib import Path
from typing import Union

import psutil
from discord import Colour
from discord.ext import commands

from .utils.checks import bot_has_permissions
from .utils.converters import ImageConverter, TimeConverter
from .utils.exceptions import InvalidExtension
from .utils.helpers import change_config


class Misc(commands.Cog):
    '''Category with all miscellaneous commands. These are usually commands that are meta to the selfbot itself.'''

    def __init__(self, bot):
        self.bot = bot

        self._command_loop_enabled = bool()
        self._cog_map = {
            'nsfw': 'cogs.NSFW',
            'moderation': 'cogs.Moderation',
            'games': 'cogs.Games'
        }


    @commands.command(aliases=['quit'])
    async def logout(self, _):
        '''Will log out the selfbot'''
        await self.bot.log('Logging out selfbot...')
        await self.bot.close()


    @commands.command(aliases=['changelog'])
    async def motd(self, ctx):
        '''Will send a message regarding the selfbot, e.g the changelog'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://pastebin.com/raw/vHirtXxn')).text()
        await ctx.respond(r)


    @commands.command()
    async def allcommands(self, ctx):
        '''Will upload all the commands of the selfbot as txt file'''
        msg = 'TAKEN FROM https://geazersb.github.io/commands.txt\n\n'
        msg += await (await self.bot.AIOHTTP_SESSION.get('https://geazersb.github.io/commands.txt')).text()
        await ctx.textfile(msg, 'commands.txt', clean=False)


    @commands.command(aliases=['link'])
    async def website(self, ctx):
        '''Will link to the Geazer Selfbot website'''
        await ctx.send('https://geazersb.github.io')


    @bot_has_permissions(attach_files=True)
    @commands.command(aliases=['senderrorfile'])
    async def senderrorlog(self, ctx):
        '''Will send the error.log file, useful for debugging'''
        with open(Path('data/logs/error.log'), encoding='utf-8') as f:
            content = f.read()
        await ctx.textfile(content, 'error.log', clean=False)


    @commands.command(aliases=['removealllisteners', 'cancelcommands'])
    async def stoplisteners(self, _):
        '''Will stop all running listeners, like annoy, autodeafen etc'''
        non_default = [
            (n, f) for n, f in
            [(k, sv) for k, v in self.bot.extra_events.items() for sv in v]
            if f not in [f for _, f in self.bot.DEFAULT_LISTENERS]
        ]
        deleted = 0
        for n, f in non_default:
            self.bot.remove_listener(f, name=n)
            deleted += 1
        await self.bot.log(f'Removed {deleted} listener(s)')


    @commands.command(aliases=['reboot'])
    async def restart(self, _):
        '''Will restart the selfbot'''
        await self.bot.log('Rebooting selfbot...')
        with suppress(Exception):
            p = psutil.Process(os.getpid())
            for handler in p.open_files() + p.connections():
                os.close(handler.fd)

        e = sys.executable
        os.execl(e, e, *sys.argv)


    @commands.command(aliases=['reloadcogs', 'refresh'])
    async def reload(self, _):
        '''Will reload all the cogs'''
        reloaded = 0
        for cog in list(self.bot.cogs.values()):
            self.bot.reload_extension(cog.__module__)
            reloaded += 1

        await self.bot.log(f'Reloaded {reloaded} cogs')


    @commands.command(aliases=['currentsettings', 'listsets', 'currentsets'])
    async def listsettings(self, ctx):
        '''Will show your current selfbot settings'''
        enabled, disabled = [], []
        items = [
            ('Guild Log', self.bot.GUILDLOG),
            ('DM Log', self.bot.DMLOG_state),
            ('Keyword Log', self.bot.KEYWORDLOG_state),
            ('Nitro Sniping', self.bot.SNIPING_nitro_state),
            ('Privnote Sniping', self.bot.SNIPING_privnote_state),
            ('Giveaway Sniping', self.bot.SNIPING_giveaway_state),
            ('Token Sniping', self.bot.SNIPING_token_state),
            ('RPC', self.bot.RPC_state),
            ('Embeds', self.bot.EMBED_state),
            ('Errorinfo', self.bot.ERRORINFO),
            ('Notifications', self.bot.NOTIFICATIONS_state),
            ('Moderation extension', self.bot.EXTENSIONS_moderation),
            ('Games extension', self.bot.EXTENSIONS_games),
            ('NSFW extension', self.bot.EXTENSIONS_nsfw)
        ]
        for n, s in items:
            (enabled if s else disabled).append(n)
        fields = [
            ('Logging to', f'{self.bot.LOG_GUILD} \u279F {self.bot.LOG_CHANNEL.mention}'),
            ('Prefix(es)', ', '.join(self.bot.PREFIXES)),
            ('\u200b', '\u200b'),
            ('Enabled', '\n'.join(enabled)),
            ('Disabled', '\n'.join(disabled)),
            ('\u200b', '\u200b')
        ]
        await ctx.respond(fields=fields)


    @commands.group(invoke_without_command=True, aliases=['dmlogsets'])
    async def dmlogsettings(self, _):
        '''Group command for changing the dmlogs settings'''
        raise commands.CommandNotFound()

    @dmlogsettings.command('enabled', usage='<enabled (yes/no)>', aliases=['toggle'])
    async def dmlogsettings_enabled(self, _, enabled: bool):
        '''Will enable/disable dmlog'''
        self.bot.DMLOG_state = change_config(('DMLOG', 'state'), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} dmlog")

    @dmlogsettings.command('webhook', aliases=['webhookurl'])
    async def dmlogsettings_webhook(self, _, webhook_url: str):
        '''Will change the webhook the dmlogs are send over, to <webhook_url>'''
        self.bot.DMLOG_webhook_url = change_config(('DMLOG', 'webhook_url'), webhook_url)
        await self.bot.log(f'Changed dmlogs webhookurl to {webhook_url}')


    @commands.group(invoke_without_command=True, aliases=['keywordlogsets'])
    async def keywordlogsettings(self, _):
        '''Group command for changing the keywordlog settings'''
        raise commands.CommandNotFound()

    @keywordlogsettings.command('enabled', usage='<enabled (yes/no)>', aliases=['toggle'])
    async def keywordlogsettings_enabled(self, _, enabled: bool):
        '''Will enable/disable keywordlog'''
        self.bot.KEYWORDLOG_state = change_config(('KEYWORDLOG', 'state'), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} keywordlog")

    @keywordlogsettings.command('webhook', aliases=['webhookurl'])
    async def keywordlogsettings_webhook(self, _, webhook_url: str):
        '''Will change the webhook the keywordlogs are send over, to <webhook_url>'''
        self.bot.KEYWORDLOG_webhook_url = change_config(('KEYWORDLOG', 'webhook_url'), webhook_url)
        await self.bot.log(f'Changed keywordlogs webhookurl to {webhook_url}')

    @keywordlogsettings.command('keywords', aliases=['words'])
    async def keywordlogsettings_keywords(self, _, *keywords: str):
        '''Will change your current keywords for the keywordlog to [keywords..]'''
        keywords = list(map(str.strip, keywords))
        self.bot.KEYWORDLOG_keywords = change_config(('KEYWORDLOG', 'keywords'), set(keywords))
        await self.bot.log(f"Changed keywordlogs keywords to {', '.join(keywords)}")


    @commands.group(invoke_without_command=True, aliases=['snipingsets'])
    async def snipingsettings(self, _):
        '''Group command for enabling/disabling sniping categories'''
        raise commands.CommandNotFound()

    @snipingsettings.command('nitro', usage='<enabled (yes/no)>')
    async def snipingsettings_nitro(self, _, enabled: bool):
        '''Will enable/disable nitro sniping'''
        self.bot.SNIPING_nitro_state = change_config(('SNIPING', 'nitro', 'state'), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} nitro sniping")

    @snipingsettings.command('privnote', usage='<enabled (yes/no)>')
    async def snipingsettings_privnote(self, _, enabled: bool):
        '''Will enable/disable privnote sniping'''
        self.bot.SNIPING_privnote_state = change_config(('SNIPING', 'privnote', 'state'), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} privnote sniping")

    @snipingsettings.command('giveaway', usage='<enabled (yes/no)>')
    async def snipingsettings_giveaway(self, _, enabled: bool):
        '''Will enable/disable giveaway sniping'''
        self.bot.SNIPING_giveaway_state = change_config(('SNIPING', 'giveaway', 'state'), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} giveaway sniping")

    @snipingsettings.command('token', usage='<enabled (yes/no)>')
    async def snipingsettings_token(self, _, enabled: bool):
        '''Will enable/disable Discord token sniping'''
        self.bot.SNIPING_token_state = change_config(('SNIPING', 'token', 'state'), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} token sniping")


    @commands.group(
        invoke_without_command=True,
        aliases=['embedsets', 'changeembed'],
        brief='Misc/embedsettings'
    )
    async def embedsettings(self, _):
        '''Group command for changing your custom embed settings'''
        raise commands.CommandNotFound()

    @embedsettings.command('enabled', usage='<enabled (yes/no)>', aliases=['toggle'])
    async def embedsettings_enabled(self, _, enabled: bool):
        '''Will enable/disable sending command output through your embed'''
        self.bot.EMBED_state = change_config(('EMBED', 'state'), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} embeds")

    @embedsettings.command('colour', usage='<colour> (a valid name, or hex code)')
    async def embedsettings_colour(self, _, colour: Union[Colour, str]):
        '''Will change your embed colour to <colour>'''
        self.bot.EMBED_colour = change_config(('EMBED', 'colour'), str(colour))
        await self.bot.log(f'Changed embed colour to {colour}')

    @embedsettings.command('footertext', aliases=['footer_text'])
    async def embedsettings_footertext(self, _, *, message: str):
        '''Will change your embeds footertext to <message>'''
        self.bot.EMBED_footer_text = change_config(('EMBED', 'footer_text'), message)
        await self.bot.log(f'Changed embed footertext to {message}')

    @embedsettings.command('footericon', aliases=['footer_icon', 'footerimage', 'footer_image'])
    async def embedsettings_footericon(self, _, link: ImageConverter):
        '''Will change your embeds footericon to <link>'''
        self.bot.EMBED_footer_icon = change_config(('EMBED', 'footer_icon'), link)
        await self.bot.log(f'Changed embed footericon to {link}')

    @embedsettings.command('autodelete', aliases=['deleteafter'])
    async def embedsettings_autodelete(self, _, delay: TimeConverter):
        '''Will change your embeds autodelete delay to <delay>'''
        self.bot.EMBED_autodelete = change_config(('EMBED', 'autodelete'), delay)
        await self.bot.log(f'Changed embed autodelete delay to {delay}s')

    @embedsettings.command('showspeed', aliases=['processingspeed'], usage='<enabled (yes/no)>')
    async def embedsettings_showspeed(self, _, enabled: bool):
        '''Will enable/disable adding a processing time to your embed'''
        self.bot.EMBED_showspeed = change_config(('EMBED', 'showspeed'), enabled)
        await self.bot.log(f"{'Enabled' if enabled else 'Disabled'} showing processing time in embeds")


    @commands.group(invoke_without_command=True, aliases=['protectionsets', 'pset'])
    async def protectionsettings(self, _):
        '''Group command for changing your protection settings'''
        raise commands.CommandNotFound()

    @protectionsettings.command('warnforadmin', aliases=['staff'], usage='<enabled (yes/no)>')
    async def protectionsettings_warnforadmin(self, _, enabled: bool):
        '''Will enable/disable warning for Discord staff'''
        self.bot.PROTECTIONS_warn_for_admin = change_config(('PROTECTIONS', 'warn_for_admin'), enabled)
        await self.bot.log(f"{'Enabled' if enabled else 'Disabled'} warning for Discord staff protection")

    @protectionsettings.command('ping', usage='<enabled (yes/no)>')
    async def protectionsettings_ping(self, _, enabled: bool):
        '''Will enable/disable the anti ping spam protection'''
        self.bot.PROTECTIONS_anti_spam_ping_state = change_config(('PROTECTIONS', 'anti_spam_ping', 'state'), enabled)
        await self.bot.log(f"{'Enabled' if enabled else 'Disabled'} anti ping spam protection")

    @protectionsettings.command('groupchat', usage='<enabled (yes/no)>')
    async def protectionsettings_groupchat(self, _, enabled: bool):
        '''Will enable/disable the anti groupchat spam protection'''
        self.bot.PROTECTIONS_anti_spam_groupchat_state = change_config(('PROTECTIONS', 'anti_spam_groupchat', 'state'), enabled)
        await self.bot.log(f"{'Enabled' if enabled else 'Disabled'} anti groupchat spam protection")

    @protectionsettings.command('friend', aliases=['friendrequest'], usage='<enabled (yes/no)>')
    async def protectionsettings_friend(self, _, enabled: bool):
        '''Will enable/disable the anti friend request spam protection'''
        self.bot.PROTECTIONS_anti_spam_friend_state = change_config(('PROTECTIONS', 'anti_spam_friend', 'state'), enabled)
        await self.bot.log(f"{'Enabled' if enabled else 'Disabled'} anti friend request spam protection")

    @protectionsettings.command('dm', usage='<enabled (yes/no)>')
    async def protectionsettings_dm(self, _, enabled: bool):
        '''Will enable/disable the anti dm spam protection'''
        self.bot.PROTECTIONS_anti_spam_dm_state = change_config(('PROTECTIONS', 'anti_spam_dm', 'state'), enabled)
        await self.bot.log(f"{'Enabled' if enabled else 'Disabled'} anti dm spam protection")


    @commands.group(invoke_without_command=True, aliases=['changerpc', 'rpcsets'])
    async def rpcsettings(self, _):
        '''Group command for changing your custom RPC settings'''

    @rpcsettings.command('enabled', aliases=['toggle'], usage='<enabled (yes/no)>')
    async def rpcsettings_enabled(self, _, enabled: bool):
        '''Will enable/disable custom Rich Presence (RPC)'''
        self.bot.RPC_state = change_config(('RPC', 'state'), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} RPC")

    @rpcsettings.command('clientid')
    async def rpcsettings_clientid(self, _, clientid: int):
        '''Will change your RPC clientid to <clientid>'''
        self.bot.RPC_clientid = change_config(('RPC', 'clientid'), clientid)
        await self.bot.log(f'Changed RPC clientid to {clientid}')

    @rpcsettings.command('name')
    async def rpcsettings_name(self, _, name: str):
        '''Will change your RPC name to <name>'''
        self.bot.RPC_name = change_config(('RPC', 'name'), name)
        await self.bot.log(f'Changed RPC name to {name}')

    @rpcsettings.command('details')
    async def rpcsettings_details(self, _, details: str):
        '''Will change your RPC details to <details>'''
        self.bot.RPC_details = change_config(('RPC', 'details'), details)
        await self.bot.log(f'Changed RPC details to {details}')

    @rpcsettings.command('large_text')
    async def rpcsettings_large_text(self, _, large_text: str):
        '''Will change your RPC large text to <large_text>'''
        self.bot.RPC_large_text = change_config(('RPC', 'large_text'), large_text)
        await self.bot.log(f'Changed RPC large text to {large_text}')

    @rpcsettings.command('small_text')
    async def rpcsettings_small_text(self, _, small_text: str):
        '''Will change your RPC small text to <small_text>'''
        self.bot.RPC_small_text = change_config(('RPC', 'small_text'), small_text)
        await self.bot.log(f'Changed RPC small text to {small_text}')

    @rpcsettings.command('large_image')
    async def rpcsettings_large_image(self, _, name: str):
        '''Will change your RPC large image to <name>'''
        self.bot.RPC_large_image = change_config(('RPC', 'large_image'), name)
        await self.bot.log(f'Changed RPC large image to {name}')

    @rpcsettings.command('small_image')
    async def rpcsettings_small_image(self, _, name: str):
        '''Will change your RPC small image to <name>'''
        self.bot.RPC_small_image = change_config(('RPC', 'small_image'), name)
        await self.bot.log(f'Changed RPC small image to {name}')


    @commands.group(invoke_without_command=True, aliases=['extensionsets', 'extension'])
    async def extensionsettings(self, _):
        '''Group command for enabling/disabling extensions'''
        raise commands.CommandNotFound()

    @extensionsettings.command('load', usage='<name> (either nsfw, moderation, games or all)')
    async def extensionsettings_load(self, _, name: str.lower):
        '''Will load the extension named <name>'''
        with suppress(commands.ExtensionAlreadyLoaded):
            if name == 'all':
                for name, fn in self._cog_map.items():
                    self.bot.load_extension(fn)
                    change_config(('EXTENSIONS', fn), True)

                await self.bot.log('Loaded and enabled all the extensions')

            else:
                if name not in self._cog_map.keys():
                    raise InvalidExtension(name)
                else:
                    _cog = self._cog_map.get(name)
                    self.bot.load_extension(_cog)
                    change_config(('EXTENSIONS', name), True)
                    await self.bot.log(f'Loaded and enabled the {name} extension')

    @extensionsettings.command('unload', usage='<name> (either nsfw, moderation, games or all)')
    async def extensionsettings_unload(self, _, name: str.lower):
        '''Will unload the extension named <name>'''
        with suppress(commands.ExtensionAlreadyLoaded):
            if name == 'all':
                for _, fn in self._cog_map.items():
                    self.bot.unload_extension(fn)
                    change_config(('EXTENSIONS', fn), False)

                await self.bot.log('Unloaded and disabled all the extensions')
                
            else:
                if name not in self._cog_map.keys():
                    raise InvalidExtension(name)
                else:
                    _cog = self._cog_map.get(name)
                    self.bot.unload_extension(_cog)
                    change_config(('EXTENSIONS', name), False)
                    await self.bot.log(f'Unloaded the {name} extension')


    @commands.group(invoke_without_command=True, aliases=['generalsets'])
    async def generalsettings(self, _):
        '''Group command for changing general selfbot settings'''
        raise commands.CommandNotFound()

    @generalsettings.command('errorinfo', usage='<enabled (yes/no)>')
    async def generalsettings_errorinfo(self, _, enabled: bool):
        '''Will enable/disable sending some error info in current channel'''
        self.bot.ERRORINFO = change_config(('ERRORINFO',), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} error info")

    @generalsettings.command('prefix', aliases=['prefixes'])
    async def generalsettings_prefix(self, _, *prefixes: str):
        '''Will change your current prefixes to [prefixes..]'''
        self.bot.command_prefix = self.bot.PREFIXES = change_config(('PREFIXES',), prefixes)
        await self.bot.log(f"Changed prefixes to {', '.join(prefixes)}")

    @generalsettings.command('guildlog', usage='<enabled (yes/no)>', aliases=['serverlog'])
    async def generalsettings_guildlog(self, _, enabled: bool):
        '''Will enable/disable logging deleted/edited messages for the serverlogs command'''
        self.bot.GUILDLOG = change_config(('GUILDLOG',), enabled)
        await self.bot.log(f"Turned {'on' if enabled else 'off'} guildlogs")


    @commands.group(
        invoke_without_command=True,
        aliases=['loopcommand'],
        brief='Misc/commandloop'
    )
    async def commandloop(self, _):
        '''Group command for starting/stopping a commandloop'''
        raise commands.CommandNotFound()

    @commandloop.command('start')
    async def commandloop_start(self, ctx, interval: TimeConverter):
        '''Will loop the next-used command every <interval> untill stopped'''
        try:
            await ctx.log(f'Next command used in {ctx.channel}, will be reinvoked every {interval}s', 'info')
            reply = await self.bot.wait_for(
                'message',
                timeout=30,
                check=lambda m: (
                    m.author == ctx.author
                    and m.channel == ctx.channel
                    and m.content.startswith(self.bot.PREFIXES)
                )
            )
        except asyncio.TimeoutError:
            pass
        else:
            new_ctx = await self.bot.get_context(reply)
            self._command_loop_enabled = True
            await self.bot.log(f'Using `{new_ctx.command.qualified_name}` in {ctx.channel} every {interval}s')
            while self._command_loop_enabled:
                await asyncio.sleep(interval)
                await new_ctx.reinvoke()

    @commandloop.command('stop')
    async def commandloop_stop(self, _):
        '''Will stop the command loop'''
        self._command_loop_enabled = False
        await self.bot.log('Stopped the commandloop')

def setup(bot):
    bot.add_cog(Misc(bot))
