# -*- coding: utf-8 -*-
import base64
import json
import math
import os
import re
import sys
import time
import uuid
from pathlib import Path
from textwrap import indent, wrap

from colorama import Fore, Style, init

from .regexes import ID_REGEX, TOKEN_REGEX, URL_REGEX

init(autoreset=True)

WHITE = Fore.WHITE
RED = Fore.RED
GREEN = Fore.GREEN
CYAN = Fore.CYAN
MAGENTA = Fore.MAGENTA
BRIGHT = Style.BRIGHT
DIM = Style.DIM
FIRST_TIME = False
DEFAULT = {
    'DISCORD_TOKEN': 'PLACEHOLDER',
    'LOGGING_GUILD': 'PLACEHOLDER',
    'PASSWORD': 'PLACEHOLDER',
    'PREFIXES': [
        'PLACEHOLDER'
    ],
    'ERRORINFO': 'PLACEHOLDER',
    'GUILDLOG': 'PLACEHOLDER',
    'SNIPING': {
        'nitro': {
            'state': 'PLACEHOLDER',
            'exclusions': []
        },
        'privnote': {
            'state': 'PLACEHOLDER',
            'exclusions': []
        },
        'token': {
            'state': 'PLACEHOLDER',
            'exclusions': []
        },
        'giveaway': {
            'state': 'PLACEHOLDER',
            'exclusions': []
        }
    },
    'EMBED': {
        'state': 'PLACEHOLDER',
        'showspeed': 'PLACEHOLDER',
        'colour': 'PLACEHOLDER',
        'footer_text': 'PLACEHOLDER',
        'footer_icon': 'PLACEHOLDER',
        'autodelete': 'PLACEHOLDER'
    },
    'DMLOG': {
        'state': 'PLACEHOLDER',
        'webhook_url': 'PLACEHOLDER'
    },
    'KEYWORDLOG': {
        'state': 'PLACEHOLDER',
        'webhook_url': 'PLACEHOLDER',
        'keywords': []
    },
    'RPC': {
        'state': 'PLACEHOLDER',
        'clientid': 'PLACEHOLDER',
        'name': 'PLACEHOLDER',
        'details': 'PLACEHOLDER',
        'large_text': 'PLACEHOLDER',
        'small_text': 'PLACEHOLDER',
        'large_image': 'PLACEHOLDER',
        'small_image': 'PLACEHOLDER',
        'buttons': [
            {
                'label': 'PLACEHOLDER',
                'url': 'PLACEHOLDER'
            },
            {
                'label': 'PLACEHOLDER',
                'url': 'PLACEHOLDER'
            }
        ]
    },
    'EXTENSIONS': {
        'moderation': 'PLACEHOLDER',
        'games': 'PLACEHOLDER',
        'nsfw': 'PLACEHOLDER'
    },
    'NOTIFICATIONS': {
        'state': 'PLACEHOLDER',
        'webhook_url': 'PLACEHOLDER'
    },
    'PROTECTIONS': {
        'webhook_url': 'PLACEHOLDER',
        'warn_for_admin': 'PLACEHOLDER',
        'anti_spam_ping': {
            'state': 'PLACEHOLDER',
            'exclude_friends': 'PLACEHOLDER',
            'calls': 'PLACEHOLDER',
            'period': 'PLACEHOLDER'
        },
        'anti_spam_groupchat': {
            'state': 'PLACEHOLDER',
            'calls': 'PLACEHOLDER',
            'period': 'PLACEHOLDER'
        },
        'anti_spam_friend': {
            'state': 'PLACEHOLDER',
            'calls': 'PLACEHOLDER',
            'period': 'PLACEHOLDER'
        },
        'anti_spam_dm': {
            'state': 'PLACEHOLDER',
            'calls': 'PLACEHOLDER',
            'period': 'PLACEHOLDER'
        }
    }
}
HELPMESSAGES = {
    'DISCORD_TOKEN': {
        'required': True,
        'index': 0,
        'description': 'Your Discord token will be used to make API calls to the Discord gateway. If you don\'t know how to obtain this token, check out FAQ #8 in our Discord server.'
    },
    'LOGGING_GUILD': {
        'required': True,
        'index': 1,
        'description': 'This ID should point to the server where all your bot stuff will be logged. It will log to this servers system_channel, that needs to be set in its settings. If you don\'t know how to obtain this ID, check out FAQ #9 in our Discord server.'
    },
    'PASSWORD': {
        'required': False,
        'index': 2,
        'description': 'Your Discord password is required to be able to use the uclone, invisible, mee6, setpfp and setname commands, as these edit your settings and thus require a higher level of authentication.'
    },
    'PREFIXES': {
        'required': True,
        'index': 3,
        'description': 'The prefix is what the message content must contain initially to have a command invoked. You can provide words, like \'hey \' (with space) or just a character, like \'!\'. Any message that starts with this prefix will automatically be deleted. Having multiple prefixes is possible, but not required.'
    },
    'ERRORINFO': {
        'required': False,
        'index': 4,
        'description': 'This setting will determine whether errors that might ocurr when using a command, will be send in the channel where the command was used. Errors are always logged to your log channel regardless of this setting.'
    },
    'SNIPING_nitro': {
        'required': False,
        'index': 5,
        'description': 'This setting will determine whether the selfbot will snipe Discord nitro gifts by immediately claiming them. This feature is spam protected, and excluded servers can be set in the config file.'
    },
    'SNIPING_privnote': {
        'required': False,
        'index': 6,
        'description': 'This setting will determine whether the selfbot will snipe privnotes by immediately opening them and saving the contents to a file. This feature is spam protected, and excluded servers can be set in the config file.'
    },
    'SNIPING_token': {
        'required': False,
        'index': 7,
        'description': 'This setting will determine whether the selfbot will snipe Discord tokens by immediately logging them to your log channel. This feature is spam protected, and excluded servers can be set in the config file.'
    },
    'SNIPING_giveaway': {
        'required': False,
        'index': 8,
        'description': 'This setting will determine whether the selfbot will snipe giveaways by reacting with an emote to specific messages after a delay. This feature is spam protected, and excluded servers can be set in the config file.'
    },
    'EMBED': {
        'required': False,
        'index': 9,
        'description': 'This setting will determine whether commands will send their output be in an embed. The footer text and image, along with the colour and autodelete delay is customizable. (Valid colour names can be found here: https://geazersb.github.io/valid_colours.png, any hex is also possible)'
    },
    'DMLOG': {
        'required': False,
        'index': 10,
        'description': 'This setting will determine whether deleted and edited messages in DMs will be logged. These will be logged in a separate webhook url chosen by you. This can NOT be a webhook in your logging servers system channel. If you don\'t know how to obtain this url, check out FAQ #10 in our Discord server.'
    },
    'GUILDLOG': {
        'required': False,
        'index': 11,
        'description': 'This setting will determine whether deleted and edited messages in servers will be logged. These, unlike with DMLOG and KEYWORDLOG, can be retrieved by using the serverlogs command. There is no reason not to keep this disabled, apart from a very minor RAM usage decrease.'
    },
    'KEYWORDLOG': {
        'required': False,
        'index': 12,
        'description': 'This setting will determine whether customizable keywords will be logged. These will be logged in a separate webhook url chosen by you. This can NOT be a webhook in your logging servers system channel. If you don\'t know how to obtain this url, check out FAQ #10 in our Discord server.'
    },
    'RPC': {
        'required': False,
        'index': 13,
        'description': 'This setting will determine whether to enable custom Rich Presence over Discord. For information regarding this subject, check our Discord. Unless you know what you are doing, it is not recommended to set this up right now.'
    },
    'NOTIFICATIONS': {
        'required': False,
        'index': 14,
        'description': 'This setting will determine whether friend added/removed and server left/joined events will be logged. These will be logged in a separate webhook url chosen by you. This can NOT be a webhook in your logging servers system channel. If you dont know how to obtain this url, check out FAQ #10 in our Discord server.'
    },
    'EXTENSION_moderation': {
        'required': False,
        'index': 15,
        'description': 'This setting will determine whether you want to load the Moderation extension on startup. This includes the mpurge, kick, ban, copybans, lock, unlock, nuke, mute, unmute, and slowmode commands.'
    },
    'EXTENSION_games': {
        'required': False,
        'index': 16,
        'description': 'This setting will determine whether you want to load the Games extension on startup. This includes the minesweeper, typeracer, guesstheword, guessthetiming, solvetheequation, akinator, hangman, doyouknowthisflag and guessthelogo commands.'
    },
    'EXTENSION_nsfw': {
        'required': False,
        'index': 17,
        'description': 'This setting will determine whether you want to load the NSFW on startup. This includes the hentai and porn groupcommands. (Made by Envy)'
    },
    'PROTECTIONS_warn_for_admin': {
        'required': False,
        'index': 18,
        'description': 'This setting will determine whether the bot will warn you for any Discord staff members typing in chat. It will not prevent you from using any commands, if it is the case however.'
    },
    'PROTECTIONS_anti_spam_ping': {
        'required': False,
        'index': 19,
        'description': 'This setting will determine whether the bot will block a user after the times he/she has pinged you, has exceeded a by you chosen rate limit. Example: If your accepted pings is 5, and your timespan is 10, the bot will block the user that pings you 6x in under 10 seconds.'
    },
    'PROTECTIONS_anti_spam_groupchat': {
        'required': False,
        'index': 20,
        'description': 'This setting will determine whether the bot will block a user after the times he/she has added you to a group chat, has exceeded a by you chosen rate limit. Example: If your accepted group adds is 3, and your timespan is 15, the bot will block the owner of the group that added you 3x in under 15 seconds.'
    },
    'PROTECTIONS_anti_spam_friend': {
        'required': False,
        'index': 21,
        'description': 'This setting will determine whether the bot will disable receiving friend requests, if the rate at which this happened has exceeded a by you chosen rate limit. Example: If your accepted friend requests is 2, and your timespan is 5, the bot will change your settings so that you can\'t receive any more friend requests.' 
    },
    'PROTECTIONS_anti_spam_dm': {
        'required': False,
        'index': 22,
        'description': 'This setting will determine whether the bot will disable receiving new DMs from non friends, if the rate at which this happened has exceeded a by you chosen rate limit. Example: If your accepted dms is 7, and your timespan is 20, the bot will change your settings so that you can\'t receive any more new dms.'
    }
}


