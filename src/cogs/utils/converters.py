# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Tuple

from dateparser.search import search_dates
from discord.abc import Messageable
from discord.ext import commands
from pycountry import countries, currencies, languages

from .exceptions import BadTime, BadToken, BadUrl
from .regexes import TIME_REGEXES, TOKEN_REGEX, URL_REGEX


class TimeConverter(commands.Converter):
    '''Converts argument <number><unit> to time in seconds

    >>> await TimeConverter().convert(ctx, "5secs")
    5

    >>> await TimeConverter().convert(ctx, "4h")
    14400

    >>> await TimeConverter().convert(ctx, "1week")
    604800
    '''
    async def convert(self, _, argument: str) -> float:
        if match := TIME_REGEXES.fullmatch(argument):
            total = 0
            for possible_group in (intervals := {
                'seconds': 1,
                'minutes': 60,
                'hours': 3600,
                'days': 86400,
                'weeks': 86400 * 7,
                'months': 86400 * 30,
                'years': 86400 * 365
            }):
                if group := match.group(possible_group):
                    try:
                        value = float(group)
                    except ValueError:
                        raise
                    else:
                        total += intervals[possible_group] * value
            return total
        raise BadTime(f'Couldn\'t convert {argument} to a valid time/number. Use number followed by unit (e.g 5weeks, 3s or 8hrs).')


class DateConverter(commands.Converter):
    '''Extracts a time from argument

    >>> await DateConverter().convert(ctx, "In 3 hours, do the dishes")
    (' do the dishes', datetime.datetime(2021, 10, 3, 15, 22, 19, 139779))
    '''
    async def convert(self, _, argument: str) -> Tuple[str, datetime]:
        dates = search_dates(argument, ['en'])
        if not dates:
            raise BadTime('Couldn\'t find a valid time construct in your argument.')
        detected, date = dates[0]
        if datetime.now() > date:
            raise BadTime('You can\'t do something in the past.')
        return argument.replace(detected, ''), date


class ImageConverter(commands.Converter):
    '''Will return an image belonging to the argument

    >>> await ImageConverter().convert(ctx, "<@764584777642672160>") # Or other input available for User conversion
    https://cdn.discordapp.com/avatars/764584777642672160/c56af9891ee8f242fbf71d1ac2e8d047.png?size=4096

    >>> await ImageConverter().convert(ctx, https://discord.com/channels/@me/843176823880941629/896781463800922132) # Or other input available for Message conversion
    https://media.discordapp.net/attachments/764870432460374047/896112972332695642/amongus.gif

    >>> await ImageConverter().convert(ctx, "<:yes:819331558913081375>") # Or other input available for Emoji conversion
    https://cdn.discordapp.com/emojis/819331558913081375.png?size=4096

    >>> await ImageConverter().convert(ctx, 833075576348475443) # Or other input available for Guild conversion
    https://cdn.discordapp.com/icons/833075576348475443/6411f0b230fa416c9fe05cad9658bef8.png?size=4096

    >>> await ImageConverter().convert(ctx, "😂")
    https://twemoji.maxcdn.com/v/latest/72x72/1f602.png
    '''
    async def convert(self, ctx, argument: str) -> str:
        match = URL_REGEX.match(argument)
        if match:
            return match.group()

        try:
            return str((
                await commands.UserConverter().convert(ctx, argument)
            ).avatar_url_as(static_format='png'))
        except commands.UserNotFound:
            try:
                message = await commands.MessageConverter().convert(ctx, argument)
                if message.attachments:
                    return message.attachments[0].url
            except commands.MessageNotFound:
                try:
                    return str((
                        await commands.PartialEmojiConverter().convert(ctx, argument)
                    ).url_as(static_format='png'))
                except commands.PartialEmojiConversionFailure:
                    try:
                        return str((
                            await commands.GuildConverter().convert(ctx, argument)
                        ).icon_as(static_format='png'))
                    except commands.GuildNotFound:
                        try:
                            emote = argument.replace('\U0000fe0f', '')
                            uc_id = f'{ord(str(emote)):x}'
                            return f'https://twemoji.maxcdn.com/v/latest/72x72/{uc_id}.png'
                        except TypeError:
                            pass
        raise BadUrl(f'Couldn\'t convert {argument} into a URL. Provide a user/guild mention/id/name, emote or a direct URL.')


class TokenConverter(commands.Converter):
    '''Checks if the argument provided matches against a valid Discord token regex
    '''
    async def convert(self, _, argument: str) -> str:
        if match := TOKEN_REGEX.match(argument):
            return match.group()
        raise BadToken(f'{argument} is an invalid Discord token.')


class CurrencyConverter(commands.Converter):
    '''Converts any form of currency abbreviation or name to a 3 letter abbreviation

    >>> await CurrencyConverter().convert(ctx, 'euro')
    EUR
    '''
    async def convert(self, _, argument: str):
        try:
            return currencies.lookup(argument).alpha_3
        except LookupError:
            raise LookupError(f'Couldn\'t find currency {argument}. Use name (e.g us dollar) or an abbreviation (e.g usd).')


class CountryConverter(commands.Converter):
    '''Converts any form of country abbreviation or name to a pycountry Country

    >>> await CountryConverter().convert(ctx, 'Netherlands')
    Country(alpha_2='NL', alpha_3='NLD', name='Netherlands', numeric='528', official_name='Kingdom of the Netherlands')
    '''
    async def convert(self, _, argument: str):
        try:
            return countries.lookup(argument)
        except LookupError:
            raise LookupError(f'Couldn\'t find country {argument}. Use name (e.g united kingdom) or an abbrevitation (e.g gb or gbr).')


class LanguageConverter(commands.Converter):
    '''Converts any form of language abbreviation or name to a pycountry Language

    >>> await LanguageConverter().convert(ctx, 'Dutch')
    Language(alpha_2='nl', alpha_3='nld', bibliographic='dut', name='Dutch', scope='I', type='L')
    '''
    async def convert(self, _, argument: str):
        try:
            return languages.lookup(argument)
        except LookupError:
            raise LookupError(f'Couldn\'t find language {argument}. Use name (e.g turkish) or an abbreviation (e.g tr or tur).')


class MultiChannelConverter(commands.Converter):
    '''Converts <argument> to Messageable using all available channel converters
    '''
    async def convert(self, ctx, argument: str) -> Messageable:
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.ChannelNotFound:
            try:
                return (await commands.UserConverter().convert(ctx, argument)).dm_channel
            except commands.UserNotFound:
                try:
                    if channel := ctx.bot.get_channel(int(argument)):
                        return channel
                except ValueError:
                    if argument in ('c', 'current', 'this', 'here'):
                        return ctx.channel
        raise commands.ChannelNotFound(argument)
