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
import html

from data.russiansources import *
from data.releaseskeywords import *
from data.habrposts import *
from data.digestrecordcategory import *
from data.digestrecordstate import *
from data.digestrecordsubcategory import *


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


class BasicPostsStatisticsGetter(metaclass=ABCMeta):

    GET_TIMEOUT_SECONDS = 30
    SLEEP_BETWEEN_ATTEMPTS_SECONDS = 5
    GET_ATTEMPTS = 5

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

    def _get_with_retries(self, url):
        for attempt_i in range(self.GET_ATTEMPTS):
            try:
                response = requests.get(url, timeout=self.GET_TIMEOUT_SECONDS)
                return response
            except requests.exceptions.ReadTimeout:
                base_timeout_msg = f'Fetching {url} timeout of {self.GET_TIMEOUT_SECONDS} seconds exceeded'
                if attempt_i != self.GET_ATTEMPTS - 1:
                    logger.error(f'{base_timeout_msg}, sleeping {self.SLEEP_BETWEEN_ATTEMPTS_SECONDS} seconds and trying again, {self.GET_ATTEMPTS - attempt_i - 1} retries left')
                    time.sleep(self.SLEEP_BETWEEN_ATTEMPTS_SECONDS)
                else:
                    raise Exception(f'{base_timeout_msg}, retries count {self.GET_ATTEMPTS} exceeded')

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
        self._posts_urls = HABR_POSTS

    def post_statistics(self, number, url):
        response = self._get_with_retries(url)
        content = response.text
        re_result = re.search('<span class="post-stats__views-count">(.*?)</span>', content)
        if re_result is None:
            logger.warning(f'Failed to parse views count in FOSS News #{number} ({url}) on Habr, trying another format')
            re_result = re.search('<span class="tm-icon-counter__value">(.*?)</span>', content)
            if re_result is None:
                logger.error(f'Failed to find statistics in FOSS News #{number} ({url}) on Habr')
                return None

        full_statistics_str = re_result.group(1)
        logger.debug(f'Full statistics string for FOSS News #{number}: "{full_statistics_str}"')
        re_result = re.fullmatch(r'((\d+)([\.,](\d+))?)[Kk]?', full_statistics_str)
        if re_result is None:
            logger.error(f'Invalid statistics format in FOSS News #{number} ({url}) on Habr: {full_statistics_str}')
            return None

        statistics_without_k = re_result.group(1)
        statistics_before_comma = re_result.group(2)
        statistics_after_comma = re_result.group(4)

        if 'K' in full_statistics_str or 'k' in full_statistics_str:
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
        self._posts_count = 1

    @property
    def posts_urls(self):
        if self._posts_urls == {}:
            for i in range(self._posts_count):
                self._posts_urls[i] = f'https://vk.com/@permlug-foss-news-{i}'
        return self._posts_urls

    def post_statistics(self, number, url):
        response = self._get_with_retries(url)
        content = response.text
        re_result = re.search(r'<div class="articleView__views_info">(\d+) просмотр', content)
        if re_result is None:
            logger.error(f'Failed to find statistics in FOSS News #{number} ({url}) on VK')
            return None
        return int(re_result.group(1))


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
                 is_main: bool = None,
                 keywords: List[str] = None):
        self.dt = dt
        self.title = title
        self.url = url
        self.state = state
        self.digest_number = digest_number
        self.category = category
        self.subcategory = subcategory
        self.drid = drid
        self.is_main = is_main
        self.keywords = keywords

    def __str__(self):
        return pformat(self.to_dict())

    def to_dict(self):
        return {
            'drid': self.drid,
            'datetime': self.dt.strftime(DIGEST_RECORD_DATETIME_FORMAT) if self.dt is not None else None,
            'title': self.title,
            'url': self.url,
            'is_main': self.is_main,
            'state': self.state.value if self.state is not None else None,
            'digest_number': self.digest_number,
            'category': self.category.value if self.category is not None else None,
            'subcategory': self.subcategory.value if self.subcategory is not None else None,
            'keywords': self.keywords,
        }


