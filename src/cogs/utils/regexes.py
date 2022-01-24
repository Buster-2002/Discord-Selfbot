# -*- coding: utf-8 -*-
import re

TOKEN_REGEX = re.compile(r"[\w\-]{24}\.[\w\-]{6}\.[\w\-]{27}|mfa\.[\w\-_]{84}")
URL_REGEX = re.compile(r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*")
ID_REGEX = re.compile(r"([0-9]{15,21})$")
MD_URL_REGEX = re.compile(r"\[(.+)\]\(([^ ]+)(?: \"(.+)\")?\)")
TWITCH_REGEX = re.compile(r"(^http(s)?://)?((www|en-es|en-gb|secure|beta|ro|www-origin|en-ca|fr-ca|lt|zh-tw|he|id|ca|mk|lv|ma|tl|hi|ar|bg|vi|th)\.)?twitch.tv/(?!directory|p|user/legal|admin|login|signup|jobs)(?P<channel>\w+)")
TIME_REGEXES = re.compile(
    r"(?:(?P<years>[0-9])(?:years?|y|yrs?))?"
    r"(?:(?P<months>[0-9]{1,2})(?:months?|mo))?"
    r"(?:(?P<weeks>[0-9]{1,4})(?:weeks?|w|wks?))?"
    r"(?:(?P<days>[0-9]{1,5})(?:days?|d))?"
    r"(?:(?P<hours>[0-9]{1,5})(?:hours?|h|hrs?))?"
    r"(?:(?P<minutes>[0-9]{1,5})(?:minutes?|m|mins?))?"
    r"(?:(?P<seconds>[0-9]{1,5})(?:seconds?|s|secs?))?",
    re.VERBOSE | re.IGNORECASE
)
GIFT_REGEX = re.compile(
    r"(discord.com\/gifts\/|discordapp.com\/gifts\/|discord.gift\/)[ ]*([\w]{16,24})",
    re.IGNORECASE
)
PRIVNOTE_REGEX = re.compile(
    r"(privnote.com)\/([\w\#]+)",
    re.IGNORECASE
)
