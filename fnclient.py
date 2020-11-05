#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
import sys
from fntools import (
    DigestRecordsCollection,
)


def parse_command_line_args():
    parser = argparse.ArgumentParser(description='FOSS News Gathering Client')
    parser.add_argument('FNGS_CONFIG',
                        help='Config with data for access to remote FOSS News Gathering Server server')
    args = parser.parse_args()
    return args


def main():
    args = parse_command_line_args()
    config_path = args.FNGS_CONFIG
    records_collection = DigestRecordsCollection()
    records_collection.load_new_digest_records_from_server(config_path)
    records_collection.categorize_interactively()


if __name__ == "__main__":
    sys.exit(main())