def lines(colour: str = 'white'):
    colours = {
        'white': WHITE,
        'red': RED,
        'green': GREEN,
        'cyan': CYAN
    }
    print(f"{DIM}{colours.get(colour)} {'-' * 105}")


def checked_input(prompt: str, check: callable = None) -> str:
    check = check or (lambda _: True)
    while True:
        inp = input(prompt).strip()
        if inp and check(inp):
            return inp
        print(f'{RED} [!] Invalid input')


def yes_no(prompt: str):
    prompt += ' Answer yes/no > '
    while True:
        inp = input(prompt).strip().casefold()
        if inp in ('yes', 'y', 't', '1', 'enable', 'on'):
            return True
        if inp in ('no', 'n', 'f', '0', 'disable', 'off'):
            return False
        print(f'{RED} [!] Invalid input. Answer yes/no or something similar.')


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


def showhelp(option: str):
    data = HELPMESSAGES.get(option)
    name = f"{option.lower().replace('_', ' ').title()} ({'required' if data['required'] else 'optional'})"
    progress = f" | {data['index'] + 1}/{len(HELPMESSAGES)} ({(data['index'] / len(HELPMESSAGES) * 100):.2f}% completed)"
    desc = indent('\n'.join([(l.ljust(100) + f'{DIM}{CYAN}|') for l in wrap(data['description'], 97)]), f' {DIM}{CYAN}|{WHITE}   ')
    print()
    lines('cyan')
    print(f"{DIM}{CYAN} |   {BRIGHT}{WHITE}{(name + progress).ljust(100) + f'{DIM}{CYAN}|'}\n{desc}")
    lines('cyan')


