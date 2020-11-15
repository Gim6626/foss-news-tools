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
from typing import List, Dict
import os
from pprint import (
    pformat,
    pprint,
)


SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
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


RUSSIAN_SOURCES = (
    'habr.com',
    'opennet.ru',
    'cnews.ru',
    'vk.com',
    'pingvinus.ru',
    'losst.ru',
    'linux.org.ru',
    'youtube.com',  # Confusing, yes, but currently we use videos from only one blogger and he is russian
)


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
            41: 'https://habr.com/ru/post/526986/',
            42: 'https://habr.com/ru/post/528132/',
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
        self._posts_count = 43

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


DIGEST_RECORD_CATEGORY_RU_MAPPING = {
    'unknown': 'Неизвестно',
    'news': 'Новости',
    'articles': 'Статьи',
    'releases': 'Релизы',
    'other': 'Прочее',
}


DIGEST_RECORD_CATEGORY_VALUES = [category.value for category in DigestRecordCategory]


class DigestRecordSubcategory(Enum):
    EVENTS = 'events'
    INTROS = 'intros'
    OPENING = 'opening'
    NEWS = 'news'
    DIY = 'diy'
    LAW = 'law'
    KnD = 'knd'
    SYSTEM = 'system'
    SPECIAL = 'special'
    MULTIMEDIA = 'multimedia'
    SECURITY = 'security'
    DEVOPS = 'devops'
    DATA_SCIENCE = 'data_science'
    WEB = 'web'
    DEV = 'dev'
    MANAGEMENT = 'management'
    USER = 'user'
    GAMES = 'games'
    HARDWARE = 'hardware'
    MISC = 'misc'


DIGEST_RECORD_SUBCATEGORY_RU_MAPPING = {
    'events': 'Мероприятия',
    'intros': 'Внедрения',
    'opening': 'Открытие кода и данных',
    'news': 'Новости FOSS организаций',
    'diy': 'DIY',
    'law': 'Юридические вопросы',
    'knd': 'Ядро и дистрибутивы',
    'system': 'Системное',
    'special': 'Специальное',
    'db': 'Базы данных',
    'multimedia': 'Мультимедиа',
    'security': 'Безопасность',
    'devops': 'DevOps',
    'data_science': 'AI & Data Science',
    'web': 'Web',
    'dev': 'Для разработчиков',
    'history': 'История',
    'management': 'Менеджмент',
    'user': 'Пользовательское',
    'games': 'Игры',
    'hardware': 'Железо',
    'misc': 'Разное',
}


DIGEST_RECORD_SUBCATEGORY_VALUES = [category.value for category in DigestRecordSubcategory]


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
            'state': self.state.value if self.state is not None else None,
            'digest_number': self.digest_number,
            'category': self.category.value if self.category is not None else None,
            'subcategory': self.subcategory.value if self.subcategory is not None else None,
        }


