#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
import argcomplete
import sys
import re
import datetime
from pprint import pprint, pformat
from typing import List
import yaml
from enum import Enum

# TODO: Categories and subcategories for main news too
# TODO: Ignore duplicates

DIGEST_RECORD_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'
PRINT_PREFIX = '=> '


class DigestRecordState(Enum):
    UNKNOWN = 'unknown'
    IN_DIGEST = 'in_digest'
    IGNORED = 'ignored'


DIGEST_RECORD_STATE_VALUES = [state.value for state in DigestRecordState]


class DigestRecordCategory(Enum):
    UNKNOWN = 'unknown'
    MAIN = 'main'
    SHORTS = 'shorts'
    RELEASES = 'releases'
    OTHER = 'other'


DIGEST_RECORD_CATEGORY_VALUES = [category.value for category in DigestRecordCategory]


class DigestRecordShortsSubCategory(Enum):
    EVENTS = 'Мероприятия'
    INTROS = 'Внедрения'
    OPENING = 'Открытие кода и данных'
    NEWS = 'Новости FOSS организаций'
    DIY = 'DIY'
    LAW = 'Юридические вопросы'
    KnD = 'Ядро и дистрибутивы'
    SYSTEM = 'Системное'
    SPECIAL = 'Специальное'
    MULTIMEDIA = 'Мультимедиа'
    SECURITY = 'Безопасность'
    DEVOPS = 'DevOps'
    DATA_SCIENCE = 'Data Science'
    WEB = 'Web'
    DEV = 'Для разработчиков'
    MANAGEMENT = 'Менеджмент'
    USER = 'Пользовательское'
    GAMES = 'Игры'
    HARDWARE = 'Железо'
    MISC = 'Разное'


DIGEST_RECORD_SHORTS_SUBCATEGORY_VALUES = [category.value for category in DigestRecordShortsSubCategory]


class DigestRecordReleasesSubcategory(Enum):
    KnD = 'Ядро и дистрибутивы'
    SYSTEM = 'Системный софт'
    SECURITY = 'Безопасность'
    DEVOPS = 'DevOps'
    DATA_SCIENCE = 'Data Science'
    WEB = 'Web'
    DEV = 'Для разработчиков'
    SPECIAL = 'Специальный софт'
    MULTIMEDIA = 'Мультимедиа'
    GAMES = 'Игры'
    USER = 'Пользовательский софт'
    MISC = 'Разное'


DIGEST_RECORD_RELEASES_SUBCATEGORY_VALUES = [category.value for category in DigestRecordReleasesSubcategory]


class DigestRecord:

    def __init__(self,
                 dt: datetime.datetime,
                 title: str,
                 url: str,
                 state: DigestRecordState = DigestRecordState.UNKNOWN,
                 digest_number: int = None,
                 category: DigestRecordCategory = DigestRecordCategory.UNKNOWN,
                 subcategory: Enum = None):
        self.dt = dt
        self.title = title
        self.url = url
        self.state = state
        self.digest_number = digest_number
        self.category = category
        self.subcategory = subcategory

    def __str__(self):
        return pformat(self.to_dict())

    def to_dict(self):
        return {
            'datetime': self.dt.strftime(DIGEST_RECORD_DATETIME_FORMAT),
            'title': self.title,
            'url': self.url,
            'state': self.state.value,
            'digest_number': self.digest_number,
            'category': self.category.value,
            'subcategory': self.subcategory.value if self.subcategory is not None else None,
        }