# TODO: Refactor
class DigestRecordsCollection:

    def __init__(self,
                 records: List[DigestRecord] = None):
        self.records = records if records is not None else []
        self.duplicates = []
        self._filtered_records = []
        self._host = None
        self._port = None
        self._user = None
        self._password = None
        self._token = None

    def __str__(self):
        return pformat([record.to_dict() for record in self.records])

    @property
    def _subcategories_keywords(self) -> Dict:
        subcategories_keywords_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                   'data',
                                                   'digestrecordsubcategorykeywords.yaml')
        with open(subcategories_keywords_path, 'r') as fin:
            keywords = yaml.safe_load(fin)
            return keywords

    @property
    def api_url(self):
        return f'http://{self._host}:{self._port}/api/v1'

    def save_to_yaml(self, yaml_path: str):
        records_plain = []
        for record_object in self.records:
            record_plain = {
                'datetime': record_object.dt.strftime(DIGEST_RECORD_DATETIME_FORMAT)
                            if record_object.dt is not None
                            else None,
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

    def load_specific_digest_records_from_server(self,
                                                 yaml_config_path: str,
                                                 digest_number: int):
        self._load_config(yaml_config_path)
        self._login()
        self._load_duplicates_for_specific_digest(yaml_config_path,
                                                  digest_number)
        self._basic_load_digest_records_from_server(yaml_config_path,
                                                    f'http://{self._host}:{self._port}/api/v1/specific-digest-records/?digest_number={digest_number}')

    def load_new_digest_records_from_server(self, yaml_config_path: str):
        self._load_config(yaml_config_path)
        self._login()
        self._basic_load_digest_records_from_server(yaml_config_path,
                                                    f'http://{self._host}:{self._port}/api/v1/new-digest-records/')

    def _load_duplicates_for_specific_digest(self,
                                             yaml_config_path: str,
                                             digest_number: int):
        logger.info(f'Getting digest records duplicates for digest number #{digest_number}')
        url = f'{self.api_url}/digest-records-duplicates-detailed/?digest_number={digest_number}'
        logger.debug(f'Getting URL {url}')
        result = requests.get(url,
                              headers={
                                  'Authorization': f'Bearer {self._token}',
                                  'Content-Type': 'application/json',
                              })
        if result.status_code != 200:
            logger.error(f'Failed to retrieve digest records duplicates, status code {result.status_code}, response: {result.content}')
            # TODO: Raise exception
            return None
        response_str = result.content.decode()
        response = json.loads(response_str)
        if not response:
            logger.info('No digest records duplicates found')
            return None
        response_converted = []
        for duplicate in response:
            duplicate_converted = {}
            for key in ('id', 'digest_number'):
                duplicate_converted[key] = duplicate[key]
            if not duplicate['digest_records']:
                logger.warning(f'Empty digest records list in duplicate #{duplicate["id"]}')
                continue
            duplicate_converted['digest_records'] = []
            for record in duplicate['digest_records']:
                if record['dt'] is not None:
                    dt_str = datetime.datetime.strptime(record['dt'],
                                                        '%Y-%m-%dT%H:%M:%SZ')
                else:
                    dt_str = None
                record_obj = DigestRecord(dt_str,
                                          record['title'],
                                          record['url'],
                                          digest_number=record['digest_number'],
                                          drid=record['id'],
                                          is_main=record['is_main'],
                                          keywords=record['keywords'].split(';') if record['keywords'] else [])
                record_obj.state = DigestRecordState(record['state'].lower()) if 'state' in record and record['state'] is not None else None
                record_obj.category = DigestRecordCategory(record['category'].lower()) if 'category' in record and record['category'] is not None else None
                if 'subcategory' in record and record['subcategory'] == 'DATABASES':
                    record['subcategory'] = 'db'
                record_obj.subcategory = DigestRecordSubcategory(record['subcategory'].lower()) if 'subcategory' in record and record['subcategory'] is not None else None
                duplicate_converted['digest_records'].append(record_obj)
            response_converted.append(duplicate_converted)
        self.duplicates += response_converted


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
            if record_plain['dt'] is not None:
                dt_str = datetime.datetime.strptime(record_plain['dt'],
                                                    '%Y-%m-%dT%H:%M:%SZ')
            else:
                dt_str = None
            record_object = DigestRecord(dt_str,
                                         record_plain['title'],
                                         record_plain['url'],
                                         digest_number=record_plain['digest_number'],
                                         drid=record_plain['id'],
                                         is_main=record_plain['is_main'],
                                         keywords=record_plain['keywords'].split(';') if record_plain['keywords'] else [])
            record_object.state = DigestRecordState(record_plain['state'].lower()) if 'state' in record_plain and record_plain['state'] is not None else None
            record_object.category = DigestRecordCategory(record_plain['category'].lower()) if 'category' in record_plain and record_plain['category'] is not None else None
            if 'subcategory' in record_plain and record_plain['subcategory'] == 'DATABASES':
                record_plain['subcategory'] = 'db'
            record_object.subcategory = DigestRecordSubcategory(record_plain['subcategory'].lower()) if 'subcategory' in record_plain and record_plain['subcategory'] is not None else None
            records_objects.append(record_object)
        self.records = records_objects

    def _clear_title(self, title: str):
        fixed_title = html.unescape(title)
        fixed_title = re.sub(r'^\[.+?\]\s+', '', fixed_title)
        return fixed_title

    def _check_url_if_english(self, url):
        for russian_source in RUSSIAN_SOURCES:
            if russian_source in url:
                return False
        return True

    def _build_url_html(self, url: str):
        return f'<a href="{url}">{url}</a>{" (en)" if self._check_url_if_english(url) else ""}'

    def records_to_html(self, html_path):
        logger.info('Converting records to HTML')
        output_records = {
            'main': [],
            DigestRecordCategory.NEWS.value: {subcategory_value: [] for subcategory_value in DIGEST_RECORD_SUBCATEGORY_VALUES},
            DigestRecordCategory.ARTICLES.value: {subcategory_value: [] for subcategory_value in DIGEST_RECORD_SUBCATEGORY_VALUES},
            DigestRecordCategory.RELEASES.value: {subcategory_value: [] for subcategory_value in DIGEST_RECORD_SUBCATEGORY_VALUES},
            DigestRecordCategory.OTHER.value: [],
        }
        digest_records_ids_from_duplicates = []
        for duplicate in self.duplicates:
            duplicate_records = duplicate['digest_records']
            first_in_duplicate = duplicate_records[0]
            if first_in_duplicate.state != DigestRecordState.IN_DIGEST:
                continue
            for duplicate_record in duplicate_records:
                digest_records_ids_from_duplicates.append(duplicate_record.drid)
            if first_in_duplicate.is_main:
                output_records['main'].append(duplicate_records)
            elif first_in_duplicate.category == DigestRecordCategory.OTHER:
                output_records[first_in_duplicate.category.value].append(duplicate_records)
            elif not first_in_duplicate.is_main and first_in_duplicate.category in (DigestRecordCategory.NEWS,
                                                                                    DigestRecordCategory.ARTICLES,
                                                                                    DigestRecordCategory.RELEASES):
                if first_in_duplicate.subcategory is not None:
                    output_records[first_in_duplicate.category.value][first_in_duplicate.subcategory.value].append(duplicate_records)
            else:
                pprint(duplicate)
                raise NotImplementedError
        for digest_record in self.records:
            if digest_record.state != DigestRecordState.IN_DIGEST:
                continue
            if digest_record.drid in digest_records_ids_from_duplicates:
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
            if not isinstance(main_record, list):
                output += f'<h3>{self._clear_title(main_record.title)}</h3>\n\n'
                output += f'<i><b>Категория</b>: {DIGEST_RECORD_CATEGORY_RU_MAPPING[main_record.category.value]}/{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[main_record.subcategory.value]}</i><br>\n\n'
                output += f'Подробности {self._build_url_html(main_record.url)}\n\n'
            else:
                output += f'<h3>{[self._clear_title(r.title) for r in main_record]}</h3>\n\n'
                output += f'<i><b>Категория</b>: {DIGEST_RECORD_CATEGORY_RU_MAPPING[main_record[0].category.value]}/{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[main_record[0].subcategory.value]}</i><br>\n\n'
                output += 'Подробности:<br>\n\n'
                output += '<ol>\n'
                for r in main_record:
                    output += f'<li>{r.title} {self._build_url_html(r.url)}</li>\n\n'
                output += '</ol>\n'

        output += '<h2>Короткой строкой</h2>\n\n'

        keys = (
            DigestRecordCategory.NEWS.value,
            DigestRecordCategory.ARTICLES.value,
            DigestRecordCategory.RELEASES.value,
        )
        for key in keys:
            output += f'<h3>{DIGEST_RECORD_CATEGORY_RU_MAPPING[key]}</h3>\n\n'
            for key_record_subcategory, key_records in output_records[key].items():
                if not key_records:
                    continue
                output += f'<h4>{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[key_record_subcategory]}</h4>\n\n'
                if len(key_records) == 1:
                    key_record = key_records[0]
                    if not isinstance(key_record, list):
                        output += f'<p>{self._clear_title(key_record.title)} {self._build_url_html(key_record.url)}</p>\n'
                    else:
                        output += f'<p>{[self._clear_title(r.title) for r in key_record]} {", ".join([self._build_url_html(r.url) for r in key_record])}</p>\n'
                else:
                    output += '<ol>\n'
                    for key_record in key_records:
                        if not isinstance(key_record, list):
                            output += f'<li>{self._clear_title(key_record.title)} {self._build_url_html(key_record.url)}</li>\n'
                        else:
                            output += f'<li>{[self._clear_title(r.title) for r in key_record]} {", ".join([self._build_url_html(r.url) for r in key_record])}</li>\n'
                    output += '</ol>\n'

        if len(output_records[DigestRecordCategory.OTHER.value]):
            output += '<h2>Что ещё посмотреть</h2>\n\n'
            if len(output_records[DigestRecordCategory.OTHER.value]) == 1:
                other_record = output_records[DigestRecordCategory.OTHER.value][0]
                output += f'{self._clear_title(other_record.title)} <a href="{other_record.url}">{other_record.url}</a>{" (en)" if self._check_url_if_english(other_record.url) else ""}<br>\n'
            else:
                output += '<ol>\n'
                for other_record in output_records[DigestRecordCategory.OTHER.value]:
                    output += f'<li>{self._clear_title(other_record.title)} <a href="{other_record.url}">{other_record.url}</a>{" (en)" if self._check_url_if_english(other_record.url) else ""}</li>\n'
                output += '</ol>\n'

        logger.info('Converted')
        with open(html_path, 'w') as fout:
            logger.info(f'Saving output to "{html_path}"')
            fout.write(output)

    def _guess_category(self, title: str) -> DigestRecordCategory:
        for release_keyword in RELEASES_KEYWORDS:
            if release_keyword in title.lower():
                return DigestRecordCategory.RELEASES
        for subcategory, keywords_by_type in self._subcategories_keywords.items():
            for keyword in keywords_by_type['specific']:
                keyword = keyword.replace('+', r'\+')
                if re.search(keyword + r',?\s+v?\.?\d', title, re.IGNORECASE):
                    return DigestRecordCategory.RELEASES
        return None

    def _guess_subcategory(self, title: str) -> (List[DigestRecordSubcategory], Dict):
        guessed_subcategories: List[DigestRecordSubcategory] = []
        matched_subcategories_keywords = {}
        for subcategory, keywords_by_type in self._subcategories_keywords.items():
            keywords = keywords_by_type['generic'] + keywords_by_type['specific']
            for keyword in keywords:
                if re.search(rf'\b{re.escape(keyword)}\b', title, re.IGNORECASE):
                    subcategory_already_matched = False
                    for guessed_subcategory in guessed_subcategories:
                        if guessed_subcategory.value == subcategory:
                            subcategory_already_matched = True
                            break
                    if not subcategory_already_matched:
                        guessed_subcategories.append(DigestRecordSubcategory(subcategory))
                    if subcategory in matched_subcategories_keywords:
                        matched_subcategories_keywords[subcategory].append(keyword)
                    else:
                        matched_subcategories_keywords[subcategory] = [keyword]
        return guessed_subcategories, matched_subcategories_keywords

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
            if record.digest_number is None:
                if current_digest_number is None:
                    record.digest_number = self._ask_digest_number(record)
                    current_digest_number = record.digest_number
                else:
                    record.digest_number = current_digest_number
            if record.state in (DigestRecordState.IN_DIGEST,
                                DigestRecordState.OUTDATED):
                if record.is_main is None:
                    is_main = self._ask_bool(f'Please input whether or no "{record.title}" is main (y/n): ')
                    logger.info(f'{"Marking" if is_main else "Not marking"} "{record.title}" as one of main records')
                    record.is_main = is_main

                guessed_category = self._guess_category(record.title)
                if guessed_category is not None:
                    msg = f'Guessed category is "{DIGEST_RECORD_CATEGORY_RU_MAPPING[guessed_category.value]}". Accept? y/n: '
                    accepted = self._ask_bool(msg)
                    if accepted:
                        logger.info(f'Setting category of record "{record.title}" to "{DIGEST_RECORD_CATEGORY_RU_MAPPING[guessed_category.value]}"')
                        record.category = guessed_category

                guessed_subcategories, matched_subcategories_keywords = self._guess_subcategory(record.title)
                if guessed_subcategories:
                    matched_subcategories_keywords_translated = {}
                    for matched_subcategory, keywords in matched_subcategories_keywords.items():
                        matched_subcategories_keywords_translated[DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[matched_subcategory]] = keywords
                    print(f'Matched subcategories keywords:\n{pformat(matched_subcategories_keywords_translated)}')
                    if len(guessed_subcategories) == 1:
                        guessed_subcategory = guessed_subcategories[0]
                        msg = f'Guessed subcategory is "{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[guessed_subcategory.value]}". Accept? y/n: '
                        accepted = self._ask_bool(msg)
                        if accepted:
                            logger.info(f'Setting subcategory of record "{record.title}" to "{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[guessed_subcategory.value]}"')
                            record.subcategory = guessed_subcategory
                    else:
                        msg = 'Guessed subcategories are:'
                        for guessed_subcategory_i, guessed_subcategory in enumerate(guessed_subcategories):
                            msg += f'\n{guessed_subcategory_i + 1}. {DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[guessed_subcategory.value]}'
                        msg += '\nType guessed subcategory index or "n" if no match: '
                        guessed_subcategory_index = self._ask_guessed_subcategory_index(msg,
                                                                                        len(guessed_subcategories))
                        if guessed_subcategory_index is not None:
                            guessed_subcategory = guessed_subcategories[guessed_subcategory_index - 1]
                            logger.info(f'Setting subcategory of record "{record.title}" to "{DIGEST_RECORD_SUBCATEGORY_RU_MAPPING[guessed_subcategory.value]}"')
                            record.subcategory = guessed_subcategory

                if record.category == DigestRecordCategory.UNKNOWN or record.category is None:
                    record.category = self._ask_category(record,
                                                         DIGEST_RECORD_CATEGORY_RU_MAPPING)
                if record.subcategory is None:
                    if record.category != DigestRecordCategory.OTHER:
                        record.subcategory = self._ask_subcategory(record,
                                                                   DIGEST_RECORD_SUBCATEGORY_RU_MAPPING)

                if record.state == DigestRecordState.IN_DIGEST \
                        and record.category is not None \
                        and record.subcategory is not None:
                    current_records_with_similar_categories = self._similar_digest_records(record.digest_number,
                                                                                           record.category,
                                                                                           record.subcategory)
                    if current_records_with_similar_categories:
                        print(f'Are there any duplicates for digest record "{record.title}" ({record.url})? Here is list of possible ones:')
                        i = 1
                        options_indexes = []
                        for option in current_records_with_similar_categories['duplicates']:
                            print(f'{i}. {"; ".join([dr["title"] + " " + dr["url"] for dr in option["digest_records"]])}')
                            options_indexes.append(option['id'])
                            i += 1
                        for option in current_records_with_similar_categories['records']:
                            print(f'{i}. {option["title"]} {option["url"]}')
                            options_indexes.append(option['id'])
                            i += 1
                        option_index = self._ask_option_index_or_no(i - 1)
                        if option_index is not None:
                            if option_index <= len(current_records_with_similar_categories['duplicates']):
                                existing_drids = None
                                for option in current_records_with_similar_categories['duplicates']:
                                    if option['id'] == options_indexes[option_index - 1]:
                                        existing_drids = [dr['id'] for dr in option['digest_records']]
                                self._add_digest_record_do_duplicate(options_indexes[option_index - 1], existing_drids, record.drid)
                                logger.info('Added to duplicate')  # TODO: More details
                            else:
                                self._create_digest_record_duplicate(record.digest_number, [options_indexes[option_index - 1], record.drid])
                                logger.info('New duplicate created')  # TODO: More details
                        else:
                            logger.info('No duplicates specified')
                    else:
                        logger.info('Similar digest records not found')


            if record in self._filtered_records:
                records_left_to_process -= 1
                if records_left_to_process > 0:
                    logger.info(f'{records_left_to_process} record(s) left to process')

            logger.info(f'Uploading record #{record.drid} to FNGS')
            result = requests.patch(f'{self.api_url}/digest-records/{record.drid}/',
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
            logger.info(f'Uploaded record #{record.drid} for digest #{record.digest_number} to FNGS')
            logger.info(f'If you want to change some parameters that you\'ve set - go to http://fn.permlug.org/admin/gatherer/digestrecord/{record.drid}/change/')

    def _ask_state(self, record: DigestRecord):
        return self._ask_enum('digest record state', DigestRecordState, record)

    def _ask_option_index_or_no(self, max_index):
        while True:
            option_index_str = input(f'Please input option number or "n" to create new one: ')
            if option_index_str.isnumeric():
                option_index = int(option_index_str)
                if 0 < option_index <= max_index:
                    return option_index
                else:
                    logger.error(f'Index should be positive and not more than {max_index}')
            elif option_index_str == 'n':
                return None
            else:
                print('Invalid answer, it should be integer or "n"')
        raise NotImplementedError

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

    def _ask_guessed_subcategory_index(self,
                                       question: str,
                                       indexes_count: int):
        while True:
            answer = input(question)
            if answer.isnumeric():
                index = int(answer)
                if 1 <= index <= indexes_count:
                    return index
                else:
                    print(f'Invalid index, it should be between 1 and {indexes_count}')
                    continue
            elif answer == 'n':
                return None
            else:
                print(f'Invalid answer, it should be positive integer between 1 and {indexes_count} or "n"')
                continue
        raise NotImplementedError

    def _ask_bool(self, question: str):
        while True:
            bool_str = input(question)
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

    def _similar_digest_records(self,
                                digest_number,
                                category,
                                subcategory):
        logger.debug(f'Getting similar records for digest number #{digest_number}, category "{category}" and subcategory "{subcategory}"')
        url = f'{self.api_url}/similar-digest-records/?digest_number={digest_number}&category={category.name}&subcategory={subcategory.name}'
        logger.debug(f'Getting URL {url}')
        result = requests.get(url,
                              headers={
                                  'Authorization': f'Bearer {self._token}',
                                  'Content-Type': 'application/json',
                              })
        if result.status_code != 200:
            logger.error(f'Failed to retrieve similar digest records, status code {result.status_code}, response: {result.content}')
            # TODO: Raise exception
            return None
        response_str = result.content.decode()
        response = json.loads(response_str)
        if not response:
            logger.info('No similar records found')
            return None
        options_duplicates = []
        options_records = []
        for similar_record_i, similar_record in enumerate(response):
            duplicates_object = self._duplicates_by_digest_record(similar_record['id'])
            if duplicates_object:
                options_duplicates.append(duplicates_object)
            else:
                options_records.append({'id': similar_record['id'], 'title': similar_record['title'], 'url': similar_record['url']})
        options_duplicates_filtered = []
        for option_duplicate in options_duplicates:
            duplicate_digest_records = []
            for duplicate_digest_record in option_duplicate['digest_records']:
                duplicate_digest_records.append({'id': duplicate_digest_record['id'], 'title': duplicate_digest_record['title'], 'url': duplicate_digest_record['url']})
            exists = False
            for option_duplicates_filtered in options_duplicates_filtered:
                if option_duplicates_filtered['id'] == option_duplicate['id']:
                    exists = True
                    break
            if not exists:
                options_duplicates_filtered.append({'id': option_duplicate['id'], 'digest_records': duplicate_digest_records})
        return {
            'duplicates': options_duplicates_filtered,
            'records': options_records,
        }

    def _add_digest_record_do_duplicate(self, duplicate_id, existing_drids, digest_record_id):
        logger.debug(f'Adding digest record #{digest_record_id} to duplicate #{duplicate_id}')
        url = f'{self.api_url}/digest-records-duplicates/{duplicate_id}/'
        data = {
            'id': duplicate_id,
            'digest_records': existing_drids + [digest_record_id],
        }
        logger.debug(f'PATCHing URL {url} with data {data}')
        result = requests.patch(url,
                                data=json.dumps(data),
                                headers={
                                    'Authorization': f'Bearer {self._token}',
                                    'Content-Type': 'application/json',
                                })
        if result.status_code != 200:
            logger.error(f'Failed to update digest record duplicate, status code {result.status_code}, response: {result.content}')
            # TODO: Raise exception

    def _create_digest_record_duplicate(self,
                                        digest_number,
                                        digest_records_ids,
                                        ):
        logger.debug(f'Creating digest record duplicate from #{digest_records_ids}')
        url = f'{self.api_url}/digest-records-duplicates/'
        data = {
            'digest_number': digest_number,
            'digest_records': digest_records_ids,
        }
        logger.debug(f'POSTing data {data} to URL {url}')
        result = requests.post(url,
                               data=json.dumps(data),
                               headers={
                                   'Authorization': f'Bearer {self._token}',
                                   'Content-Type': 'application/json',
                               })
        if result.status_code != 201:
            logger.error(f'Failed to create digest record duplicate, status code {result.status_code}, response: {result.content}')
            # TODO: Raise exception

    def _digest_record_by_id(self, digest_record_id):
        logger.debug(f'Loading digest record #{digest_record_id}')
        url = f'{self.api_url}/digest-records/{digest_record_id}'
        logger.debug(f'Getting URL {url}')
        result = requests.get(url,
                              headers = {
                                  'Authorization': f'Bearer {self._token}',
                                  'Content-Type': 'application/json',
                              })
        if result.status_code != 200:
            logger.error(f'Failed to retrieve digest record, status code {result.status_code}, response: {result.content}')
            # TODO: Raise exception
            return None
        logger.debug(f'Received response: {result.content}')
        response_str = result.content.decode()
        response = json.loads(response_str)
        if not response:
            # TODO: Raise exception
            logger.error('No digest record in response')
            return None
        return response

    def _duplicates_by_digest_record(self, digest_record_id):
        logger.debug(f'Checking if there are duplicates for digest record #{digest_record_id}')
        url = f'{self.api_url}/duplicates-by-digest-record/?digest_record={digest_record_id}'
        logger.debug(f'Getting URL {url}')
        result = requests.get(url,
                              headers={
                                  'Authorization': f'Bearer {self._token}',
                                  'Content-Type': 'application/json',
                              })
        if result.status_code != 200:
            logger.error(f'Failed to retrieve similar digest records, status code {result.status_code}, response: {result.content}')
            # TODO: Raise exception
            return None
        logger.debug(f'Received response: {result.content}')
        response_str = result.content.decode()
        response = json.loads(response_str)
        if not response:
            logger.debug(f'No duplicates found for digest record #{digest_record_id}')
            return None
        return response[0] # TODO: Handle multiple case

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
