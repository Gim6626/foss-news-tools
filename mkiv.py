#!/usr/bin/env python
from argparse import ArgumentParser
from sys import argv
from urllib.parse import urlencode, urlunsplit


TEMPLATE_HASH = '4e0fc53b2a95fa'


def make_instant_view_url(url: str) -> str:
    if not url.startswith('http'):
        raise ValueError(f"Invalid URL '{url}'")
    query = urlencode(query=dict(url=url, rhash=TEMPLATE_HASH), doseq=True)
    return urlunsplit(('https', 't.me', 'iv', query, ''))


if __name__ == '__main__':
    parser = ArgumentParser(description='Make Telegram Instant View URL for FOSS News article.')
    parser.add_argument('url', help='article URL')
    args = parser.parse_args()
    print(make_instant_view_url(args.url))
