# -*- coding: utf-8 -*-
import asyncio
import base64
import json
import random
from pathlib import Path
from textwrap import dedent

from colorama import Fore
from discord import LoginFailure
from discord.ext import commands

from .utils.converters import TokenConverter
from .utils.exceptions import DataNotFound
from main import CustomBot


class Raid(commands.Cog):
    '''Category with all raid related commands. The commands you can use with logged in accounts are found in the RaidCommands category.'''

    def __init__(self, bot):
        self.bot = bot

        self._raid_instances = dict()


    @commands.group(invoke_without_command=True, aliases=['token'])
    async def account(self, _):
        '''Group command for logging in/out and listing/adding/removing accounts'''
        raise commands.CommandNotFound()

    @account.command('login')
    async def account_login(self, _, bot_accounts: bool = False):
        '''Will log in all the user accounts from usertokens.json, they will also join your logging guild'''
        with open(Path('data/json/usertokens.json'), encoding='utf-8') as f:
            accounts = json.load(f)

        if not accounts:
            raise DataNotFound('There are no tokens to log in. Add them to your list by using the `account login` command.')

        invite = await self.bot.LOG_GUILD.system_channel.create_invite(unique=False)
        self._raid_instances, immune, count, loop = {}, [self.bot.user.id], 0, asyncio.get_event_loop()
        await self.bot.log(f"Logging in all {'user' if not bot_accounts else 'bot'} accounts...")

        for botid, token in accounts.items():
            count += 1
            raiduser = self.bot.get_user(int(botid))
            print(f'{Fore.CYAN} [r] {raiduser}: Logging in..')
            immune.append(getattr(raiduser, 'id', None))

            self._raid_instances[botid] = CustomBot(
                loop=loop,
                command_prefix=self.bot.RAID_PREFIXES,
                owner_id=self.bot.user.id
            )

            subbot = self._raid_instances[botid]
            subbot.RANDOM_NUMBER = random.randrange(5, 121)
            subbot.IMMUNE = immune
            subbot.TOKEN = token
            subbot.PASSWORD = self.bot.PASSWORD
            subbot.LOGGING_GUILD = self.bot.LOGGING_GUILD
            subbot.load_extension('cogs.RaidCommands')

            try:
                loop.create_task(subbot.start(token, bot=bot_accounts))
                await subbot.join_guild(invite)
            except LoginFailure:
                print(f'{Fore.RED} [r] Couldn\'t log in {raiduser}: improper token')
                self._raid_instances.pop(botid)
                count -= 1
                continue

        await self.bot.log(f'Logged in {count} accounts')

    @account.command('logout')
    async def account_logout(self, _):
        '''Will log out all the user instances'''
        await self.bot.log('Logging out all accounts...', 'info')
        count = 0
        try:
            for botid, botinstance in self._raid_instances.items():
                raiduser = self.bot.get_user(int(botid))
                print(f"{Fore.CYAN} [r] {raiduser}: Logging out..")
                await botinstance.logout()
                count += 1
            await self.bot.log(f'Logged out {count} accounts')
        except AttributeError:
            await self.bot.log('There are no logged in accounts to logout!', 'error')

    @account.command('add')
    async def account_add(self, _, *tokens: TokenConverter):
        '''Will add tokens to the list of useraccounts that can be used to log in'''
        with open(Path('data/json/usertokens.json'), encoding='utf-8') as f:
            data = json.load(f)

        with open(Path('data/json/usertokens.json'), 'w', encoding='utf-8') as f:
            for t in tokens:
                try:
                    _id = str(base64.b64decode(str(t.split('.')[0])).decode('utf-8'))
                    data.update({_id: t})
                except base64.binascii.Error:
                    await self.bot.log('Invalid token', 'error')
                    continue

            await self.bot.log(f'Added {len(tokens)} token(s)')

    @account.command('remove', aliases=['delete'])
    async def account_remove(self, _, *ids: str):
        '''Will remove a id:token entry from the token list by [ids...]'''
        with open(Path('data/json/usertokens.json'), encoding='utf-8') as f:
            data = json.load(f)

        with open(Path('data/json/usertokens.json'), 'w', encoding='utf-8') as f:
            removed = 0
            for _id in ids:
                deleted = data.pop(_id)
                if deleted:
                    removed += 1

            json.dump(data, f, indent=4)
            await self.bot.log(f'Removed {removed} id:token combinations from user tokens list')

    @account.command('amount', aliases=['count', 'list'])
    async def account_list(self, _):
        '''Will give the amount of id:token combinations'''
        with open(Path('data/json/usertokens.json'), encoding='utf-8') as f:
            count = len(json.load(f))
        await self.bot.log(f'There are {count} id:token combinations stored in the usertokens file', 'info')

    @account.command('help')
    async def account_help(self, ctx):
        '''Will show help for raid commands, usable by logged in accounts'''
        msg = dedent(f'''
            These commands can be triggered by using `r{ctx.prefix}` in a channel where your logged in accounts can see it.

            **Take note** that some commands (suffixed _id) take only IDs instead of the usual mention/name converter, in order to be stateless.

            Errors and other information are logged to the console.
            ```
            report ➟ <message_link> <reason (see normal report command for usage)>
            channeloutage ➟ <server> [amount=10]
            say ➟ <channel> <message>
            dm ➟ <user> <message>
            fr ➟ <user>
            username ➟ [username=random]
            avatar ➟ [user=random]
            nickname ➟ <server> [nickname=random]
            spam ➟ <channel> [amount=5] <message>
            guild
                join ➟ <invite> [delayed=False]
                leave ➟ <guild_id>
            blank ➟ [channel]
                guild ➟ <guild_id>
                stop ➟ No args
            annoy
                user ➟ <user_id> [emojis...]
                guild ➟ <guild_id> [emojis...]
                stop ➟ No args
            raidserver
                start ➟ <guild> [message=pings]
                stop ➟ No args
            activity
                streaming ➟ <stream_url> <message>
                playing ➟ <message>
                listening ➟ <message>
                watching ➟ <message>
                competing ➟ <message>
            presence
                idle ➟ No args
                dnd ➟ No args
                online ➟ No args
                offline ➟ No args
            voicechannel
                join ➟ <voicechannel>
                leave ➟ No args
            ```
        ''')
        await ctx.respond(msg)


def setup(bot):
    bot.add_cog(Raid(bot))
