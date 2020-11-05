#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
import sys
import re

from fnclient import (
    DigestRecord,
    DigestRecordsCollection,
    DigestRecordState,
    DigestRecordCategory,
    PRINT_PREFIX,
    DIGEST_RECORD_CATEGORY_VALUES,
    DIGEST_RECORD_SHORTS_SUBCATEGORY_VALUES,
    DIGEST_RECORD_RELEASES_SUBCATEGORY_VALUES,
)


def yaml_to_html(yaml_path, html_path):
    digest_records_collection = DigestRecordsCollection()
    digest_records_collection.load_from_yaml(yaml_path)
    output_records = {
        DigestRecordCategory.MAIN.value: [],
        DigestRecordCategory.SHORTS.value: {subcategory_value: [] for subcategory_value in DIGEST_RECORD_SHORTS_SUBCATEGORY_VALUES},
        DigestRecordCategory.RELEASES.value: {subcategory_value: [] for subcategory_value in DIGEST_RECORD_RELEASES_SUBCATEGORY_VALUES},
        DigestRecordCategory.OTHER.value: [],
    }
    for digest_record in digest_records_collection.records:
        if digest_record.state != DigestRecordState.IN_DIGEST:
            continue
        if digest_record.category in (DigestRecordCategory.MAIN,
                                      DigestRecordCategory.OTHER):
            output_records[digest_record.category.value].append(digest_record)
        elif digest_record.category in (DigestRecordCategory.SHORTS,
                                        DigestRecordCategory.RELEASES):
            if digest_record.subcategory is not None:
                output_records[digest_record.category.value][digest_record.subcategory.value].append(digest_record)
        else:
            raise NotImplementedError
    output = '<h2>Главное</h2>\n\n'
    for main_record in output_records[DigestRecordCategory.MAIN.value]:
        output += f'<h3>{clear_title(main_record.title)}</h3>\n\n'
        output += f'Подробности - <a href="{main_record.url}">{main_record.url}</a>\n\n'

    output += '<h2>Короткой строкой</h2>\n\n'
    for shorts_record_subcategory, shorts_records in output_records[DigestRecordCategory.SHORTS.value].items():
        output += f'<h3>{shorts_record_subcategory}</h3>\n\n'
        for shorts_record in shorts_records:
            output += f'{clear_title(shorts_record.title)} <a href={shorts_record.url}>{shorts_record.url}</a><br>\n'

    output += '<h2>Релизы</h2>\n\n'
    for releases_record_subcategory, releases_records in output_records[DigestRecordCategory.RELEASES.value].items():
        output += f'<h3>{releases_record_subcategory}</h3>\n\n'
        for releases_record in releases_records:
            output += f'{clear_title(releases_record.title)} <a href={releases_record.url}>{releases_record.url}<br></a>\n'

    output += '<h2>Что ещё посмотреть</h2>\n\n'
    for other_record in output_records[DigestRecordCategory.OTHER.value]:
        output += f'{clear_title(other_record.title)} <a href="{other_record.url}">{other_record.url}</a>\n'

    with open(html_path, 'w') as fout:
        print(f'{PRINT_PREFIX}Saving output to "{html_path}"')
        fout.write(output)


def clear_title(title: str):
    return re.sub('^\[.+\]\s+', '', title)


def parse_command_line_args():
    parser = argparse.ArgumentParser(
                        description='FOSS News Converter')
    parser.add_argument('SOURCE',
                        help='Source file (YAML)')
    parser.add_argument('DESTINATION',
                        help='Source file (HTML)')
    args = parser.parse_args()
    return args


def main():
    args = parse_command_line_args()
    source_path = args.SOURCE
    destination_path = args.DESTINATION
    yaml_to_html(source_path, destination_path)


if __name__ == "__main__":
    sys.exit(main())
