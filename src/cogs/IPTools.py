# -*- coding: utf-8 -*-
import socket
import time
from contextlib import suppress
from datetime import datetime
from textwrap import dedent
from typing import List

from discord.ext import commands
from icmplib import async_ping, traceroute
from pycountry import countries
from unshortenit import UnshortenIt

from .utils import flags
from .utils.checks import bot_has_permissions
from .utils.enums import ProxyType
from .utils.exceptions import DataNotFound
from .utils.helpers import format_date
from .utils.tokens import (APIFLASH_TOKEN, APILAYER_TOKEN, IPINFO_TOKEN,
                           VIEWDNS_TOKEN, VIRUSTOTAL_TOKEN, VPNAPI_TOKEN,
                           WEBRESOLVER_TOKEN, WHOISXML_TOKEN)


class IPTools(commands.Cog):
    '''Category for all IP related commands.'''

    def __init__(self, bot):
        self.bot = bot


    @staticmethod
    async def _send_proxies(ctx, timeout: int, proxy_type: ProxyType) -> None:
        r = await (await ctx.bot.AIOHTTP_SESSION.get(f'https://api.proxyscrape.com/?request=displayproxies&proxytype={proxy_type}&timeout={timeout}')).text()
        await ctx.textfile(r, f'{len(r.splitlines())}_{proxy_type}_proxies.txt')


    @staticmethod
    def _tcpping(host: str, port: int, timeout: float, packetcount: int, interval: float) -> List[float]:
        results = []
        for _ in range(packetcount):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            start = time.perf_counter()
            try:
                s.connect((host, port))
                s.shutdown(socket.SHUT_RD)
            except socket.timeout:
                results.append(None)
            except OSError:
                pass
            else:
                results.append(round((time.perf_counter() - start) * 1000, 2))
            finally:
                time.sleep(interval)
        return results


    @commands.command(aliases=['ebayviewbot', 'crawl'])
    async def viewbot(self, _, url: str, amount: int = 20):
        '''Will send [amount] get requests to <url>'''
        await self.bot.log(f'Sending {amount} get requests to {url}')
        with suppress(Exception):
            for _ in range(amount):
                async with self.bot.AIOHTTP_SESSION.get(url, timeout=15):
                    pass


    @commands.command(aliases=['virustotal', 'viruscheck'])
    async def scanmalware(self, ctx, url: str):
        '''Will have <url> checked for malware by anti-virus services'''
        try:
            analysis_id = (await (await self.bot.AIOHTTP_SESSION.post(
                f'https://www.virustotal.com/api/v3/urls',
                headers={'x-apikey': VIRUSTOTAL_TOKEN},
                data={'url': url}
            )).json())['data']['id']
            r = await (await self.bot.AIOHTTP_SESSION.get(
                f'https://www.virustotal.com/api/v3/analyses/{analysis_id}',
                headers={'x-apikey': VIRUSTOTAL_TOKEN}
            )).json()
            data = r['data']['attributes']

            total = '\n'.join([f"{k.capitalize()}: {v}" for k, v in data['stats'].items()])
            results = '\n'.join([
                f"{k}: {v['category']} ({v['result'] or 'N/A'})"
                for k, v in sorted(
                    data['results'].items(),
                    key=lambda item: item[1]['category']
                )
            ])
            msg = f"Total:\n{total}\n\nIndividual:\n{results}"
            await ctx.textfile(msg, 'scan.txt', clean=False)
        except KeyError:
            raise DataNotFound('Couldn\'t scan url')


    @commands.command(aliases=['ip', 'ipinfo', 'hostinfo'])
    async def iplookup(self, ctx, host: str):
        '''Will display information about <host>'''
        r1 = await (await self.bot.AIOHTTP_SESSION.get(f'http://ip-api.com/json/{host}')).json()
        r2 = await (await self.bot.AIOHTTP_SESSION.get(f'https://ipinfo.io/{host}?token={IPINFO_TOKEN}')).json()
        r3 = await (await self.bot.AIOHTTP_SESSION.get(f'https://vpnapi.io/api/{host}?key={VPNAPI_TOKEN}')).json()
        try:
            loc, sec, net = r3['location'], r3['security'], r3['network']
            fields = [
                ('ip-api.com', f"Country: {countries.lookup(r1.get('country')).name}\nRegion: {r1.get('regionName')}\nCity: {r1.get('city')}\nTZ: {r1.get('timezone')}"),
                ('ipinfo.com', f"Country: {countries.lookup(r2.get('country')).name}\nRegion: {r2.get('region')}\nCity: {r2.get('city')}\nTZ: {r2.get('timezone')}"),
                ('vpnapi.io', f"Country: {countries.lookup(loc.get('country')).name}\nRegion: {loc.get('region')}\nCity: {loc.get('city')}\nTZ: {loc.get('time_zone')}"),
                ('Other', f"VPN: {sec.get('vpn')}\nPROXY: {sec.get('proxy')}\nTOR: {sec.get('tor')}\nISP: {net.get('autonomous_system_organization')}\nASN: {net.get('autonomous_system_number')}", False)
            ]
            msg = f"IP Info | {host} ({r1.get('hostname') or 'No Hostname'})"
            await ctx.respond(msg, fields=fields, title='IP Lookup')
        except KeyError:
            raise DataNotFound(f'The host `{host}` couldn\'t be found.')


    @commands.command()
    async def unshorten(self, ctx, link: str):
        '''Will unshorten AdfLy, AdFocus, ShorteSt and MetaRefresh links (including 14 domains)'''
        await ctx.send(UnshortenIt().unshorten(link))


    @commands.command(aliases=['tinyurl'])
    async def shorten(self, ctx, *, link: str):
        '''Will generate a tinyurl link from <link>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'http://tinyurl.com/api-create.php?url={link}')).text()
        await ctx.send(r)


    @commands.command(aliases=['nsresolve', 'reversenslookup'])
    async def resolvenameservers(self, ctx, domain: str, page: int = 1):
        '''Will show domains that share same nameserver as <domain>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.viewdns.info/reversens/?ns={domain}&apikey={VIEWDNS_TOKEN}&output=json&page={page}')).json()
        try:
            await ctx.textfile('\n'.join([d['domain'] for d in r['response']['domains']]))
        except KeyError:
            raise DataNotFound(f'The domain name server {domain} couldn\'t be found.')


    @commands.command(aliases=['isblacklisted'])
    async def spamblacklist(self, ctx, ip: str):
        '''Will check if <ip> is found in spam blacklist databases'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.viewdns.info/spamdblookup/?ip={ip}&apikey={VIEWDNS_TOKEN}&output=json')).json()
        try:
            await ctx.textfile('\n'.join([f"{d['name']}: {d['result']}" for d in r['response']['dbs']]))
        except KeyError:
            raise DataNotFound(f'The IP {ip} couldn\'t be found.')


    @flags.add_flag('--timeout', type=float, default=5.0)
    @flags.add_flag('--packetcount', type=int, default=5)
    @flags.add_flag('--interval', type=int, default=1)
    @flags.command(
        aliases=['icmp'],
        usage='<host> [--timeout=5.0] [--packetcount=5] [--interval=1]'
    )
    async def icmpping(self, ctx, host: str, **options):
        '''Will ping <host> using ICMP packets'''
        timeout, packetcount, interval = options['timeout'], options['packetcount'], options['interval']
        result = await async_ping(
            host,
            packetcount,
            interval,
            timeout
        )
        formatted = '\n'.join([f"**{i}.** {f'{r:.2f}ms' if r else 'No Response'}"
                    for i, r in list(enumerate(result.rtts, 1))])
        msg = dedent(f'''
            **Host:** {host}
            **Timeout:** {timeout}
            **Packet count:** {packetcount}

            {formatted}
            **Average:** {result.avg_rtt:.2f}ms
        ''')
        await ctx.respond(msg, title='ICMP Ping')


    @flags.add_flag('--timeout', type=float, default=5.0)
    @flags.add_flag('--packetcount', type=int, default=5)
    @flags.add_flag('--interval', type=int, default=1)
    @flags.command(
        aliases=['tcp'],
        usage='<host> [port=80] [--timeout=5.0] [--packetcount=5] [--interval=1]'
    )
    async def tcpping(self, ctx, host: str, port: str = 80, **options):
        '''Will ping <host> on port [port] using TCP packets'''
        timeout, packetcount, interval = options['timeout'], options['packetcount'], options['interval']
        results = await self.bot.loop.run_in_executor(
            None,
            lambda: self._tcpping(
                host,
                port,
                timeout,
                packetcount,
                interval
            )
        )
        formatted = '\n'.join([f"**{i}.** {f'{r:.2f}ms' if r else 'No Response'}"
                    for i, r in list(enumerate(results, 1))])

        try:
            filtered = list(filter(None, results))
            average = sum(filtered) / len(filtered)
        except ZeroDivisionError:
            average = 0

        msg = dedent(f'''
            **Host:** {host}
            **Timeout:** {timeout}s
            **Packet count:** {packetcount}
            **Port:** {port}

            {formatted}
            **Average:** {average:.2f}ms
        ''')
        await ctx.respond(msg, title='TCP Ping')


    @commands.command(aliases=['rua'])
    async def resolveuseragent(self, ctx, *, user_agent: str):
        '''Will show information about <user_agent>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.apicagent.com?ua={user_agent}')).json()
        try:
            msg = f'User Agent Info | {user_agent}'
            fields = []
            for k, v in r.items():
                if isinstance(v, dict):
                    fields.append((
                        k.capitalize(),
                        '\n'.join([f"{sk.replace('_', ' ').title()}: {sv}" for sk, sv in v.items()])
                    ))
            await ctx.respond(msg, fields=fields, title='User-Agent Info')
        except KeyError:
            raise DataNotFound(f'The user agent `{user_agent}` couldn\'t be found.') 


    @commands.command(aliases=['dns', 'dnsresolver'])
    async def resolvedns(self, ctx, host: str):
        '''Will resolve a DNS by hostname'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f"https://www.whoisxmlapi.com/whoisserver/DNSService?apiKey={WHOISXML_TOKEN}&domainName={host}&type=1&outputFormat=json")).json()
        try:
            data = r['DNSData']
            msg = f'DNS lookup | {host}'
            fields = [
                ('Type', data['dnsTypes']),
                ('Created', data['audit']['createdDate']),
                ('Updated', data['audit']['updatedDate'])
            ]

            for rec in data['dnsRecords']:
                fields.append((rec['name'], f"TTL: {rec['ttl']}\nAddress: {rec['address']}\nType: {rec['dnsType']}"))

            await ctx.respond(msg, fields=fields, title='Resolve DNS')
        except KeyError:
            raise DataNotFound(f'The DNS `{host}` couldn\'t be found.')


    @commands.command(aliases=['skype', 'skyperesolver'])
    async def resolveskype(self, ctx, name: str):
        '''Will attempt to resolve the IP connected to the Skype <name>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://webresolver.nl/api.php?key={WEBRESOLVER_TOKEN}&json&action=resolve&string={name}')).json()
        try:
            await ctx.respond(f"Username: {r['username']}\nIP: {r['ip']}")
        except KeyError:
            raise DataNotFound(f'The skype account `{name}` couldn\'t be found.')


    @commands.command(aliases=['cfresolver', 'resolvecf'])
    async def resolvecloudflare(self, ctx, domain: str):
        '''Will search for the real IP of a cf protected <domain>'''
        if domain.startswith('www.'):
            domain = domain[4:]
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://webresolver.nl/api.php?key={WEBRESOLVER_TOKEN}&json&action=cloudflare&string={domain}')).json()
        try:
            detected = list(filter(
                lambda d: (
                    not d['cloudflare']
                    and not d['ip'].startswith(('172', '72'))
                ),
                r['domains'].values()
            ))
            msg = f"Cloudflare resolve | {domain}"
            fields = []

            for d in detected:
                fields.append((d['domain'], f"IP: {d['ip']}\nCountry: {countries.lookup(d['country']).name}"))

            await ctx.respond(msg, fields=fields)
        except KeyError:
            raise DataNotFound(f'The domain `{domain}` couldn\'t be resolved.')


    @commands.command(aliases=['webrep', 'vulnerabilities', 'testwebsite'])
    async def websitereputation(self, ctx, host: str):
        '''Will show some information about <host>'s reputation'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f"https://domain-reputation.whoisxmlapi.com/api/v1?apiKey={WHOISXML_TOKEN}&domainName={host}&outputFormat=json")).json()
        try:
            msg = f'Websiterep | {host}'
            fields = [
                ('Reputation', f"{r['reputationScore']}/100")
            ]
            for res in r['testResults']:
                fields.append((res['test'], f"Warnings: {', '.join(res.get('warnings', ['None']))}"))
            await ctx.respond(msg, fields=fields, title='Website Reputation')
        except KeyError:
            raise DataNotFound(f'The website `{host}` couldn\'t be found.')


    @commands.command(aliases=['myip', 'headers'])
    async def showheaders(self, ctx):
        '''Will show the HTTP headers that your client sends when connecting to a webserver'''
        r1 = await (await self.bot.AIOHTTP_SESSION.get('http://httpbin.org/headers')).json()
        r2 = await (await self.bot.AIOHTTP_SESSION.get('https://api.myip.com')).json(content_type='text/html')
        msg = f"**IP:** {r2['ip']}\n\n" + '\n'.join([f'**{k}:** {v}' for k, v in r1['headers'].items()])
        await ctx.respond(msg)


    @commands.command()
    async def whois(self, ctx, host: str):
        '''Will do a WHOIS lookup for <host> and return the results'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey={WHOISXML_TOKEN}&domainName={host}&outputFormat=json')).json()
        data = r['WhoisRecord']
        data_r = data.get('registrant', {'organization': None, 'country': None})
        try:
            to_date = lambda v: format_date(datetime.strptime(data.get(v)[:19], '%Y-%m-%dT%X'))
            msg = f'WHOIS | {host}'
            fields = [
                ('Created', to_date('createdDate')),
                ('Updated', to_date('updatedDate')),
                ('Expires', to_date('expiresDate')),
                ('Registrant', f"Organization: {data_r['organization']} ({countries.lookup(data_r['country']).name})"),
                ('Domain', data['domainName']),
                ('Nameservers', data['nameServers']['rawText'])
            ]
            await ctx.respond(msg, fields=fields)
        except KeyError:
            raise DataNotFound(f'The host `{host}` couldn\'t be found.')


    @commands.command()
    async def portscan(self, ctx, host: str):
        '''Will scan the common ports of a <host>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.viewdns.info/portscan/?host={host}&apikey={VIEWDNS_TOKEN}&output=json')).json()
        try:
            formatted = '\n'.join([(f"**{d['number']}** ({d['service']}): {d['status']}")
                        for d in r['response']['port']])
            msg = f'**Host:** {host}\n{formatted}'
            await ctx.respond(msg)
        except KeyError:
            raise DataNotFound(f'The host `{host}` couldn\'t be found.')


    @flags.add_flag('--timeout', type=float, default=2.0)
    @flags.add_flag('--packetcount', type=int, default=2)
    @flags.add_flag('--interval', type=float, default=0.05)
    @flags.add_flag('--maxhops', type=int, default=15)
    @flags.command(
        aliases=['tracert'],
        usage='<host> [--timeout=2.0] [--packetcount=2] [--interval=0.05] [--maxhops=15]'
    )
    async def traceroute(self, ctx, host: str, **options):
        '''Will determine what servers data traverses through before reaching the <host>'''
        timeout, packetcount, interval, maxhops = options['timeout'], options['packetcount'], options['interval'], options['maxhops']
        result = await self.bot.loop.run_in_executor(
            None,
            lambda: traceroute(
                host,
                packetcount,
                interval,
                timeout,
                max_hops=maxhops
            )
        )

        last_distance, formatted = 0, []
        for hop in result:
            if last_distance != hop.distance:
                formatted.append('Request timed out')
            else:
                formatted.append(f"**{hop.distance} - {hop.address}:** ~{hop.avg_rtt:.2f}ms")
            last_distance = hop.distance

        formatted = '\n'.join(formatted)
        msg = dedent(f'''
            **Host:** {host}
            **Timeout:** {timeout}s
            **Packet count:** {packetcount}

            {formatted}
        ''')
        await ctx.respond(msg)


    @commands.command(usage='<mac (separate with \'-\' like 00-05-etc)>', aliases=['mac'])
    async def maclookup(self, ctx, mac: str):
        '''Will search for the manufacturer of a product based on it's <mac> address'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.viewdns.info/maclookup/?mac={mac}&apikey={VIEWDNS_TOKEN}&output=json')).json()
        msg = f"**MAC:** {mac}\n**Manufacturer:** {r['response']['manufacturer']}"
        await ctx.respond(msg, title='MAC Lookup')


    @commands.command()
    async def phonelookup(self, ctx, number: str):
        '''Will search for the phonenumber and return some information'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'http://apilayer.net/api/validate?access_key={APILAYER_TOKEN}&number={number}&format=1')).json()
        msg = f'Phonelookup | {number}'
        fields = [
            ('Type', r['line_type']),
            ('Valid', r['valid']),
            ('International', r['international_format']),
            ('Country', r.get('country_name', 'Not Found')),
            ('City', r.get('location', 'Not Found')),
            ('Provider', r.get('carrier', 'Not Found'))
        ]
        await ctx.respond(msg, fields=fields)


    @commands.command(aliases=['cfw'])
    async def chinesefirewall(self, ctx, domain: str):
        '''Will check if your <domain> is blocked in China'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.viewdns.info/chinesefirewall/?domain={domain}&apikey={VIEWDNS_TOKEN}&output=json')).json()
        try:    
            data = r['v2response']
            results = {d['location']: d['resultstatus'] for d in data['dnsresults']['server']}
            formatted = '\n'.join(f'**{k}:** {v}'
                        for k, v in results.items())
            msg = dedent(f'''
                **Domain:** {r['query']['domain']}

                {data['dnsresults']['description']}

                {formatted}
            ''')
            await ctx.respond(msg)
        except KeyError:
            raise DataNotFound(f'The domain `{domain}` couldn\'t be found.')


    @commands.command(aliases=['websitescreen', 'screenpage', 'sws'])
    async def screenwebsite(self, ctx, url: str):
        '''Will send a screenshot of a website with the provided <url>'''
        r = await (await self.bot.AIOHTTP_SESSION.get(f'https://api.apiflash.com/v1/urltoimage?access_key={APIFLASH_TOKEN}&response_type=json&url={url}')).json()
        await ctx.respond(image=r['url'])


    @commands.group(aliases=['proxy'], invoke_without_command=True)
    async def proxies(self, _):
        '''Group command for getting http/https/socks4/socks5 proxies'''
        raise commands.CommandNotFound()

    @bot_has_permissions(attach_files=True)
    @proxies.command()
    async def http(self, ctx, proxy_timeout_ms: int = 1000):
        '''Will scrape HTTP proxies and send them as file'''
        await self._send_proxies(ctx, proxy_timeout_ms, ProxyType.http)

    @bot_has_permissions(attach_files=True)
    @proxies.command()
    async def https(self, ctx, proxy_timeout_ms: int = 1000):
        '''Will scrape HTTPS proxies and send them as file'''
        await self._send_proxies(ctx, proxy_timeout_ms, ProxyType.https)

    @bot_has_permissions(attach_files=True)
    @proxies.command()
    async def socks4(self, ctx, proxy_timeout_ms: int = 1000):
        '''Will scrape SOCKS4 proxies and send them as file'''
        await self._send_proxies(ctx, proxy_timeout_ms, ProxyType.socks4)

    @bot_has_permissions(attach_files=True)
    @proxies.command()
    async def socks5(self, ctx, proxy_timeout_ms: int = 1000):
        '''Will scrape SOCKS5 proxies and send them as file'''
        await self._send_proxies(ctx, proxy_timeout_ms, ProxyType.socks5)


def setup(bot):
    bot.add_cog(IPTools(bot))
