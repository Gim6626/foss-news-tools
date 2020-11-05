import sys
import time
from abc import (
    ABCMeta,
    abstractmethod,
)
import requests
import logging
import re
import datetime
import yaml
import json
from enum import Enum
from typing import List
from pprint import (
    pformat,
    pprint,
)


DIGEST_RECORD_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'

days_count = None

LOGGING_SETTINGS = {
    'level': logging.INFO,
    'format': '[%(asctime)s] %(levelname)s: %(message)s',
    'stream': sys.stderr,
}

logging.basicConfig(**LOGGING_SETTINGS)

logger = logging.getLogger('fntools')
logging.getLogger("requests").setLevel(logging.WARNING)


class BasicPostsStatisticsGetter(metaclass=ABCMeta):

    def __init__(self):
        self._posts_urls = {}
        self.source_name = None

    def posts_statistics(self):
        posts_statistics = {}
        for number, url in self.posts_urls.items():
            views_count = self.post_statistics(number, url)
            posts_statistics[number] = views_count
            logger.info(f'Views count for {self.source_name} post #{number} ({url}): {views_count}')
            time.sleep(1)
        return posts_statistics

    @abstractmethod
    def post_statistics(self, number, url):
        pass

    @property
    def posts_urls(self):
        return self._posts_urls


class HabrPostsStatisticsGetter(BasicPostsStatisticsGetter):

    def __init__(self):
        super().__init__()
        self.source_name = 'Habr'
        self._posts_urls = {
            1: 'https://habr.com/ru/post/486178/',
            2: 'https://habr.com/ru/post/487662/',
            3: 'https://habr.com/ru/post/488590/',
            4: 'https://habr.com/ru/post/489632/',
            5: 'https://habr.com/ru/post/490594/',
            6: 'https://habr.com/ru/post/491562/',
            7: 'https://habr.com/ru/post/492440/',
            8: 'https://habr.com/ru/post/493780/',
            9: 'https://habr.com/ru/post/494682/',
            10: 'https://habr.com/ru/post/495782/',
            11: 'https://habr.com/ru/post/496858/',
            12: 'https://habr.com/ru/post/498026/',
            13: 'https://habr.com/ru/post/499166/',
            14: 'https://habr.com/ru/post/500248/',
            15: 'https://habr.com/ru/post/501336/',
            16: 'https://habr.com/ru/post/502414/',
            17: 'https://habr.com/ru/post/503598/',
            18: 'https://habr.com/ru/post/504710/',
            19: 'https://habr.com/ru/post/505706/',
            20: 'https://habr.com/ru/post/506624/',
            21: 'https://habr.com/ru/post/507590/',
            22: 'https://habr.com/ru/post/508632/',
            23: 'https://habr.com/ru/post/509660/',
            24: 'https://habr.com/ru/post/510636/',
            25: 'https://habr.com/ru/post/511610/',
            26: 'https://habr.com/ru/post/512552/',
            27: 'https://habr.com/ru/post/513652/',
            28: 'https://habr.com/ru/post/514434/',
            29: 'https://habr.com/ru/post/515372/',
            30: 'https://habr.com/ru/post/516292/',
            31: 'https://habr.com/ru/post/517138/',
            32: 'https://habr.com/ru/post/518010/',
            33: 'https://habr.com/ru/post/518942/',
            34: 'https://habr.com/ru/post/519914/',
            35: 'https://habr.com/ru/post/520718/',
            36: 'https://habr.com/ru/post/522160/',
            37: 'https://habr.com/ru/post/522958/',
            38: 'https://habr.com/ru/post/523978/',
            39: 'https://habr.com/ru/post/524968/',
            40: 'https://habr.com/ru/post/526014/',
        }

    def post_statistics(self, number, url):
        response = requests.get(url)
        content = response.text
        re_result = re.search('<span class="post-stats__views-count">(.*?)</span>', content)
        if re_result is None:
            logger.error(f'Failed to find statistics in FOSS News #{number} ({url}) on Habr')
            return None

        full_statistics_str = re_result.group(1)
        logger.debug(f'Full statistics string for FOSS News #{number}: "{full_statistics_str}"')
        re_result = re.fullmatch(r'((\d+)(,(\d+))?)k?', full_statistics_str)
        if re_result is None:
            logger.error(f'Invalid statistics format in FOSS News #{number} ({url}) on Habr')
            return None

        statistics_without_k = re_result.group(1)
        statistics_before_comma = re_result.group(2)
        statistics_after_comma = re_result.group(4)

        if 'k' in full_statistics_str:
            views_count = int(statistics_before_comma) * 1000
            if statistics_after_comma is not None:
                views_count += int(statistics_after_comma) * 100
        else:
            views_count = int(statistics_without_k)

        return views_count


