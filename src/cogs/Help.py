# -*- coding: utf-8 -*-
import asyncio
from contextlib import suppress
from textwrap import dedent, shorten
from typing import List, Mapping, Optional

from discord import utils
from discord.ext import commands


class HelpCommand(commands.HelpCommand):
    '''Subclass of HelpCommand.'''

    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Sends help for categories, group commands and commands',
            'hidden': True
        })


    @property
    def _prefix(self) -> str:
        '''Returns the already mention transformed prefix with escaped markdown'''
        return utils.escape_markdown(self.clean_prefix)


    async def _send_message(self, title: str, description: str, image: str = None):
        '''Makes sure that when user invokes another help command, the original one is edited and the auto delete time is reset'''
        ctx, content = self.context, None
        embed = ctx.bot.default_embed(
            title=title,
            description=description,
            url='https://geazersb.github.io',
        )
        embed.set_thumbnail(url=ctx.bot.ICON)
        embed.set_image(url=f'https://geazersb.github.io/help_gifs/{image}.gif' if image else f'https://singlecolorimage.com/get/{str(embed.colour)[1:]}/400x4')

        me = ctx.guild.me if ctx.guild else ctx.bot.user
        if not ctx.channel.permissions_for(me).embed_links and ctx.guild:
            content = f"```\n{utils.remove_markdown(embed.description)}\n```"

        try:
            await ctx.bot.HELP_MESSAGE.edit(embed=embed, content=content)
            ctx.bot.HELP_TASK.cancel()
        except:
            ctx.bot.HELP_MESSAGE = await ctx.send(embed=embed, content=content)

        ctx.bot.HELP_TASK = asyncio.ensure_future(
            asyncio.sleep(
                30,
                loop=ctx.bot.loop
            )
        )

        with suppress(Exception):
            await ctx.bot.HELP_TASK
            await ctx.bot.HELP_MESSAGE.delete()
            ctx.bot.HELP_MESSAGE = None


    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]):
        '''This function triggers with <prefix>help'''
        title = 'Geazer Selfbot | Help'
        formatted = '\n'.join(sorted([(
            f'**{cog.qualified_name}** \u279F {len(cog_commands)} commands and {sum([(len(group.commands)) for group in cog_commands if isinstance(group, commands.Group)])} subcommands')
            for cog, cog_commands in filter(lambda i: i[0], mapping.items()) if cog.qualified_name not in {'Help', 'Events'}
        ]))
        msg = dedent(f'''
            *Use {self._prefix}help [category] to see its available commands*

            {formatted}
        ''').strip()
        await self._send_message(title, msg)


    async def send_cog_help(self, cog: commands.Cog):
        '''This function triggers with <prefix>help <cog>'''
        title = f'Geazer Selfbot | Help > {cog.qualified_name}'
        formatted = '\n'.join(sorted([
            shorten(
                f"**{self._prefix}{c.qualified_name}** \u279F Group command" 
                if isinstance(c, commands.Group) else f"**{self._prefix}{c.qualified_name}** \u279F {c.help}",
                50,
                placeholder='...'
            ) for c in cog.get_commands() if not c.hidden
        ], key=len, reverse=True))
        msg = dedent(f'''
            *Use {self._prefix}help [command] for more info on a command or commandgroup*

            {formatted}
        ''').strip()
        await self._send_message(title, msg)


    async def send_group_help(self, group: commands.Group):
        '''This function triggers with <prefix>help <group>'''
        title = f'Geazer Selfbot | Help > {group.cog_name} > {group.qualified_name}'
        aliases = ', '.join(group.aliases) or 'This group doesn\'t have any aliases.'
        usage = group.usage or group.signature.replace('_', '') or 'This group doesn\'t take any arguments.'
        formatted = '\n'.join(sorted([(
            f"**{self._prefix}{c.qualified_name}** \u279F {c.help}")
            for c in group.commands
        ]))
        msg = dedent(f'''
            *Use {self._prefix}help [command] [subcommand] for more info on a subcommand*

            **{self._prefix}{group.qualified_name}** \u279F {group.help}

            **Usage:** {usage}
            **Aliases:** {aliases}

            {formatted}
        ''').strip()
        await self._send_message(title, msg, group.brief)


    async def send_command_help(self, command: commands.Command):
        '''This function triggers with <prefix>help <command>'''
        ctx = self.context
        await command.can_run(ctx) # Ensures locally added variables with decorators are propagated to this stateless help class
        title = f'Geazer Selfbot | Help > {command.cog_name} > {f"{command.parent} > " if command.parent else ""}{command.name}'
        aliases = ', '.join(command.aliases) or 'This command doesn\'t have any aliases.'
        usage = command.usage or command.signature.replace('_', '') or 'This command doesn\'t take any arguments.'
        perms = ', '.join(command.required_perms) if getattr(command, 'required_perms', False) else 'This command doesn\'t need any special perms.'
        msg = dedent(f'''
            *Arguments in between <> are required, arguments in between [] have a default value*

            **{self._prefix}{command.qualified_name}** \u279F {command.help}

            **Usage:** {usage}
            **Aliases:** {aliases}
            **Required perms:** {perms}
        ''').strip()
        await self._send_message(title, msg, command.brief)


class Help(commands.Cog):
    '''Shows available categories, or shows help to the user for specific commands, groups or cogs.'''
    def __init__(self, bot):
        self.bot = bot
        self.bot.help_command = HelpCommand()
        self.bot.help_command.cog = self


def setup(bot):
    bot.add_cog(Help(bot))