def config_setup():
    global FIRST_TIME
    cls()

    with open(Path('data/json/config.json'), 'r+', encoding='utf-8') as f:
        try:
            config = json.load(f)
            # For if I changed the config
            for k, v in DEFAULT.items():
                if k not in config.keys():
                    config[k] = v

        except json.JSONDecodeError:
            f.seek(0)
            f.truncate(0)
            json.dump(DEFAULT, f, indent=4)
            with open(Path('data/json/config.json'), encoding='utf-8') as f:
                config = json.load(f)

    with open(Path('data/json/config.json'), 'w', encoding='utf-8') as f:
        try:
            if config['DISCORD_TOKEN'] == 'PLACEHOLDER':
                showhelp('DISCORD_TOKEN')
                config['DISCORD_TOKEN'] = checked_input(f'{MAGENTA} [>] {WHITE}Your Discord token > ', lambda s: re.match(TOKEN_REGEX, s))
                cls()

            if config['LOGGING_GUILD'] == 'PLACEHOLDER':
                showhelp('LOGGING_GUILD')
                config['LOGGING_GUILD'] = int(checked_input(f'{MAGENTA} [>] {WHITE}Your logging servers ID > ', lambda s: re.match(ID_REGEX, s)))
                cls()

            if config['PASSWORD'] == 'PLACEHOLDER':
                showhelp('PASSWORD')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to set a password?')
                if answer:
                    config['PASSWORD'] = checked_input(f'{MAGENTA} [>] {WHITE}Your Discord password > ')
                else:
                    config['PASSWORD'] = None
                cls()

            if config['PREFIXES'][0] == 'PLACEHOLDER':
                showhelp('PREFIXES')
                config['PREFIXES'] = list(map(lambda p: p.lstrip() if len(p.strip()) >= 3 else p.strip(), checked_input(f'{MAGENTA} [>] {WHITE}What prefix(es) do you want? Separate multiple entries with a comma (,) > ').split(',')))
                cls()

            if config['ERRORINFO'] == 'PLACEHOLDER':
                showhelp('ERRORINFO')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable error info?')
                config['ERRORINFO'] = answer
                cls()

            if config['SNIPING']['nitro']['state'] == 'PLACEHOLDER':
                showhelp('SNIPING_nitro')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable sniping gifts?')
                config['SNIPING']['nitro']['state'] = answer
                cls()

            if config['SNIPING']['privnote']['state'] == 'PLACEHOLDER':
                showhelp('SNIPING_privnote')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable sniping privnotes?')
                config['SNIPING']['privnote']['state'] = answer
                cls()

            if config['SNIPING']['token']['state'] == 'PLACEHOLDER':
                showhelp('SNIPING_token')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable sniping tokens?')
                config['SNIPING']['token']['state'] = answer
                cls()

            if config['SNIPING']['giveaway']['state'] == 'PLACEHOLDER':
                showhelp('SNIPING_giveaway')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable sniping giveaways?')
                config['SNIPING']['giveaway']['state'] = answer
                cls()

            if config['EMBED']['state'] == 'PLACEHOLDER':
                showhelp('EMBED')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable embeds?')
                if answer:
                    config['EMBED']['state'] = True
                    config['EMBED']['showspeed'] = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to show the time it took for the command to process, in the embed?')
                    config['EMBED']['colour'] = checked_input(f'{MAGENTA} [>] {WHITE}What do you want your embed colour to be? A HEX or colour name > ')
                    config['EMBED']['footer_text'] = checked_input(f'{MAGENTA} [>] {WHITE}What do you want your footer text to be? Your text > ')
                    config['EMBED']['footer_icon'] = checked_input(f'{MAGENTA} [>] {WHITE}What do you want your footer image to be? Image link > ', lambda s: re.match(URL_REGEX, s))
                    config['EMBED']['autodelete'] = int(checked_input(f'{MAGENTA} [>] {WHITE}After how many seconds do you want the embed to be deleted? Time in seconds > ', lambda s: s.isdigit()))
                else:
                    config['EMBED'] = {
                        'state': False,
                        'showspeed': None,
                        'colour': None,
                        'footer_text': None,
                        'footer_icon': None,
                        'autodelete': None
                    }
                cls()

            if config['DMLOG']['state'] == 'PLACEHOLDER':
                showhelp('DMLOG')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable dmlog?')
                if answer:
                    config['DMLOG']['state'] = True
                    config['DMLOG']['webhook_url'] = checked_input(f'{MAGENTA} [>] {WHITE}What is the webhook URL you want this to be logged over? URL > ', lambda s: re.match(URL_REGEX, s)).strip()
                else:
                    config['DMLOG'] = {
                        'state': False,
                        'webhook_url': None
                    }
                cls()

            if config['GUILDLOG'] == 'PLACEHOLDER':
                showhelp('GUILDLOG')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable guildlog?')
                config['GUILDLOG'] = answer
                cls()

            if config['KEYWORDLOG']['state'] == 'PLACEHOLDER':
                showhelp('KEYWORDLOG')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable keywordlog?')

                if answer:
                    config['KEYWORDLOG']['state'] = True
                    config['KEYWORDLOG']['webhook_url'] = checked_input(f'{MAGENTA} [>] {WHITE}What is the webhook URL you want this to be logged over? URL > ', lambda s: re.match(URL_REGEX, s)).strip()
                    config['KEYWORDLOG']['keywords'] = list(map(str.strip, checked_input(f'{MAGENTA} [>] {WHITE}What keywords do you want logged? Separate multiple entries with a comma (,) > ').split(',')))
                else:
                    config['KEYWORDLOG'] = {
                        'state': False,
                        'webhook_url': None,
                        'keywords': []
                    }
                cls()

            if config['RPC']['state'] == 'PLACEHOLDER':
                showhelp('RPC')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable RPC?')
                if answer:
                    config['RPC']['state'] = True
                    config['RPC']['clientid'] = int(checked_input(f'{MAGENTA} [>] {WHITE}RPC Application ID > ', lambda s: re.match(ID_REGEX, s)))
                    config['RPC']['name'] = checked_input(f'{MAGENTA} [>] {WHITE}RPC Status > ', lambda s: len(s) < 100)
                    config['RPC']['details'] = checked_input(f'{MAGENTA} [>] {WHITE}RPC Details > ', lambda s: len(s) < 100)
                    config['RPC']['large_text'] = checked_input(f'{MAGENTA} [>] {WHITE}RPC Tooltip for the large image > ', lambda s: len(s) < 999)
                    config['RPC']['small_text'] = checked_input(f'{MAGENTA} [>] {WHITE}RPC Tooltip for the small image > ', lambda s: len(s) < 999)
                    config['RPC']['large_image'] = checked_input(f'{MAGENTA} [>] {WHITE}RPC Name of the uploaded image for the large profile artwork > ')
                    config['RPC']['small_image'] = checked_input(f'{MAGENTA} [>] {WHITE}RPC Name of the uploaded image for the small profile artwork > ')
                    buttons = []
                    buttons.append({
                        'label': checked_input(f'{MAGENTA} [>] {WHITE}RPC Button 1 label > ', lambda s: len(s) < 35), 
                        'url': checked_input(f'{MAGENTA} [>] {WHITE}RPC Button 1 url > ', lambda s: re.match(URL_REGEX, s))
                    })
                    buttons.append({
                        'label': checked_input(f'{MAGENTA} [>] {WHITE}RPC Button 2 label > ', lambda s: len(s) < 35), 
                        'url': checked_input(f'{MAGENTA} [>] {WHITE}RPC Button 2 url > ', lambda s: re.match(URL_REGEX, s))
                    })
                    config['RPC']['buttons'] = buttons
                else:
                    config['RPC'] = {
                        'state': False,
                        'clientid': None,
                        'name': None,
                        'details': None,
                        'large_text': None,
                        'small_text': None,
                        'large_image': None,
                        'small_image': None,
                        'buttons': [
                            {
                                'label': None,
                                'url': None
                            },
                            {
                                'label': None,
                                'url': None
                            }
                        ]
                    }
                cls()

            if config['NOTIFICATIONS']['state'] == 'PLACEHOLDER':
                showhelp('NOTIFICATIONS')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable logging server/friend changes?')
                if answer:
                    config['NOTIFICATIONS']['state'] = True
                    config['NOTIFICATIONS']['webhook_url'] = checked_input(f'{MAGENTA} [>] {WHITE}What is the webhook URL you want this to be logged over? URL > ', lambda s: re.match(URL_REGEX, s))
                else:
                    config['NOTIFICATIONS'] = {
                        'state': False,
                        'webhook_url': None
                    }
                cls()

            if config['EXTENSIONS']['moderation'] == 'PLACEHOLDER':
                showhelp('EXTENSION_moderation')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable the moderation extension?')
                config['EXTENSIONS']['moderation'] = answer
                cls()

            if config['EXTENSIONS']['games'] == 'PLACEHOLDER':
                showhelp('EXTENSION_games')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable the games extension?')
                config['EXTENSIONS']['games'] = answer
                cls()

            if config['EXTENSIONS']['nsfw'] == 'PLACEHOLDER':
                showhelp('EXTENSION_nsfw')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable the NSFW extension?')
                config['EXTENSIONS']['nsfw'] = answer
                cls()

            if config['PROTECTIONS']['warn_for_admin'] == 'PLACEHOLDER':
                showhelp('PROTECTIONS_warn_for_admin')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable the staff warn protection?')
                config['PROTECTIONS']['warn_for_admin'] = answer
                cls()
            
            if config['PROTECTIONS']['anti_spam_ping']['state'] == 'PLACEHOLDER':
                showhelp('PROTECTIONS_anti_spam_ping')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable anti ping spam protection?')
                if answer:
                    config['PROTECTIONS']['anti_spam_ping']['state'] = True
                    config['PROTECTIONS']['anti_spam_ping']['exclude_friends'] = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to exclude friends from this protection?')
                    config['PROTECTIONS']['anti_spam_ping']['calls'] = int(checked_input(f'{MAGENTA} [>] {WHITE}How many pings will you accept (set timespan next)? Number > ', lambda s: s.isdigit()))
                    config['PROTECTIONS']['anti_spam_ping']['period'] = int(checked_input(f'{MAGENTA} [>] {WHITE}In what timespan will you be accepting this many pings? Time in seconds > ', lambda s: s.isdigit()))
                else:
                    config['PROTECTIONS']['anti_spam_ping'] = {
                        'state': None,
                        'exclude_friends': None,
                        'calls': None,
                        'period': None
                    }
                cls()

            if config['PROTECTIONS']['anti_spam_groupchat']['state'] == 'PLACEHOLDER':
                showhelp('PROTECTIONS_anti_spam_groupchat')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable anti groupchat spam protection?')
                if answer:
                    config['PROTECTIONS']['anti_spam_groupchat']['state'] = True
                    config['PROTECTIONS']['anti_spam_groupchat']['calls'] = int(checked_input(f'{MAGENTA} [>] {WHITE}How many group adds will you accept (set timespan next)? Number > ', lambda s: s.isdigit()))
                    config['PROTECTIONS']['anti_spam_groupchat']['period'] = int(checked_input(f'{MAGENTA} [>] {WHITE}In what timespan will you be accepting this many group adds? Time in seconds > ', lambda s: s.isdigit()))
                else:
                    config['PROTECTIONS']['anti_spam_groupchat'] = {
                        'state': None,
                        'calls': None,
                        'period': None
                    }
                cls()

            if config['PROTECTIONS']['anti_spam_friend']['state'] == 'PLACEHOLDER':
                showhelp('PROTECTIONS_anti_spam_friend')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable anti friend spam protection?')
                if answer:
                    config['PROTECTIONS']['anti_spam_friend']['state'] = True
                    config['PROTECTIONS']['anti_spam_friend']['calls'] = int(checked_input(f'{MAGENTA} [>] {WHITE}How many friend requests will you accept (set timespan next)? Number > ', lambda s: s.isdigit()))
                    config['PROTECTIONS']['anti_spam_friend']['period'] = int(checked_input(f'{MAGENTA} [>] {WHITE}In what timespan will you be accepting this many friend requests? Time in seconds > ', lambda s: s.isdigit()))
                else:
                    config['PROTECTIONS']['anti_spam_friend'] = {
                        'state': None,
                        'calls': None,
                        'period': None
                    }
                cls()

            if config['PROTECTIONS']['anti_spam_dm']['state'] == 'PLACEHOLDER':
                showhelp('PROTECTIONS_anti_spam_dm')
                answer = yes_no(f'{MAGENTA} [?] {WHITE}Do you wish to enable anti DM spam protection?')
                if answer:
                    config['PROTECTIONS']['anti_spam_dm']['state'] = True
                    config['PROTECTIONS']['anti_spam_dm']['calls'] = int(checked_input(f'{MAGENTA} [>] {WHITE}How many new DMs will you accept (set timespan next)? Number > ', lambda s: s.isdigit()))
                    config['PROTECTIONS']['anti_spam_dm']['period'] = int(checked_input(f'{MAGENTA} [>] {WHITE}In what timespan will you be accepting this many new DMs? Time in seconds > ', lambda s: s.isdigit()))
                else:
                    config['PROTECTIONS']['anti_spam_dm'] = {
                        'state': None,
                        'calls': None,
                        'period': None
                    }
                cls()

            if any(v is True for v in (
                config['PROTECTIONS']['anti_spam_dm']['state'],
                config['PROTECTIONS']['anti_spam_friend']['state'],
                config['PROTECTIONS']['anti_spam_groupchat']['state'],
                config['PROTECTIONS']['warn_for_admin'],
                config['PROTECTIONS']['anti_spam_ping']['state']
            )) and config['PROTECTIONS']['webhook_url'] == 'PLACEHOLDER':
                answer = checked_input(f'{MAGENTA} [>] {WHITE}What is the webhook URL you want the protections to be logged over? URL > ', lambda s: re.match(URL_REGEX, s)).strip()
                config['PROTECTIONS']['webhook_url'] = answer
                cls()

            json.dump(config, f, indent=4)
            cls()

        except KeyboardInterrupt:
            cls()
            lines('red')
            print(f'{RED}\n [!] The setup process was cancelled. Restart the bot to continue.\n')
            lines('red')
            json.dump(config, f, indent=4)
            sys.exit()

        except Exception as exc:
            cls()
            lines('red')
            print(f'{RED}\n [!] The setup process has encountered an error. Restart the bot to retry.\n [!] Error: {exc}\n')
            lines('red')
            json.dump(config, f, indent=4)
            sys.exit()
