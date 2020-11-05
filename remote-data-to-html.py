#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
import sys

from fntools import (
    logger,
    DigestRecordsCollection,
)


def parse_command_line_args():
    parser = argparse.ArgumentParser(
                        description='FOSS News Converter')
    parser.add_argument('FNGS_CONFIG',
                        help='Config with data for access to remote FOSS News Gathering Server server')
    parser.add_argument('DIGEST_NUMBER',
                        help='Digest number')
    parser.add_argument('DESTINATION',
                        help='Destination HTML file')
    args = parser.parse_args()
    return args


def main():
    args = parse_command_line_args()
    digest_records_collection = DigestRecordsCollection()
    digest_records_collection.load_specific_digest_records_from_server(args.FNGS_CONFIG, args.DIGEST_NUMBER)
    digest_records_collection.records_to_html(args.DESTINATION)


if __name__ == "__main__":
    sys.exit(main())