class VkPostsStatisticsGetter(BasicPostsStatisticsGetter):

    def __init__(self):
        super().__init__()
        self.source_name = 'VK'
        self._posts_urls = {}
        self._posts_count = 41

    @property
    def posts_urls(self):
        if self._posts_urls == {}:
            for i in range(self._posts_count):
                self._posts_urls[i] = f'https://vk.com/@permlug-foss-news-{i}'
        return self._posts_urls

    def post_statistics(self, number, url):
        response = requests.get(url)
        content = response.text
        re_result = re.search(r'<div class="articleView__views_info">(\d+) просмотр', content)
        if re_result is None:
            logger.error(f'Failed to find statistics in FOSS News #{number} ({url}) on VK')
            return None
        return int(re_result.group(1))


class DigestRecordState(Enum):
    UNKNOWN = 'unknown'
    IN_DIGEST = 'in_digest'
    IGNORED = 'ignored'


DIGEST_RECORD_STATE_VALUES = [state.value for state in DigestRecordState]


class DigestRecordCategory(Enum):
    UNKNOWN = 'unknown'
    NEWS = 'news'
    ARTICLES = 'articles'
    RELEASES = 'releases'
    OTHER = 'other'


DIGEST_RECORD_CATEGORY_VALUES = [category.value for category in DigestRecordCategory]


class DigestRecordSubCategory(Enum):
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


DIGEST_RECORD_SHORTS_SUBCATEGORY_VALUES = [category.value for category in DigestRecordSubCategory]