class DigestRecordsCollection:

    def __init__(self,
                 records: List[DigestRecord] = None):
        self.records = records if records is not None else []
        self._filtered_records = []

    def __str__(self):
        return pformat([record.to_dict() for record in self.records])

    def save_to_yaml(self, yaml_path: str):
        records_plain = []
        for record_object in self.records:
            record_plain = {
                'datetime': record_object.dt.strftime(DIGEST_RECORD_DATETIME_FORMAT),
                'title': record_object.title,
                'url': record_object.url,
                'state': record_object.state.value,
                'digest_number': record_object.digest_number,
                'category': record_object.category.value,
                'subcategory': record_object.subcategory.value if record_object.subcategory is not None else None,
            }
            records_plain.append(record_plain)
        with open(yaml_path, 'w') as fout:
            print(f'{PRINT_PREFIX}Saving results to "{yaml_path}"')
            yaml.safe_dump(records_plain, fout)

    def load_from_file(self, file_path: str):
        if '.html' in file_path:
            self.load_from_html(file_path)
        elif '.yaml' in file_path or '.yml' in file_path:
            self.load_from_yaml(file_path)
        else:
            raise NotImplementedError

    def load_from_yaml(self, yaml_path: str):
        records_objects: List[DigestRecord] = []
        print(f'{PRINT_PREFIX}Loading input data from "{yaml_path}"')
        with open(yaml_path, 'r') as fin:
            fin_data = yaml.safe_load(fin)
            for record_plain in fin_data:
                category = DigestRecordCategory(record_plain['category'])
                subcategory_str = record_plain['subcategory']
                if category == DigestRecordCategory.SHORTS:
                    subcategory = DigestRecordShortsSubCategory(subcategory_str)
                elif category == DigestRecordCategory.RELEASES:
                    subcategory = DigestRecordReleasesSubcategory(subcategory_str)
                else:
                    subcategory = None
                record_object = DigestRecord(datetime.datetime.strptime(record_plain['datetime'],
                                                                        DIGEST_RECORD_DATETIME_FORMAT),
                                             record_plain['title'],
                                             record_plain['url'],
                                             DigestRecordState(record_plain['state']),
                                             record_plain['digest_number'],
                                             category,
                                             subcategory)
                records_objects.append(record_object)
        self.records = records_objects

    def load_from_html(html_path):
        records_objects: List[DigestRecord] = []
        with open(html_path, 'r') as fin:
            html_content_str = fin.read()
            re_str = r'(\d{4}.+)([-+]\d{2}:\d{2}) (.+?) <a href="(.+?)">'
            re_res = re.findall(re_str, html_content_str)
            if re_res:
                for record in re_res:
                    dt = datetime.datetime.strptime(f'{record[0]} {record[1].replace(":", "")}',
                                                    DIGEST_RECORD_DATETIME_FORMAT)
                    title = record[2].strip()
                    url = record[3]
                    record_object = DigestRecord(dt, title, url)
                    records_objects.append(record_object)
        self.records = records_objects

    def categorize_interactively(self):
        current_digest_number = None
        self._filtered_records = []
        for record in self.records:
            if record.state == DigestRecordState.UNKNOWN:
                self._filtered_records.append(record)
                continue
            if record.state == DigestRecordState.IN_DIGEST:
                if record.digest_number is None:
                    self._filtered_records.append(record)
                    continue
                if record.category == DigestRecordCategory.UNKNOWN:
                    self._filtered_records.append(record)
                    continue
                if record.subcategory is None:
                    if record.category == DigestRecordCategory.SHORTS \
                            or record.category == DigestRecordCategory.RELEASES:
                        self._filtered_records.append(record)
                        continue
        print(f'{PRINT_PREFIX}{len(self._filtered_records)} record(s) left to process')
        print()
        records_left_to_process = len(self._filtered_records)
        for record in self.records:
            # TODO: Rewrite using FSM
            print(f'{PRINT_PREFIX}Processing record "{record.title}" from date {record.dt}:\n{record}')
            if record.state == DigestRecordState.UNKNOWN:
                record.state = self._ask_state(record)
            if record.state == DigestRecordState.IN_DIGEST:
                if record.digest_number is None:
                    if current_digest_number is None:
                        record.digest_number = self._ask_digest_number(record)
                        current_digest_number = record.digest_number
                    else:
                        record.digest_number = current_digest_number
                if record.category == DigestRecordCategory.UNKNOWN:
                    record.category = self._ask_category(record)
                if record.subcategory is None:
                    if record.category == DigestRecordCategory.SHORTS \
                            or record.category == DigestRecordCategory.RELEASES:
                        record.subcategory = self._ask_subcategory(record)
            self._make_backup()
            if record in self._filtered_records:
                records_left_to_process -= 1
                if records_left_to_process > 0:
                    print(f'{PRINT_PREFIX}{records_left_to_process} record(s) left to process')

    def _ask_state(self, record: DigestRecord):
        return self._ask_enum('digest record state', DigestRecordState, record)

    def _ask_digest_number(self, record: DigestRecord):
        while True:
            digest_number_str = input(f'{PRINT_PREFIX}Please input digest number for "{record.title}": ')
            if digest_number_str.isnumeric():
                digest_number = int(digest_number_str)
                print(f'{PRINT_PREFIX}Setting digest number of record "{record.title}" to {digest_number}')
                print()
                return digest_number
            else:
                print('Invalid digest number, it should be integer')
        raise NotImplementedError

    def _ask_category(self, record: DigestRecord):
        return self._ask_enum('digest record category', DigestRecordCategory, record)

    def _ask_subcategory(self, record: DigestRecord):
        enum_name = 'digest record subcategory'
        if record.category == DigestRecordCategory.SHORTS:
            return self._ask_enum(enum_name, DigestRecordShortsSubCategory, record)
        elif record.category == DigestRecordCategory.RELEASES:
            return self._ask_enum(enum_name, DigestRecordReleasesSubcategory, record)
        else:
            raise NotImplementedError

    def _ask_enum(self, enum_name, enum_class, record: DigestRecord):
        while True:
            print(f'{PRINT_PREFIX}Waiting for {enum_name}')
            print(f'{PRINT_PREFIX}Available values:')
            enum_options_values = [enum_variant.value for enum_variant in enum_class]
            for enum_option_value_i, enum_option_value in enumerate(enum_options_values):
                print(f'{enum_option_value_i + 1}. {enum_option_value}')
            enum_value_index_str = input(f'{PRINT_PREFIX}Please input index of {enum_name} for "{record.title}": ')
            if enum_value_index_str.isnumeric():
                enum_value_index = int(enum_value_index_str)
                if 0 <= enum_value_index <= len(enum_options_values):
                    try:
                        enum_value = enum_options_values[enum_value_index - 1]
                        enum_obj = enum_class(enum_value)
                        print(f'{PRINT_PREFIX}Setting {enum_name} of record "{record.title}" to "{enum_obj.value}"')
                        print()
                        return enum_obj
                    except ValueError:
                        print(f'Invalid {enum_name} value "{enum_value}"')
                        continue
                else:
                    print(f'Invalid index, it should be positive and not more than {len(enum_options_values)}')
                    continue
            else:
                print('Invalid index, it should be integer')
                continue
        raise NotImplementedError

    def _make_backup(self):
        current_datetime_stamp_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_path = f'backups/{current_datetime_stamp_str}.yaml'
        self.save_to_yaml(backup_path)


def parse_command_line_args():
    parser = argparse.ArgumentParser(
                        description='FOSS News Client')
    parser.add_argument('SOURCE',
                        help='Source file (HTML or YAML)')
    parser.add_argument('DESTINATION',
                        help='Destination file (YAML)')
    args = parser.parse_args()
    return args


def main():
    args = parse_command_line_args()
    source_path = args.SOURCE
    destination_path = args.DESTINATION
    records_collection = DigestRecordsCollection()
    records_collection.load_from_file(source_path)
    records_collection.categorize_interactively()
    records_collection.save_to_yaml(destination_path)


if __name__ == "__main__":
    sys.exit(main())
