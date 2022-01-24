# -*- coding: utf-8 -*-
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from urllib3 import HTTPResponse, PoolManager


class Sherlock:
    def __init__(self, username: str, max_workers: int):
        """Checks if a username exists on about 200 social media platforms

        Args:
            username (str): The username to search for
            max_workers (int): The maximum amount of workers (threads) to send requests with
        """
        self._start_time = time.perf_counter()
        self._username = username
        self._max_workers = max_workers
        self._pool = PoolManager(timeout=2)
        self._results = {
            'meta': {
                'websites_checked': int(),
                'time_elapsed': int()
            },
            'data': {
                'unknown': list(),
                'available': list(),
                'claimed': list()
            }
        }

    def _get_available_websites(self) -> List[dict]:
        return [
            (lambda d: d.update(name=k) or d)(v) for k, v in
            json.loads(self._pool.request(
                'GET',
                'https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock/resources/data.json'
            ).data.decode('utf-8')).items()
        ]

    def _load_url(self, website_data: dict) -> Optional[HTTPResponse]:
        url = website_data['url'].format(self._username)
        if regex := website_data.get('regexCheck'):
            if not bool(re.match(regex, self._username)):
                self._results['data']['available'].append(url)
                return None
        try:
            return self._pool.request('GET', url)
        except:
            self._results['data']['unknown'].append(url)

    def start(self) -> Dict[str, List[str]]:
        available_websites = self._get_available_websites()
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_url = {
                executor.submit(self._load_url, d): d
                for d in available_websites
            }

            # I tried this a different (shorter) way; with only one .append statement and no continue statements,
            # but it doesn't seem to work properly, so I just took the easy way out and sinned
            for future in as_completed(future_to_url):
                website_data = future_to_url[future]
                response_data = future.result()
                website = f"{website_data['name']}: {website_data['url'].format(self._username)}"

                if not response_data:
                    self._results['data']['unknown'].append(website)
                    continue
                else:
                    error_type = website_data['errorType']
                    if error_type == 'message':
                        try:
                            response = response_data.data.decode('utf-8')
                        except UnicodeDecodeError:
                            self._results['data']['available'].append(website)
                            continue

                        expected_if_error = website_data.get('errorMsg', '')
                        if isinstance(expected_if_error, str):
                            if expected_if_error in response:
                                self._results['data']['available'].append(website)
                                continue
                            else:
                                self._results['data']['claimed'].append(website)
                                continue
                        else:
                            if any(e in response for e in expected_if_error):
                                self._results['data']['available'].append(website)
                                continue
                            else:
                                self._results['data']['claimed'].append(website)
                                continue

                    elif error_type == 'response_url':
                        if response_data.geturl() == website_data['errorUrl'].format(self._username):
                            self._results['data']['available'].append(website)
                            continue

                    elif error_type == 'status_code':
                        if not 200 <= response_data.status < 300:
                            self._results['data']['available'].append(website)
                            continue
                        else:
                            self._results['data']['claimed'].append(website)
                            continue

                    else:
                        self._results['data']['unknown'].append(website)
                        continue

        self._results['meta']['time_elapsed'] = time.perf_counter() - self._start_time
        self._results['meta']['websites_checked'] = len(available_websites)
        return self._results