class DigestRecordsCollection:

    def __init__(self,
                 records: List[DigestRecord] = None):
        self.records = records if records is not None else []
        self._filtered_records = []
        self._host = None
        self._port = None
        self._user = None
        self._password = None
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
                'state': record_object.state.value if record_object.state is not None else None,
                'is_main': record_object.is_main,
                'digest_number': record_object.digest_number,
                'category': record_object.category.value if record_object.category is not None else None,
                'subcategory': record_object.subcategory.value if record_object.subcategory is not None else None,
            }
            records_plain.append(record_plain)
        with open(yaml_path, 'w') as fout:
            logger.info(f'Saving results to "{yaml_path}"')
            yaml.safe_dump(records_plain, fout)

    def _login(self):
        logger.info('Logging in')
        result = requests.post(f'http://{self._host}:{self._port}/api/v1/token/',
                               data={'username': self._user, 'password': self._password})
        if result.status_code != 200:
            raise Exception(f'Invalid response code from FNGS login - {result.status_code}: {result.content.decode("utf-8")}')
        result_data = json.loads(result.content)
        self._token = result_data['access']
        logger.info('Logged in')

    def _load_config(self, config_path):
        logger.info(f'Loading gathering server connect data from config "{config_path}"')
        with open(config_path, 'r') as fin:
            config_data = yaml.safe_load(fin)
            self._host = config_data['host']
            self._port = config_data['port']
            self._user = config_data['user']
            self._password = config_data['password']
            logger.info('Loaded')

    def load_specific_digest_records_from_server(self, yaml_config_path: str, digest_number):
        self._load_config(yaml_config_path)
        self._login()
        self._basic_load_digest_records_from_server(yaml_config_path,
                                                    f'http://{self._host}:{self._port}/api/v1/specific-digest-records/?digest_number={digest_number}')

    def load_new_digest_records_from_server(self, yaml_config_path: str):
        self._load_config(yaml_config_path)
        self._login()
        self._basic_load_digest_records_from_server(yaml_config_path,
                                                    f'http://{self._host}:{self._port}/api/v1/new-digest-records/')

    def _basic_load_digest_records_from_server(self, yaml_config_path: str, url: str):
        records_objects: List[DigestRecord] = []
        logger.info('Getting data')
        result = requests.get(url,
                              headers={
                                  'Authorization': f'Bearer {self._token}',
                                  'Content-Type': 'application/json',
                              })
        if result.status_code != 200:
            raise Exception(
                f'Invalid response code from FNGS fetch - {result.status_code}: {result.content.decode("utf-8")}')
        logger.info('Got data')
        result_data = json.loads(result.content)
        for record_plain in result_data:
            record_object = DigestRecord(datetime.datetime.strptime(record_plain['dt'],
                                                                    '%Y-%m-%dT%H:%M:%SZ'),
                                         record_plain['title'],
                                         record_plain['url'],
                                         digest_number=record_plain['digest_number'],
                                         drid=record_plain['id'],
                                         is_main=record_plain['is_main'])
            record_object.state = DigestRecordState(record_plain['state'].lower()) if 'state' in record_plain and record_plain['state'] is not None else None
            record_object.category = DigestRecordCategory(record_plain['category'].lower()) if 'category' in record_plain and record_plain['category'] is not None else None
            record_object.subcategory = DigestRecordSubcategory(record_plain['subcategory'].lower()) if 'subcategory' in record_plain and record_plain['subcategory'] is not None else None
            records_objects.append(record_object)
        self.records = records_objects

    def _clear_title(self, title: str):
        return re.sub(r'^\[.+\]\s+', '', title)

    def _check_url_if_english(self, url):
        for russian_source in RUSSIAN_SOURCES:
            if russian_source in url:
                return False
        return True

    def records_to_html(self, html_path):
        output_records = {
            'main': [],
            DigestRecordCategory.NEWS.value: {subcategory_value: [] for subcategory_value in DIGEST_RECORD_SUBCATEGORY_VALUES},
            DigestRecordCategory.ARTICLES.value: {subcategory_value: [] for subcategory_value in DIGEST_RECORD_SUBCATEGORY_VALUES},
            DigestRecordCategory.RELEASES.value: {subcategory_value: [] for subcategory_value in DIGEST_RECORD_SUBCATEGORY_VALUES},
            DigestRecordCategory.OTHER.value: [],
        }
        for digest_record in self.records:
            if digest_record.state != DigestRecordState.IN_DIGEST:
                continue
            if digest_record.is_main:
                output_records['main'].append(digest_record)
            elif digest_record.category == DigestRecordCategory.OTHER:
                output_records[digest_record.category.value].append(digest_record)
            elif not digest_record.is_main and digest_record.category in (DigestRecordCategory.NEWS,
                                                                          DigestRecordCategory.ARTICLES,
                                                                          DigestRecordCategory.RELEASES):
                if digest_record.subcategory is not None:
                    output_records[digest_record.category.value][digest_record.subcategory.value].append(digest_record)
            else:
                print(digest_record.title, digest_record.category, digest_record.is_main)
                raise NotImplementedError
        output = '<h2>Главное</h2>\n\n'
        for main_record in output_records['main']:
            output += f'<h3>{self._clear_title(main_record.title)}</h3>\n\n'
            output += f'<i><b>Категория</b>: {DIGEST_RECORD_CATEGORY_RU_MAPPING[main_record.category.value]}/{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[main_record.subcategory.value]}</i><br>\n\n'
            output += f'Подробности - <a href="{main_record.url}">{main_record.url}</a>{" (en)" if self._check_url_if_english(main_record.url) else ""}\n\n'

        output += '<h2>Короткой строкой</h2>\n\n'

        # TODO: Refactor following 3 loops, unite them in one upper
        output += f'<h3>{DIGEST_RECORD_CATEGORY_RU_MAPPING[DigestRecordCategory.NEWS.value]}</h3>\n\n'
        for news_record_subcategory, news_records in output_records[DigestRecordCategory.NEWS.value].items():
            if not news_records:
                continue
            output += f'<h4>{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[news_record_subcategory]}</h4>\n\n'
            for news_record in news_records:
                output += f'{self._clear_title(news_record.title)} <a href={news_record.url}>{news_record.url}</a>{" (en)" if self._check_url_if_english(news_record.url) else ""}<br>\n'

        output += f'<h3>{DIGEST_RECORD_CATEGORY_RU_MAPPING[DigestRecordCategory.ARTICLES.value]}</h3>\n\n'
        for articles_record_subcategory, articles_records in output_records[DigestRecordCategory.ARTICLES.value].items():
            if not articles_records:
                continue
            output += f'<h4>{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[articles_record_subcategory]}</h4>\n\n'
            for articles_record in articles_records:
                output += f'{self._clear_title(articles_record.title)} <a href={articles_record.url}>{articles_record.url}</a>{" (en)" if self._check_url_if_english(articles_record.url) else ""}<br>\n'

        output += f'<h3>{DIGEST_RECORD_CATEGORY_RU_MAPPING[DigestRecordCategory.RELEASES.value]}</h3>\n\n'
        for releases_record_subcategory, releases_records in output_records[DigestRecordCategory.RELEASES.value].items():
            if not releases_records:
                continue
            output += f'<h4>{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[releases_record_subcategory]}</h4>\n\n'
            for releases_record in releases_records:
                output += f'{self._clear_title(releases_record.title)} <a href={releases_record.url}>{releases_record.url}</a>{" (en)" if self._check_url_if_english(releases_record.url) else ""}<br>\n'

        output += '<h2>Что ещё посмотреть</h2>\n\n'
        for other_record in output_records[DigestRecordCategory.OTHER.value]:
            output += f'{self._clear_title(other_record.title)} <a href="{other_record.url}">{other_record.url}</a>{" (en)" if self._check_url_if_english(other_record.url) else ""}<br>\n'

        with open(html_path, 'w') as fout:
            logger.info(f'Saving output to "{html_path}"')
            fout.write(output)

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
            if record.state == DigestRecordState.IN_DIGEST:
                if record.is_main is None:
                    record.is_main = self._ask_bool(record)
                if record.digest_number is None:
                    if current_digest_number is None:
                        record.digest_number = self._ask_digest_number(record)
                        current_digest_number = record.digest_number
                    else:
                        record.digest_number = current_digest_number
                if record.category == DigestRecordCategory.UNKNOWN or record.category is None:
                    record.category = self._ask_category(record,
                                                         DIGEST_RECORD_CATEGORY_RU_MAPPING)
                if record.subcategory is None:
                    if record.category != DigestRecordCategory.OTHER:
                        record.subcategory = self._ask_subcategory(record,
                                                                   DIGEST_RECORD_SUBCATEGORY_RU_MAPPING)
            self._make_backup()
            if record in self._filtered_records:
                records_left_to_process -= 1
                if records_left_to_process > 0:
                    logger.info(f'{records_left_to_process} record(s) left to process')

            logger.info(f'Uploading record #{record.drid} to FNGS')
            result = requests.patch(f'http://{self._host}:{self._port}/api/v1/digest-records/{record.drid}/',
                                    data=json.dumps({
                                        'id': record.drid,
                                        'state': record.state.name if record.state is not None else None,
                                        'digest_number': record.digest_number,
                                        'is_main': record.is_main,
                                        'category': record.category.name if record.category is not None else None,
                                        'subcategory': record.subcategory.name if record.subcategory is not None else None,
                                    }),
                                    headers={
                                        'Authorization': f'Bearer {self._token}',
                                        'Content-Type': 'application/json',
                                    })
            if result.status_code != 200:
                raise Exception(f'Invalid response code from FNGS patch - {result.status_code}: {result.content.decode("utf-8")}')
            logger.info(f'Uploaded record #{record.drid} to FNGS')

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

    def _ask_category(self,
                      record: DigestRecord,
                      translations: Dict[str, str] = None):
        return self._ask_enum('digest record category', DigestRecordCategory, record, translations)

    def _ask_subcategory(self,
                         record: DigestRecord,
                         translations: Dict[str, str] = None):
        enum_name = 'digest record subcategory'
        if record.category != DigestRecordCategory.UNKNOWN and record.category != DigestRecordCategory.OTHER:
            return self._ask_enum(enum_name, DigestRecordSubcategory, record, translations)
        else:
            raise NotImplementedError

    def _ask_enum(self,
                  enum_name,
                  enum_class,
                  record: DigestRecord,
                  translations: Dict[str, str] = None):
        while True:
            logger.info(f'Waiting for {enum_name}')
            logger.info('Available values:')
            enum_options_values = [enum_variant.value for enum_variant in enum_class]
            for enum_option_value_i, enum_option_value in enumerate(enum_options_values):
                enum_option_value_mod = translations[enum_option_value] if translations is not None else enum_option_value
                print(f'{enum_option_value_i + 1}. {enum_option_value_mod}')
            enum_value_index_str = input(f'Please input index of {enum_name} for "{record.title}": ')
            if enum_value_index_str.isnumeric():
                enum_value_index = int(enum_value_index_str)
                if 0 <= enum_value_index <= len(enum_options_values):
                    try:
                        enum_value = enum_options_values[enum_value_index - 1]
                        enum_obj = enum_class(enum_value)
                        enum_obj_value_mod = translations[enum_obj.value] if translations is not None else enum_obj.value
                        logger.info(f'Setting {enum_name} of record "{record.title}" to "{enum_obj_value_mod}"')
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
        backup_dir_name = 'backups'
        backup_dir_path = os.path.join(SCRIPT_DIRECTORY,
                                       backup_dir_name)
        if not os.path.exists(backup_dir_path):
            os.mkdir(backup_dir_path)
        current_datetime_stamp_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_path = os.path.join(backup_dir_path,
                                   f'{current_datetime_stamp_str}.yaml')
        self.save_to_yaml(backup_path)