class DigestRecord:

    def __init__(self,
                 dt: datetime.datetime,
                 title: str,
                 url: str,
                 state: DigestRecordState = DigestRecordState.UNKNOWN,
                 digest_number: int = None,
                 category: DigestRecordCategory = DigestRecordCategory.UNKNOWN,
                 subcategory: Enum = None,
                 drid: int = None,
                 is_main: bool = None):
        self.dt = dt
        self.title = title
        self.url = url
        self.state = state
        self.digest_number = digest_number
        self.category = category
        self.subcategory = subcategory
        self.drid = drid
        self.is_main = is_main

    def __str__(self):
        return pformat(self.to_dict())

    def to_dict(self):
        return {
            'drid': self.drid,
            'datetime': self.dt.strftime(DIGEST_RECORD_DATETIME_FORMAT),
            'title': self.title,
            'url': self.url,
            'is_main': self.is_main,
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
        self._host = None
        self._port = None
        self._token = None

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
                'is_main': record_object.is_main,
                'digest_number': record_object.digest_number,
                'category': record_object.category.value,
                'subcategory': record_object.subcategory.value if record_object.subcategory is not None else None,
            }
            records_plain.append(record_plain)
        with open(yaml_path, 'w') as fout:
            logger.info(f'Saving results to "{yaml_path}"')
            yaml.safe_dump(records_plain, fout)

    def load(self, file_path: str):
        if '.conf.yaml' in file_path:
            self.load_from_server(file_path)
        elif '.html' in file_path:
            self.load_from_html(file_path)
        elif '.yaml' in file_path or '.yml' in file_path:
            self.load_from_yaml(file_path)
        else:
            raise NotImplementedError

    def load_from_server(self, yaml_config_path: str):
        records_objects: List[DigestRecord] = []
        logger.info(f'Loading gathering server connect data from config "{yaml_config_path}"')
        with open(yaml_config_path, 'r') as fin:
            config_data = yaml.safe_load(fin)
            # pprint(config_data)
            self._host = config_data['host']
            self._port = config_data['port']
            user = config_data['user']
            password = config_data['password']
            logger.info('Loaded')
            logger.info('Logging in')
            result = requests.post(f'http://{self._host}:{self._port}/api/v1/token/',
                                   data={'username': user, 'password': password})
            if result.status_code != 200:
                raise Exception(f'Invalid response code from FNGS login - {result.status_code}: {result.content.decode("utf-8")}')
            result_data = json.loads(result.content)
            self._token = result_data['access']
            logger.info('Logged in')
            logger.info('Getting data')
            result = requests.get(f'http://{self._host}:{self._port}/api/v1/new-digest-records/',
                                  headers={
                                      'Authorization': f'Bearer {self._token}',
                                      'Content-Type': 'application/json',
                                  })
            if result.status_code != 200:
                raise Exception(f'Invalid response code from FNGS fetch - {result.status_code}: {result.content.decode("utf-8")}')
            logger.info('Got data')
            result_data = json.loads(result.content)
            for record_plain in result_data:
                record_object = DigestRecord(datetime.datetime.strptime(record_plain['dt'],
                                                                        '%Y-%m-%dT%H:%M:%SZ'),
                                             record_plain['title'],
                                             record_plain['url'],
                                             drid=record_plain['id'],
                                             is_main=record_plain['is_main'])
                records_objects.append(record_object)
            self.records = records_objects

    def load_from_yaml(self, yaml_path: str):
        records_objects: List[DigestRecord] = []
        logger.info(f'Loading input data from "{yaml_path}"')
        with open(yaml_path, 'r') as fin:
            fin_data = yaml.safe_load(fin)
            for record_plain in fin_data:
                category = DigestRecordCategory(record_plain['category'])
                subcategory_str = record_plain['subcategory']
                if category != DigestRecordCategory.OTHER and category != DigestRecordCategory.UNKNOWN:
                    subcategory = DigestRecordSubCategory(subcategory_str)
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

    def load_from_html(self, html_path):
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
            if record.is_main is None:
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
                    if record.category != DigestRecordCategory.OTHER:
                        self._filtered_records.append(record)
                        continue
        logger.info(f'{len(self._filtered_records)} record(s) left to process')
        records_left_to_process = len(self._filtered_records)
        for record in self.records:
            # TODO: Rewrite using FSM
            logger.info(f'Processing record "{record.title}" from date {record.dt}:\n{record}')
            if record.state == DigestRecordState.UNKNOWN:
                record.state = self._ask_state(record)
            if record.is_main is None:
                record.is_main = self._ask_bool(record)
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
                    if record.category != DigestRecordCategory.OTHER:
                        record.subcategory = self._ask_subcategory(record)
            self._make_backup()
            if record in self._filtered_records:
                records_left_to_process -= 1
                if records_left_to_process > 0:
                    logger.info(f'{records_left_to_process} record(s) left to process')
        if self._token is not None:
            logger.info('Uploading categorized results to FNGS')
            for record in self.records:
                result = requests.patch(f'http://{self._host}:{self._port}/api/v1/digest-records/{record.drid}/',
                                        data=json.dumps({
                                            'id': record.drid,
                                            'state': record.state.name,
                                            'digest_number': record.digest_number,
                                            'is_main': record.is_main,
                                            'category': record.category.name,
                                            'subcategory': record.subcategory.name,
                                        }),
                                        headers={
                                            'Authorization': f'Bearer {self._token}',
                                            'Content-Type': 'application/json',
                                        })
                if result.status_code != 200:
                    raise Exception(f'Invalid response code from FNGS patch - {result.status_code}: {result.content.decode("utf-8")}')
                logger.info(f'Uploaded record #{record.drid}')
            logger.info('Uploaded categorized results to FNGS')

    def _ask_state(self, record: DigestRecord):
        return self._ask_enum('digest record state', DigestRecordState, record)

    def _ask_digest_number(self, record: DigestRecord):
        while True:
            digest_number_str = input(f'Please input digest number for "{record.title}": ')
            if digest_number_str.isnumeric():
                digest_number = int(digest_number_str)
                logger.info(f'Setting digest number of record "{record.title}" to {digest_number}')
                return digest_number
            else:
                print('Invalid digest number, it should be integer')
        raise NotImplementedError

    def _ask_bool(self, record: DigestRecord):
        while True:
            bool_str = input(f'Please input whether or no "{record.title}" is main (y/n): ')
            if bool_str == 'y':
                return True
            elif bool_str == 'n':
                return False
            else:
                print('Invalid boolean, it should be "y" or "n"')
        raise NotImplementedError

    def _ask_category(self, record: DigestRecord):
        return self._ask_enum('digest record category', DigestRecordCategory, record)

    def _ask_subcategory(self, record: DigestRecord):
        enum_name = 'digest record subcategory'
        if record.category != DigestRecordCategory.UNKNOWN and record.category != DigestRecordCategory.OTHER:
            return self._ask_enum(enum_name, DigestRecordSubCategory, record)
        else:
            raise NotImplementedError

    def _ask_enum(self, enum_name, enum_class, record: DigestRecord):
        while True:
            logger.info(f'Waiting for {enum_name}')
            logger.info('Available values:')
            enum_options_values = [enum_variant.value for enum_variant in enum_class]
            for enum_option_value_i, enum_option_value in enumerate(enum_options_values):
                print(f'{enum_option_value_i + 1}. {enum_option_value}')
            enum_value_index_str = input(f'Please input index of {enum_name} for "{record.title}": ')
            if enum_value_index_str.isnumeric():
                enum_value_index = int(enum_value_index_str)
                if 0 <= enum_value_index <= len(enum_options_values):
                    try:
                        enum_value = enum_options_values[enum_value_index - 1]
                        enum_obj = enum_class(enum_value)
                        logger.info(f'Setting {enum_name} of record "{record.title}" to "{enum_obj.value}"')
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