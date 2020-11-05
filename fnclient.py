#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
import sys
from fntools import (
    DigestRecordsCollection,
)


def parse_command_line_args():
    parser = argparse.ArgumentParser(description='FOSS News Gathering Client')
    parser.add_argument('SOURCE_OR_CONFIG',
                        help='Source file (HTML or YAML) or config to access remote server')
    parser.add_argument('DESTINATION',
                        help='Destination file (YAML)',
                        nargs='?')
    args = parser.parse_args()
    if '.conf.yaml' not in args.SOURCE_OR_CONFIG:
        if '.html' in args.SOURCE_OR_CONFIG or '.yaml' in args.SOURCE_OR_CONFIG or '.yml' in args.SOURCE_OR_CONFIG:
            if args.DESTINATION is None:
                raise Exception('DESTINATION command line argument is required if source file is passed')
        else:
            raise NotImplementedError
    return args


def main():
    args = parse_command_line_args()
    source_path = args.SOURCE_OR_CONFIG
    destination_path = args.DESTINATION
    records_collection = DigestRecordsCollection()
    records_collection.load(source_path)
    records_collection.categorize_interactively()
    if '.conf.yaml' not in args.SOURCE_OR_CONFIG:
        records_collection.save_to_yaml(destination_path)


if __name__ == "__main__":
    sys.exit(main())
