#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
import logging
import sys

from fntools import (
    logger,
    HtmlFormat,
    DigestRecordsCollection,
)


def parse_command_line_args():
    parser = argparse.ArgumentParser(
                        description='FOSS News Converter')
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help='Enable debug output')
    parser.add_argument('FNGS_CONFIG',
                        help='Config with data for access to remote FOSS News Gathering Server server')
    parser.add_argument('FORMAT',
                        help='Output format',
                        choices=[f.name for f in HtmlFormat])
    parser.add_argument('DIGEST_NUMBER',
                        help='Digest number')
    parser.add_argument('DESTINATION',
                        help='Destination HTML file')
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    return args


def main():
    args = parse_command_line_args()
    digest_records_collection = DigestRecordsCollection(args.FNGS_CONFIG)
    # TODO: Check digest number if it is int
    digest_records_collection.load_specific_digest_records_from_server(int(args.DIGEST_NUMBER))
    digest_records_collection.records_to_html(args.FORMAT, args.DESTINATION)


if __name__ == "__main__":
    sys.exit(main())
