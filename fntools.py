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
from multiprocessing.pool import ThreadPool
import threading
from enum import Enum
import random
from typing import List, Dict
import os
from pprint import (
    pformat,
    pprint,
)
import html
from colorama import Fore, Style
from urllib.parse import (
    urlparse,
    parse_qsl,
    urlencode,
    urlunparse,
)

from data.releaseskeywords import *
from data.articleskeywords import *
from data.digestrecordcontenttype import *
from data.digestrecordstate import *
from data.digestrecordcontentcategory import *

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
DIGEST_RECORD_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'
FNGS_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'

days_count = None


class HtmlFormat(Enum):
    HABR = 'habr'
    REDDIT = 'reddit'


class Language(Enum):
    ENGLISH = 'english'
    RUSSIAN = 'russian'


class Formatter(logging.Formatter):

    def __init__(self, fmt=None):
        if fmt is None:
            fmt = self._colorized_fmt()
        logging.Formatter.__init__(self, fmt)

    def _colorized_fmt(self, color=Fore.RESET):
        return f'{color}[%(asctime)s] %(levelname)s: %(message)s{Style.RESET_ALL}'

    def format(self, record):
        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._style._fmt

        # Replace the original format with one customized by logging level
        if record.levelno == logging.DEBUG:
            color = Fore.CYAN
        elif record.levelno == logging.INFO:
            color = Fore.GREEN
        elif record.levelno == logging.WARNING:
            color = Fore.YELLOW
        elif record.levelno == logging.ERROR:
            color = Fore.RED
        elif record.levelno == logging.CRITICAL:
            color = Fore.MAGENTA
        else:
            color = Fore.WHITE
        self._style._fmt = self._colorized_fmt(color)

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)

        # Restore the original format configured by the user
        self._style._fmt = format_orig

        return result


class Logger(logging.Logger):

    def __init__(self):
        super().__init__('fntools')
        h = logging.StreamHandler(sys.stderr)
        f = Formatter()
        h.setFormatter(f)
        h.flush = sys.stderr.flush
        self.addHandler(h)
        self.setLevel(logging.INFO)


logger = Logger()

NETWORK_TIMEOUT_SECONDS = 30


class NetworkingMixin:
    SLEEP_BETWEEN_ATTEMPTS_SECONDS = 5
    NETWORK_RETRIES_COUNT = 50
    MAX_PAGE_SIZE = 500

    class RequestType(Enum):
        GET = 'GET'
        PATCH = 'PATCH'
        POST = 'POST'

    @staticmethod
    def get_with_retries(url, headers=None, timeout=NETWORK_TIMEOUT_SECONDS):
        response = NetworkingMixin.request_with_retries(url, headers=headers, method=NetworkingMixin.RequestType.GET, data=None, timeout=timeout)
        if response.status_code != 200:
            raise Exception(f'Non-success HTTP return code {response.status_code}')
        return response

    @staticmethod
    def get_results_from_all_pages(base_url, headers, timeout=NETWORK_TIMEOUT_SECONDS):
        results = []
        url_parts = list(urlparse(base_url))
        query = dict(parse_qsl(url_parts[4]))
        if 'page_size' not in query:
            query.update({'page_size': NetworkingMixin.MAX_PAGE_SIZE})
            url_parts[4] = urlencode(query)
            base_url = urlunparse(url_parts)
        while True:  # TODO: Think how to get rid of infinite loop
            response = NetworkingMixin.get_with_retries(base_url, headers, timeout)
            response_str = response.content.decode()
            response_data = json.loads(response_str)
            results += response_data['results']
            if response_data['links']['next']:
                base_url = response_data['links']['next']
            else:
                break
        logger.debug(f'{len(results)} results fetched')
        return results

    @staticmethod
    def patch_with_retries(url, headers=None, data=None, timeout=NETWORK_TIMEOUT_SECONDS):
        return NetworkingMixin.request_with_retries(url, headers=headers, method=NetworkingMixin.RequestType.PATCH, data=data, timeout=timeout)

    @staticmethod
    def post_with_retries(url, headers=None, data=None, timeout=NETWORK_TIMEOUT_SECONDS):
        return NetworkingMixin.request_with_retries(url, headers=headers, method=NetworkingMixin.RequestType.POST, data=data, timeout=timeout)

    @staticmethod
    def request_with_retries(url,
                             headers=None,
                             method=RequestType.GET,
                             data=None,
                             timeout=NETWORK_TIMEOUT_SECONDS):
        if headers is None:
            headers = {}
        for attempt_i in range(NetworkingMixin.NETWORK_RETRIES_COUNT):
            begin_datetime = datetime.datetime.now()
            try:
                if method == NetworkingMixin.RequestType.GET:
                    logger.debug(f'GETting URL "{url}"')
                    response = requests.get(url,
                                            headers=headers,
                                            timeout=timeout)
                elif method == NetworkingMixin.RequestType.PATCH:
                    logger.debug(f'PATCHing URL "{url}"')
                    response = requests.patch(url,
                                              data=data,
                                              headers=headers,
                                              timeout=timeout)
                elif method == NetworkingMixin.RequestType.POST:
                    logger.debug(f'POSTing URL "{url}"')
                    response = requests.post(url,
                                             data=data,
                                             headers=headers,
                                             timeout=timeout)
                else:
                    raise NotImplementedError
                end_datetime = datetime.datetime.now()
                logger.debug(f'Response time: {end_datetime - begin_datetime}')
                return response
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                base_timeout_msg = f'Request to url {url} reached timeout of {NETWORK_TIMEOUT_SECONDS} seconds'
                if attempt_i != NetworkingMixin.NETWORK_RETRIES_COUNT - 1:
                    logger.warning(f'{base_timeout_msg}, sleeping {NetworkingMixin.SLEEP_BETWEEN_ATTEMPTS_SECONDS} seconds and trying again, {NetworkingMixin.NETWORK_RETRIES_COUNT - attempt_i - 1} retries left')
                    time.sleep(NetworkingMixin.SLEEP_BETWEEN_ATTEMPTS_SECONDS)
                else:
                    raise Exception(f'{base_timeout_msg}, retries count {NetworkingMixin.NETWORK_RETRIES_COUNT} exceeded')


class BasicPostsStatisticsGetter(NetworkingMixin,
                                 metaclass=ABCMeta):

    def __init__(self, sessions_count):
        self.sessions_count = sessions_count
        self._posts_urls = {}
        self.source_name = None
        self._posts_statistics = {}
        self._lock = threading.Lock()

    def gather_posts_statistics(self):
        threads_pool = ThreadPool(self.sessions_count)
        self._posts_statistics = {}
        threads_pool.map(self._gather_post_statistics, [(self, number, url, self._lock) for number, url in self.posts_urls.items()])
        return self._posts_statistics

    def _gather_post_statistics(self, data):
        obj, number, url, lock = data
        views_count = obj._internal_gather_post_statistics(number, url)
        logger.info(f'Views count for {obj.source_name} post #{number} ({url}): {views_count}')
        obj._lock.acquire()
        obj._posts_statistics[number] = views_count
        obj._lock.release()

    @abstractmethod
    def _internal_gather_post_statistics(self, number, url):
        pass

    @property
    def posts_urls(self):
        return self._posts_urls


class VkPostsStatisticsGetter(BasicPostsStatisticsGetter):

    def __init__(self, sessions_count):
        super().__init__(sessions_count)
        self.source_name = 'VK'
        self._posts_urls = {}
        self._posts_count = 1

    @property
    def posts_urls(self):
        if self._posts_urls == {}:
            for i in range(self._posts_count):
                self._posts_urls[i] = f'https://vk.com/@permlug-foss-news-{i}'
        return self._posts_urls

    def _internal_gather_post_statistics(self, number, url):
        response = NetworkingMixin.get_with_retries(url)
        content = response.text
        re_result = re.search(r'<div class="articleView__footer_views" style="">(\d+) просмотр', content)
        if re_result is None:
            logger.error(f'Failed to find statistics in FOSS News #{number} ({url}) on VK')
            return None
        return int(re_result.group(1))


class DigestRecord:

    def __init__(self,
                 dt: datetime.datetime,
                 source: str,
                 title: str,
                 url: str,
                 additional_url: str,
                 state: DigestRecordState = DigestRecordState.UNKNOWN,
                 digest_issue: int = None,
                 content_type: DigestRecordContentType = DigestRecordContentType.UNKNOWN,
                 content_category: DigestRecordContentCategory = None,
                 drid: int = None,
                 is_main: bool = None,
                 keywords: List = None,
                 language: str = None,
                 estimations: List = None):
        self.dt = dt
        self.source = source
        self.title = title
        self.url = url
        self.additional_url = additional_url
        self.state = state
        self.digest_issue = digest_issue['number'] if isinstance(digest_issue, dict) else digest_issue
        self.content_type = content_type
        self.content_category = content_category
        self.drid = drid
        self.is_main = is_main
        self.keywords = keywords
        self.proprietary_keywords_names = set([k['name'] for k in keywords if k['proprietary']] if keywords else [])
        self.not_proprietary_keywords_names = set([k['name'] for k in keywords if not k['proprietary'] and not k['is_generic']] if keywords else [])
        self.language = Language(language.lower())
        self.estimations = estimations

    def __str__(self):
        return pformat(self.to_dict())

    def to_dict(self):
        return {
            'drid': self.drid,
            'datetime': self.dt.strftime(DIGEST_RECORD_DATETIME_FORMAT) if self.dt is not None else None,
            'source': self.source,
            'title': self.title,
            'url': self.url,
            'is_main': self.is_main,
            'state': self.state.value if self.state is not None else None,
            'digest_issue': self.digest_issue,
            'content_type': self.content_type.value if self.content_type is not None else None,
            'content_category': self.content_category.value if self.content_category is not None else None,
            'proprietary_keywords_names': self.proprietary_keywords_names,
            'not_proprietary_keywords_names': self.not_proprietary_keywords_names,
            'language': self.language.value,
            'estimations': [{'user': e['user'],
                             'state': e['state'].value}
                            for e in self.estimations],
        }


class ServerConnectionMixin:
    # Requires NetworkingMixin

    def _load_config(self, config_path):
        logger.info(f'Loading gathering server connect data from config "{config_path}"')
        with open(config_path, 'r') as fin:
            config_data = yaml.safe_load(fin)
            self._host = config_data['host']
            self._protocol = config_data['protocol']
            self._port = config_data['port']
            self._user = config_data['user']
            self._password = config_data['password']
            logger.info('Loaded')

    def _login(self):
        logger.info('Logging in')
        url = f'{self.auth_api_url}/token/'
        data = {'username': self._user, 'password': self._password}
        response = self.post_with_retries(url=url,
                                          data=data)
        if response.status_code != 200:
            raise Exception(f'Invalid response code from FNGS login - {response.status_code}: {response.content.decode("utf-8")}')
        result_data = json.loads(response.content)
        self._token = result_data['access']
        logger.info('Logged in')

    @property
    def base_api_url(self):
        return f'{self._protocol}://{self._host}:{self._port}/api/v2'

    @property
    def auth_api_url(self):
        return f'{self.base_api_url}/auth'

    @property
    def gatherer_api_url(self):
        return f'{self.base_api_url}/gatherer'

    @property
    def tbot_api_url(self):
        return f'{self.base_api_url}/tbot'

    @property
    def admin_url(self):
        return f'{self._protocol}://{self._host}:{self._port}/admin'

    @property
    def _auth_headers(self):
        return {
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/json',
        }


class HabrPostsStatisticsGetter(BasicPostsStatisticsGetter,
                                ServerConnectionMixin):

    def __init__(self, config_path, sessions_count):
        super().__init__(sessions_count)
        self.source_name = 'Habr'
        self.sessions_count = sessions_count
        self._drivers = []
        self._locks: List[threading.Lock] = []
        self._load_config(config_path)
        self._login()
        self._posts_urls = {di['number']: di['habr_url'] for di in self._digest_issues}

    def gather_posts_statistics(self):
        self._drivers = [webdriver.Firefox() for _ in range(self.sessions_count)]
        self._locks = [threading.Lock() for _ in range(self.sessions_count)]
        stats = super().gather_posts_statistics()
        [driver.close() for driver in self._drivers]
        return stats

    @property
    def _digest_issues(self):
        response = self.get_with_retries(f'{self.gatherer_api_url}/digest-issue/?page_size=500', headers=self._auth_headers)
        content = response.text
        if response.status_code != 200:
            raise Exception(f'Failed to get digest issues info, status code {response.status_code}, response: {content}')
        content_data = json.loads(content)['results']
        return content_data

    def _internal_gather_post_statistics(self, number, url):
        if not url:
            logger.error(f'Empty URL for digest issue #{number}')
            return None
        job_index = random.randint(0, self.sessions_count - 1)
        driver = self._drivers[job_index]
        lock = self._locks[job_index]
        lock.acquire()
        # driver = webdriver.Firefox()
        driver.get(url)
        xpath = '//div[contains(@class, "tm-page__main tm-page__main_has-sidebar")]//div[contains(@class, "tm-data-icons tm-article-sticky-panel__icons")]//span[contains(@class, "tm-icon-counter tm-data-icons__item")]/span'
        element = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, xpath)))

        full_statistics_str = element.text
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

        lock.release()
        # driver.close()
        return views_count


class DbToHtmlConverter:

    def __init__(self, records, similar_records):
        self._records = records
        self._similar_records = similar_records

    def convert(self, html_path):
        logger.info('Converting DB records to HTML')
        content = self._convert()
        logger.info('Converted')
        with open(html_path, 'w') as fout:
            logger.info(f'Saving output to "{html_path}"')
            fout.write(content)

    @abstractmethod
    def _convert(self) -> str:
        pass


# TODO: Extract common code from here and HabrDbToHtmlConverter
class RedditDbToHtmlConverter(DbToHtmlConverter):

    def __init__(self, records, similar_records):
        super().__init__(records, similar_records)

    def _process_url(self, digest_record):
        # TODO: Find better solution of marking things that needs attention
        if digest_record.language == Language.RUSSIAN:
            return '!!! ' + digest_record.url
        elif digest_record.additional_url:
            return '!!! ' + digest_record.additional_url
        else:
            return digest_record.url

    def _convert(self) -> str:
        # TODO: Refactor additional_url and OpenNET related code
        output_records = {
            'main': [],
            DigestRecordContentType.NEWS.value: {content_category: [] for content_category in
                                                 DIGEST_RECORD_CONTENT_CATEGORY_VALUES},
            DigestRecordContentType.VIDEOS.value: {content_category: [] for content_category in
                                                   DIGEST_RECORD_CONTENT_CATEGORY_VALUES},
            DigestRecordContentType.ARTICLES.value: {content_category: [] for content_category in
                                                     DIGEST_RECORD_CONTENT_CATEGORY_VALUES},
            DigestRecordContentType.RELEASES.value: {content_category: [] for content_category in
                                                     DIGEST_RECORD_CONTENT_CATEGORY_VALUES},
            DigestRecordContentType.OTHER.value: [],
        }
        digest_records_ids_from_similar_records = []
        for similar_records_item in self._similar_records:
            similar_records_item_records = similar_records_item['digest_records']
            similar_records_item_records_included_to_digest = [dr for dr in similar_records_item_records if dr.state == DigestRecordState.IN_DIGEST and (dr.language == Language.ENGLISH or 'opennet' in dr.url)]
            if not similar_records_item_records_included_to_digest:
                continue
            for similar_records_item_records_one in similar_records_item_records:
                digest_records_ids_from_similar_records.append(similar_records_item_records_one.drid)
            first_in_similar_records_item_records = similar_records_item_records_included_to_digest[0]
            if [dr for dr in similar_records_item_records_included_to_digest if dr.is_main]:
                output_records['main'].append(similar_records_item_records)
            elif first_in_similar_records_item_records.content_type == DigestRecordContentType.OTHER:
                output_records[first_in_similar_records_item_records.content_type.value].append(similar_records_item_records)
            elif not first_in_similar_records_item_records.is_main and first_in_similar_records_item_records.content_type in (DigestRecordContentType.NEWS,
                                                                                        DigestRecordContentType.ARTICLES,
                                                                                        DigestRecordContentType.VIDEOS,
                                                                                        DigestRecordContentType.RELEASES):
                if first_in_similar_records_item_records.content_category is not None:
                    output_records[first_in_similar_records_item_records.content_type.value][first_in_similar_records_item_records.content_category.value].append(similar_records_item_records)
            else:
                pprint(similar_records_item)
                raise NotImplementedError
        for digest_record in self._records:
            if digest_record.state != DigestRecordState.IN_DIGEST:
                continue
            if digest_record.drid in digest_records_ids_from_similar_records:
                continue
            if digest_record.is_main:
                output_records['main'].append(digest_record)
            elif digest_record.content_type == DigestRecordContentType.OTHER:
                output_records[digest_record.content_type.value].append(digest_record)
            elif not digest_record.is_main and digest_record.content_type in (DigestRecordContentType.NEWS,
                                                                              DigestRecordContentType.ARTICLES,
                                                                              DigestRecordContentType.VIDEOS,
                                                                              DigestRecordContentType.RELEASES):
                if digest_record.content_category is not None:
                    output_records[digest_record.content_type.value][digest_record.content_category.value].append(digest_record)
            else:
                print(digest_record.title, digest_record.content_type, digest_record.is_main)
                raise NotImplementedError
        output = '<h2>Main</h2>\n\n'
        # pprint([([r.title for r in rs] if isinstance(rs, list) else rs.title) for rs in output_records['main']])
        for main_record in output_records['main']:
            if not isinstance(main_record, list):
                output += f'<h3>{DigestRecordsCollection.clear_title(main_record.title)}</h3>\n\n'
                output += f'<i><b>Category</b>: {DIGEST_RECORD_CONTENT_TYPE_EN_MAPPING[main_record.content_type.value]}/{DIGEST_RECORD_CONTENT_CATEGORY_EN_MAPPING[main_record.content_category.value]}</i><br>\n\n'
                output += f'Details {DigestRecordsCollection.build_url_html(self._process_url(main_record), main_record.language, do_not_mark_language=True)}\n\n'
            else:
                output += f'<h3>{[DigestRecordsCollection.clear_title(r.title) for r in main_record]}</h3>\n\n'
                output += f'<i><b>Category</b>: {DIGEST_RECORD_CONTENT_TYPE_EN_MAPPING[main_record[0].content_type.value]}/{DIGEST_RECORD_CONTENT_CATEGORY_EN_MAPPING[main_record[0].content_category.value]}</i><br>\n\n'
                output += 'Details:<br>\n\n'
                output += '<ol>\n'
                for r in main_record:
                    output += f'<li>{r.title} {DigestRecordsCollection.build_url_html(self._process_url(r), r.language, do_not_mark_language=True)}</li>\n\n'
                output += '</ol>\n'

        output += '<h2>Briefly</h2>\n\n'

        keys = (
            DigestRecordContentType.NEWS.value,
            DigestRecordContentType.VIDEOS.value,
            DigestRecordContentType.ARTICLES.value,
            DigestRecordContentType.RELEASES.value,
        )
        for key in keys:
            output += f'<h3>{DIGEST_RECORD_CONTENT_TYPE_EN_MAPPING[key]}</h3>\n\n'
            for key_record_content_category, key_records in output_records[key].items():
                if not key_records:
                    continue
                output += f'<h4>{DIGEST_RECORD_CONTENT_CATEGORY_EN_MAPPING[key_record_content_category]}</h4>\n\n'
                for key_record in key_records:
                    if not isinstance(key_record, list):
                        output += f'<p>{DigestRecordsCollection.build_url_html(self._process_url(key_record), key_record.language, do_not_mark_language=True, link_text=DigestRecordsCollection.clear_title(key_record.title))}</p>\n'
                    else:
                        output += f'<p>{", ".join([DigestRecordsCollection.build_url_html(self._process_url(r), r.language, do_not_mark_language=True, link_text=DigestRecordsCollection.clear_title(r.title)) for r in key_record])}</p>\n'

        if len(output_records[DigestRecordContentType.OTHER.value]):
            output += '<h2>More links</h2>\n\n'
            for other_record in output_records[DigestRecordContentType.OTHER.value]:
                output += f'<p>{DigestRecordsCollection.build_url_html(self._process_url(other_record), other_record.language, do_not_mark_language=True, link_text=DigestRecordsCollection.clear_title(other_record.title))}</p>\n'
        return output


# TODO: Extract common code from here and RedditDbToHtmlConverter
class HabrDbToHtmlConverter(DbToHtmlConverter):

    def __init__(self, records, similar_records):
        super().__init__(records, similar_records)

    def _convert(self) -> str:
        output_records = {
            'main': [],
            DigestRecordContentType.NEWS.value: {content_category: [] for content_category in
                                                 DIGEST_RECORD_CONTENT_CATEGORY_VALUES},
            DigestRecordContentType.VIDEOS.value: {content_category: [] for content_category in
                                                   DIGEST_RECORD_CONTENT_CATEGORY_VALUES},
            DigestRecordContentType.ARTICLES.value: {content_category: [] for content_category in
                                                     DIGEST_RECORD_CONTENT_CATEGORY_VALUES},
            DigestRecordContentType.RELEASES.value: {content_category: [] for content_category in
                                                     DIGEST_RECORD_CONTENT_CATEGORY_VALUES},
            DigestRecordContentType.OTHER.value: [],
        }
        digest_records_ids_from_similar_records_item_records = []
        for similar_records_item in self._similar_records:
            similar_records_item_records = similar_records_item['digest_records']
            similar_records_item_records_included_to_digest = [dr for dr in similar_records_item_records if dr.state == DigestRecordState.IN_DIGEST]
            if not similar_records_item_records_included_to_digest:
                continue
            for similar_records_item_records_one in similar_records_item_records:
                digest_records_ids_from_similar_records_item_records.append(similar_records_item_records_one.drid)
            first_in_similar_records_item_records = similar_records_item_records_included_to_digest[0]
            if [dr for dr in similar_records_item_records_included_to_digest if dr.is_main]:
                output_records['main'].append(similar_records_item_records)
            elif first_in_similar_records_item_records.content_type == DigestRecordContentType.OTHER:
                output_records[first_in_similar_records_item_records.content_type.value].append(similar_records_item_records)
            elif not first_in_similar_records_item_records.is_main and first_in_similar_records_item_records.content_type in (DigestRecordContentType.NEWS,
                                                                                        DigestRecordContentType.ARTICLES,
                                                                                        DigestRecordContentType.VIDEOS,
                                                                                        DigestRecordContentType.RELEASES):
                if first_in_similar_records_item_records.content_category is not None:
                    output_records[first_in_similar_records_item_records.content_type.value][first_in_similar_records_item_records.content_category.value].append(
                        similar_records_item_records)
            else:
                pprint(similar_records_item)
                raise NotImplementedError
        for digest_record in self._records:
            if digest_record.state != DigestRecordState.IN_DIGEST:
                continue
            if digest_record.drid in digest_records_ids_from_similar_records_item_records:
                continue
            if digest_record.is_main:
                output_records['main'].append(digest_record)
            elif digest_record.content_type == DigestRecordContentType.OTHER:
                output_records[digest_record.content_type.value].append(digest_record)
            elif not digest_record.is_main and digest_record.content_type in (DigestRecordContentType.NEWS,
                                                                              DigestRecordContentType.ARTICLES,
                                                                              DigestRecordContentType.VIDEOS,
                                                                              DigestRecordContentType.RELEASES):
                if digest_record.content_category is not None:
                    output_records[digest_record.content_type.value][digest_record.content_category.value].append(digest_record)
            else:
                logger.error(f'Unsupported digest record data: {digest_record}')
                raise NotImplementedError
        output = '<h2>Главное</h2>\n\n'
        for main_record in output_records['main']:
            if not isinstance(main_record, list):
                output += f'<h3>{DigestRecordsCollection.clear_title(main_record.title)}</h3>\n\n'
                output += f'<i><b>Категория</b>: {DIGEST_RECORD_CONTENT_TYPE_RU_MAPPING[main_record.content_type.value]}/{DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING[main_record.content_category.value]}</i><br>\n\n'
                output += f'Подробности {DigestRecordsCollection.build_url_html(main_record.url, main_record.language)}\n\n'
            else:
                output += f'<h3>{[DigestRecordsCollection.clear_title(r.title) for r in main_record]}</h3>\n\n'
                output += f'<i><b>Категория</b>: {DIGEST_RECORD_CONTENT_TYPE_RU_MAPPING[main_record[0].content_type.value]}/{DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING[main_record[0].content_category.value]}</i><br>\n\n'
                output += 'Подробности:<br>\n\n'
                output += '<ol>\n'
                for r in main_record:
                    output += f'<li>{r.title} {DigestRecordsCollection.build_url_html(r.url, r.language)}</li>\n\n'
                output += '</ol>\n'

        output += '<h2>Короткой строкой</h2>\n\n'

        keys = (
            DigestRecordContentType.NEWS.value,
            DigestRecordContentType.VIDEOS.value,
            DigestRecordContentType.ARTICLES.value,
            DigestRecordContentType.RELEASES.value,
        )
        for key in keys:
            output += f'<h3>{DIGEST_RECORD_CONTENT_TYPE_RU_MAPPING[key]}</h3>\n\n'
            for key_record_content_category, key_records in output_records[key].items():
                if not key_records:
                    continue
                output += f'<h4>{DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING[key_record_content_category]}</h4>\n\n'
                if len(key_records) == 1:
                    key_record = key_records[0]
                    if not isinstance(key_record, list):
                        output += f'<p>{DigestRecordsCollection.clear_title(key_record.title)} {DigestRecordsCollection.build_url_html(key_record.url, key_record.language)}</p>\n'
                    else:
                        output += f'<p>{[DigestRecordsCollection.clear_title(r.title) for r in key_record]} {", ".join([DigestRecordsCollection.build_url_html(r.url, r.language) for r in key_record])}</p>\n'
                else:
                    output += '<ol>\n'
                    for key_record in key_records:
                        if not isinstance(key_record, list):
                            output += f'<li>{DigestRecordsCollection.clear_title(key_record.title)} {DigestRecordsCollection.build_url_html(key_record.url, key_record.language)}</li>\n'
                        else:
                            output += f'<li>{[DigestRecordsCollection.clear_title(r.title) for r in key_record]} {", ".join([DigestRecordsCollection.build_url_html(r.url, r.language) for r in key_record])}</li>\n'
                    output += '</ol>\n'

        if len(output_records[DigestRecordContentType.OTHER.value]):
            output += '<h2>Что ещё посмотреть</h2>\n\n'
            if len(output_records[DigestRecordContentType.OTHER.value]) == 1:
                other_record = output_records[DigestRecordContentType.OTHER.value][0]
                output += f'{DigestRecordsCollection.clear_title(other_record.title)} {DigestRecordsCollection.build_url_html(other_record.url, other_record.language)}<br>\n'
            else:
                output += '<ol>\n'
                for other_record in output_records[DigestRecordContentType.OTHER.value]:
                    output += f'<li>{DigestRecordsCollection.clear_title(other_record.title)} {DigestRecordsCollection.build_url_html(other_record.url, other_record.language)}</li>\n'
                output += '</ol>\n'
        return output


# TODO: Refactor
class DigestRecordsCollection(NetworkingMixin,
                              ServerConnectionMixin):

    def __init__(self,
                 config_path: str,
                 records: List[DigestRecord] = None,
                 bot_only: bool = True):
        self._config_path = config_path
        self.records = records if records is not None else []
        self.similar_records = []
        self._bot_only = bot_only
        self._token = None
        self._current_digest_issue = None

    def __str__(self):
        return pformat([record.to_dict() for record in self.records])

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
                'digest_issue': record_object.digest_issue,
                'content_type': record_object.content_type.value if record_object.content_type is not None else None,
                'content_category': record_object.content_category.value if record_object.content_category is not None else None,
            }
            records_plain.append(record_plain)
        with open(yaml_path, 'w') as fout:
            logger.info(f'Saving results to "{yaml_path}"')
            yaml.safe_dump(records_plain, fout)

    def load_specific_digest_records_from_server(self,
                                                 digest_issue: int):
        self._load_config(self._config_path)
        self._login()
        self._load_similar_records_for_specific_digest(digest_issue)
        self._basic_load_digest_records_from_server(f'{self.gatherer_api_url}/digest-record/detailed/?digest_issue={digest_issue}')

    @property
    def _unsorted_digest_record_endpoint(self):
        base_url = f'{self.gatherer_api_url}/digest-record/not-categorized/oldest/?project=FOSS News'
        if self._bot_only:
            return f'{base_url}&from-bot=true'
        else:
            return f'{base_url}&from-bot=false'

    @property
    def _unsorted_digest_records_count_endpoint(self):
        base_url = f'{self.gatherer_api_url}/digest-record/not-categorized/count/?project=FOSS News'
        if self._bot_only:
            return f'{base_url}&from-bot=true'
        else:
            return f'{base_url}&from-bot=false'

    def _load_one_new_digest_record_from_server(self):
        self._basic_load_digest_records_from_server(self._unsorted_digest_record_endpoint)

    def _load_tbot_categorization_data(self):
        self.records = []
        logger.info('Loading TBot categorization data')
        url = f'{self.tbot_api_url}/digest-record/categorized/'
        response = self.get_with_retries(url, headers=self._auth_headers)
        if response.status_code != 200:
            raise Exception(f'Failed to retrieve similar digest records, status code {response.status_code}, response: {response.content}')
        response_str = response.content.decode()
        response_data = json.loads(response_str)
        for digest_record_id, digest_record_data_and_estimations in response_data.items():
            digest_record_data = digest_record_data_and_estimations['record']
            estimations = digest_record_data_and_estimations['estimations']
            if digest_record_data['dt'] is not None:
                dt_str = datetime.datetime.strptime(digest_record_data['dt'],
                                                    FNGS_DATETIME_FORMAT)
            else:
                dt_str = None
            record_object = DigestRecord(dt_str,
                                         digest_record_data['source'],
                                         digest_record_data['title'],
                                         digest_record_data['url'],
                                         digest_record_data['additional_url'],
                                         state=DigestRecordState(digest_record_data['state'].lower()),
                                         content_type=DigestRecordContentType(digest_record_data['content_type'].lower()) if digest_record_data['content_type'] else None,
                                         content_category=DigestRecordContentCategory(digest_record_data['content_category'].lower() if digest_record_data['content_category'] != 'DATABASES' else 'db') if digest_record_data['content_category'] else None,
                                         digest_issue=digest_record_data['digest_issue'],
                                         drid=digest_record_id,
                                         language=digest_record_data['language'],
                                         is_main=digest_record_data['is_main'],
                                         keywords=digest_record_data['title_keywords'],
                                         estimations=[{'user': e['user'],
                                                       'state': DigestRecordState(e['state'].lower()),
                                                       'is_main': e['is_main'],
                                                       'content_type': DigestRecordContentType(e['content_type'].lower()) if e['content_type'] else None,
                                                       'content_category': DigestRecordContentCategory(e['content_category'].lower() if e['content_category'] != 'DATABASES' else 'db') if e['content_category'] else None}
                                                      for e in estimations])
            self.records.append(record_object)


    def _load_similar_records_for_specific_digest(self,
                                                  digest_issue: int):
        logger.info(f'Getting similar digest records for digest number #{digest_issue}')
        url = f'{self.gatherer_api_url}/similar-digest-record/detailed/?digest_issue={digest_issue}'
        results = self.get_results_from_all_pages(url, self._auth_headers)
        response_converted = []
        for similar_records_item in results:
            similar_records_item_converted = {}
            for key in ('id', 'digest_issue'):
                similar_records_item_converted[key] = similar_records_item[key]
            if not similar_records_item['digest_records']:
                logger.warning(f'Empty digest records list in similar records #{similar_records_item["id"]}')
                continue
            similar_records_item_converted['digest_records'] = []
            for record in similar_records_item['digest_records']:
                if record['dt'] is not None:
                    dt_str = datetime.datetime.strptime(record['dt'],
                                                        FNGS_DATETIME_FORMAT)
                else:
                    dt_str = None
                record_obj = DigestRecord(dt_str,
                                          None,
                                          record['title'],
                                          record['url'],
                                          record['additional_url'],
                                          digest_issue=record['digest_issue'],
                                          drid=record['id'],
                                          is_main=record['is_main'],
                                          keywords=record['title_keywords'],
                                          language=record['language'])
                record_obj.state = DigestRecordState(record['state'].lower()) if 'state' in record and record['state'] is not None else None
                record_obj.content_type = DigestRecordContentType(record['content_type'].lower()) if 'content_type' in record and record['content_type'] is not None else None
                if 'content_category' in record and record['content_category'] == 'DATABASES':
                    record['content_category'] = 'db'
                record_obj.content_category = DigestRecordContentCategory(record['content_category'].lower()) if 'content_category' in record and record['content_category'] is not None else None
                similar_records_item_converted['digest_records'].append(record_obj)
            response_converted.append(similar_records_item_converted)
        self.similar_records += response_converted


    def _basic_load_digest_records_from_server(self, url: str):
        records_objects: List[DigestRecord] = []
        logger.info('Getting digest records')
        results = self.get_results_from_all_pages(url, self._auth_headers)
        for record_plain in results:
            if record_plain['dt'] is not None:
                dt_str = datetime.datetime.strptime(record_plain['dt'],
                                                    FNGS_DATETIME_FORMAT)
            else:
                dt_str = None
            record_object = DigestRecord(dt_str,
                                         None,
                                         record_plain['title'],
                                         record_plain['url'],
                                         record_plain['additional_url'],
                                         digest_issue=record_plain['digest_issue'],
                                         drid=record_plain['id'],
                                         is_main=record_plain['is_main'],
                                         keywords=record_plain['title_keywords'],
                                         language=record_plain['language'],
                                         estimations=[{'user': e['telegram_bot_user']['username'],
                                                       'state': DigestRecordState(e['estimated_state'].lower())}
                                                      for e in record_plain['tbot_estimations']])
            record_object.state = DigestRecordState(record_plain['state'].lower()) if 'state' in record_plain and record_plain['state'] is not None else None
            record_object.content_type = DigestRecordContentType(record_plain['content_type'].lower()) if 'content_type' in record_plain and record_plain['content_type'] is not None else None
            if 'content_category' in record_plain and record_plain['content_category'] == 'DATABASES':
                record_plain['content_category'] = 'db'
            record_object.content_category = DigestRecordContentCategory(record_plain['content_category'].lower()) if 'content_category' in record_plain and record_plain['content_category'] is not None else None
            records_objects.append(record_object)
        self.records = records_objects

    @staticmethod
    def clear_title(title: str):
        fixed_title = html.unescape(title)
        return fixed_title

    @staticmethod
    def build_url_html(url: str, lang: Language, do_not_mark_language: bool = False, link_text: str = None):
        if not isinstance(lang, Language):
            raise Exception('"lang" variable should be instance of "Language" class')
        patterns_to_clear = (
            '\?rss=1$',
            r'#ftag=\w+$',
            '[&?]utm_source=rss&utm_medium=rss&utm_campaign=.*$',
        )
        for pattern_to_clear in patterns_to_clear:
            url = re.sub(pattern_to_clear, '', url)
        return f'{"!!! " if "!!! " in url else ""}<a href="{url.replace("!!! ", "")}">{link_text if link_text is not None else url.replace("!!! ", "")}</a>{" (en)" if lang == Language.ENGLISH and not do_not_mark_language else ""}'  # TODO: Remove "!!! " replacement after Reddit converter refactoring

    def records_to_html(self, format_name, html_path):
        if format_name == HtmlFormat.HABR.name:
            converter = HabrDbToHtmlConverter(self.records, self.similar_records)
        elif format_name == HtmlFormat.REDDIT.name:
            converter = RedditDbToHtmlConverter(self.records, self.similar_records)
        else:
            raise NotImplementedError
        converter.convert(html_path)

    def _guess_content_type(self, title: str, url: str) -> DigestRecordContentType:
        if 'https://www.youtube.com' in url:
            return DigestRecordContentType.VIDEOS
        if 'SD Times Open-Source Project of the Week' in title:
            return DigestRecordContentType.OTHER
        if 'weeklyOSM' in title:
            return DigestRecordContentType.NEWS
        if re.search(r'DEF CON \d+ Cloud Village', title):
            return DigestRecordContentType.VIDEOS
        for release_keyword in RELEASES_KEYWORDS:
            if release_keyword.lower() in title.lower():
                return DigestRecordContentType.RELEASES
        for article_keyword in ARTICLES_KEYWORDS:
            if article_keyword.lower() in title.lower():
                return DigestRecordContentType.ARTICLES

        for keyword_data in self._keywords():
            if not keyword_data['is_generic']:
                keyword_name_fixed = keyword_data['name'].replace('+', r'\+')
                if re.search(keyword_name_fixed + r',?\s+v?\.?\d', title, re.IGNORECASE):
                    return DigestRecordContentType.RELEASES
        return None

    def _keywords(self):
        url = f'{self.gatherer_api_url}/keyword?page_size=5000'
        results = self.get_results_from_all_pages(url, self._auth_headers)
        return results

    def _show_similar_from_previous_digest(self, keywords: List[Dict]):
        if not keywords:
            logger.debug('Could not search for similar records from previous digest cause keywords list is empty')
            return
        url = f'{self.gatherer_api_url}/digest-issue/{self._current_digest_issue}/previous/similar-records/?keywords={",".join([k["name"] for k in keywords])}'
        response = self.get_with_retries(url, self._auth_headers)
        if response.status_code != 200:
            logger.error(f'Failed to retrieve guessed subcategories, status code {response.status_code}, response: {response.content}')
            raise Exception('Failed to retrieve guessed subcategories')
        response_str = response.content.decode()
        response = json.loads(response_str)
        if response:
            similar_records_in_previous_digest = response
            if similar_records_in_previous_digest:
                print(f'Similar records in previous digest:')
                for record in similar_records_in_previous_digest:
                    is_main_ru = "главная" if record["is_main"] else "не главная"
                    if record["content_type"]:
                        content_type_ru = DIGEST_RECORD_CONTENT_TYPE_RU_MAPPING[DigestRecordContentType.from_name(record["content_type"]).value].lower()
                    else:
                        content_type_ru = None
                    if record["content_category"]:
                        content_category_ru = DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING[DigestRecordContentCategory.from_name(record["content_category"]).value].lower()
                    else:
                        content_category_ru = None
                    print(f'- {record["title"]} ({is_main_ru}, {content_type_ru}, {content_category_ru}) - {record["url"]}')

    def _guess_content_category(self, record_title: str, record_url: str) -> (List[DigestRecordContentCategory], Dict):
        if 'weeklyOSM' in record_title:
            return [DigestRecordContentCategory.ORG], {}
        if re.search(r'DEF CON \d+ Cloud Village', record_title):
            return [DigestRecordContentCategory.SECURITY], {}

        url = f'{self.gatherer_api_url}/content-category/guess/?title={record_title}'
        response = self.get_with_retries(url, self._auth_headers)
        if response.status_code != 200:
            logger.error(f'Failed to retrieve guessed content categories, status code {response.status_code}, response: {response.content}')
            # TODO: Raise exception and handle above
            return None
        response_str = response.content.decode()
        response = json.loads(response_str)
        # TODO: Check title
        matches = response['matches']

        guessed_content_categories: List[DigestRecordContentCategory] = []
        matched_subcategories_keywords = {}

        for guessed_content_category_name, matched_keywords in matches.items():
            if not guessed_content_category_name or guessed_content_category_name == 'null':
                continue
            subcategory = DigestRecordContentCategory(guessed_content_category_name.lower()
                                                      if guessed_content_category_name != 'DATABASES'
                                                      else 'db')
            guessed_content_categories.append(subcategory)
            matched_subcategories_keywords[guessed_content_category_name.lower()] = matched_keywords

        diy_category = DigestRecordContentCategory('diy')
        if 'https://hackaday.com' in record_url and diy_category not in guessed_content_categories:
            guessed_content_categories.append(diy_category)

        return guessed_content_categories, matched_subcategories_keywords

    def categorize_interactively(self):
        self._load_config(self._config_path)
        self._login()
        while True:
            if self._current_digest_issue is None:
                self._current_digest_issue = self._ask_digest_issue()
            self._print_non_categorized_digest_records_count()
            # self._print_non_categorized_digest_records_count()
            self._load_tbot_categorization_data()
            if self.records:
                # TODO: Think how to process left record in non-conflicting with Tbot usage way
                self._process_estimations_from_tbot()
                # self._print_non_categorized_digest_records_count()
            if not self.records:
                self._load_one_new_digest_record_from_server()
            self._categorize_new_records()
            if self._non_categorized_digest_records_count() == 0:
                logger.info('No uncategorized digest records left')
                break

    def _print_non_categorized_digest_records_count(self):
        left_to_process_count = self._non_categorized_digest_records_count()
        print(f'Digest record(s) left to process: {left_to_process_count}')

    def _non_categorized_digest_records_count(self):
        response = self.get_with_retries(url=self._unsorted_digest_records_count_endpoint,
                                         headers=self._auth_headers)
        response_str = response.content.decode()
        response_data = json.loads(response_str)
        return response_data['count']

    def _admins_estimation(self, estimations):
        # TODO: Support multiple admins estimations
        admins_estimations = [e for e in estimations if e['user'] == 'gim6626']
        return admins_estimations[0] if admins_estimations else None

    def _process_estimations_from_tbot(self):
        # TODO: Refactor, split into steps and extract them into separate methods and extract common selection code
        ignore_candidates_records = []
        approve_candidates_records = []
        records_with_is_main_estimation = []
        records_with_content_type_estimation = []
        records_with_content_category_estimation = []
        for record in self.records:
            if not record.estimations:
                continue
            if record.state == DigestRecordState.UNKNOWN:
                ignore_state_votes_count = len([estimation for estimation in record.estimations if estimation['state'] == DigestRecordState.IGNORED])
                ignore_vote_by_admin = len([estimation for estimation in record.estimations if estimation['user'] == 'gim6626' and estimation['state'] == DigestRecordState.IGNORED]) > 0  # TODO: Replace hardcode with some DB query on backend
                total_state_votes_count = len(record.estimations)
                if ignore_state_votes_count / total_state_votes_count > 0.5 and total_state_votes_count > 1 or ignore_vote_by_admin:
                    ignore_candidates_records.append(record)
                approve_state_votes_count = len([estimation for estimation in record.estimations if estimation['state'] == DigestRecordState.IN_DIGEST])
                approve_vote_by_admin = len([estimation for estimation in record.estimations if estimation['user'] == 'gim6626' and estimation['state'] == DigestRecordState.IN_DIGEST]) > 0  # TODO: Replace hardcode with some DB query on backend
                total_state_votes_count = len(record.estimations)
                if approve_state_votes_count / total_state_votes_count > 0.5 and total_state_votes_count > 1 or approve_vote_by_admin:
                    approve_candidates_records.append(record)
            if self._admins_estimation(record.estimations):
                if record.is_main is None:
                    for estimation in record.estimations:
                        if estimation['is_main'] is not None and record.url not in [r.url for r in records_with_is_main_estimation]:
                            records_with_is_main_estimation.append(record)
                if record.content_type is None:
                    for estimation in record.estimations:
                        if estimation['content_type'] is not None:
                            records_with_content_type_estimation.append(record)
                if record.content_category is None:
                    for estimation in record.estimations:
                        if estimation['content_category'] is not None:
                            records_with_content_category_estimation.append(record)

        records_left_from_tbot = []
        if ignore_candidates_records:
            print('Candidates to ignore:')
            for ignore_candidate_record_i, ignore_candidate_record in enumerate(ignore_candidates_records):
                print(f'{ignore_candidate_record_i + 1}. {ignore_candidate_record.title} {ignore_candidate_record.url}')
            do_not_ignore_records_indexes = self._ask_all_or_skipped_indexes('Approve all records ignoring with typing "all" or comma-separated input records indexes which you want to left non-ignored: ')
            records_to_ignore = [ignore_candidate_record
                                 for ignore_candidate_record_i, ignore_candidate_record in enumerate(ignore_candidates_records)
                                 if ignore_candidate_record_i not in do_not_ignore_records_indexes]
            if records_to_ignore:
                logger.info('Uploading data')
                for record_to_ignore_i, record_to_ignore in enumerate(records_to_ignore):
                    record_to_ignore.digest_issue = self._current_digest_issue
                    record_to_ignore.state = DigestRecordState.IGNORED
                    self._upload_record(record_to_ignore, ['state'])

            # TODO: Research if this is really needed because records are taken from server
            # records_left_from_tbot += [digest_record
            #                            for digest_record_i, digest_record in
            #                            enumerate(ignore_candidates_records)
            #                            if digest_record_i in do_not_ignore_records_indexes]

        if approve_candidates_records:
            print('Candidates to approve:')
            for approve_candidate_record_i, approve_candidate_record in enumerate(approve_candidates_records):
                print(f'{approve_candidate_record_i + 1}. {approve_candidate_record.title} {approve_candidate_record.url}')
            do_not_approve_records_indexes = self._ask_all_or_skipped_indexes('Approve all records inclusion in digest with typing "all" or comma-separated input records indexes which you want to left to be processed separately: ')
            records_to_approve = [approve_candidate_record
                                  for approve_candidate_record_i, approve_candidate_record in enumerate(approve_candidates_records)
                                  if approve_candidate_record_i not in do_not_approve_records_indexes]
            if records_to_approve:
                logger.info('Uploading data')
                for record_to_approve_i, record_to_approve in enumerate(records_to_approve):
                    record_to_approve.digest_issue = self._current_digest_issue
                    record_to_approve.state = DigestRecordState.IN_DIGEST
                    self._upload_record(record_to_approve, ['state'])

            # TODO: Research if this is really needed because records are taken from server
            # records_left_from_tbot += [digest_record
            #                            for digest_record_i, digest_record in
            #                            enumerate(approve_candidates_records)
            #                            if digest_record_i in do_not_approve_records_indexes]

        if records_with_is_main_estimation:
            print('Main or not main estimations from Telegram bot to process:')
            for mark_as_main_record_i, mark_as_main_record in enumerate(records_with_is_main_estimation):
                # TODO: Add support for multiple estimations
                print(f'{mark_as_main_record_i + 1}. {"MAIN" if self._admins_estimation(mark_as_main_record.estimations)["is_main"] else "NOT MAIN"} {mark_as_main_record.title} {mark_as_main_record.url}')
            not_accepted_estimations_records_indexes = self._ask_all_or_skipped_indexes('Approve all specified above records "is_main" estimations with typing "all" or specify comma-separated list of records indexes to ignore estimation and process separately: ')
            records_with_approved_estimations = [digest_record
                                                 for digest_record_i, digest_record in
                                                 enumerate(records_with_is_main_estimation)
                                                 if digest_record_i not in not_accepted_estimations_records_indexes]
            if records_with_approved_estimations:
                logger.info('Uploading data')
                for record_with_approved_estimations in records_with_approved_estimations:
                    # TODO: Add support for multiple estimations
                    record_with_approved_estimations.is_main = record_with_approved_estimations.estimations[0]['is_main']
                    self._upload_record(record_with_approved_estimations, ['is_main'])

        if records_with_content_type_estimation:
            print('Content type estimations from Telegram bot to process:')
            for estimated_record_i, estimated_record in enumerate(records_with_content_type_estimation):
                # TODO: Add support for multiple estimations
                print(f'{estimated_record_i + 1}. {self._admins_estimation(estimated_record.estimations)["content_type"].name} {estimated_record.title} {estimated_record.url}')
            not_accepted_estimations_records_indexes = self._ask_all_or_skipped_indexes('Approve all specified above content type estimations with typing "all" or specify comma-separated list of records indexes to ignore estimation and process separately: ')
            records_with_approved_estimations = [digest_record
                                                 for digest_record_i, digest_record in
                                                 enumerate(records_with_content_type_estimation)
                                                 if digest_record_i not in not_accepted_estimations_records_indexes]
            if records_with_approved_estimations:
                logger.info('Uploading data')
                for record_with_approved_estimations in records_with_approved_estimations:
                    # TODO: Add support for multiple estimations
                    record_with_approved_estimations.content_type = self._admins_estimation(record_with_approved_estimations.estimations)['content_type']
                    self._upload_record(record_with_approved_estimations, ['content_type'])

        if records_with_content_category_estimation:
            print('Content category estimations from Telegram bot to process:')
            for estimated_record_i, estimated_record in enumerate(records_with_content_category_estimation):
                # TODO: Add support for multiple estimations
                print(f'{estimated_record_i + 1}. {self._admins_estimation(estimated_record.estimations)["content_category"].name} {estimated_record.title} {estimated_record.url}')
            not_accepted_estimations_records_indexes = self._ask_all_or_skipped_indexes('Approve all specified above content category estimations with typing "all" or specify comma-separated list of records indexes to ignore estimation and process separately: ')
            records_with_approved_estimations = [digest_record
                                                 for digest_record_i, digest_record in
                                                 enumerate(records_with_content_category_estimation)
                                                 if digest_record_i not in not_accepted_estimations_records_indexes]
            if records_with_approved_estimations:
                logger.info('Uploading data')
                for record_with_approved_estimations in records_with_approved_estimations:
                    # TODO: Add support for multiple estimations
                    record_with_approved_estimations.content_category = self._admins_estimation(record_with_approved_estimations.estimations)['content_category']
                    self._upload_record(record_with_approved_estimations, ['content_category'])

        # TODO: Research if this is really needed because records are taken from server
        # self.records = records_left_from_tbot

    def _ask_all_or_skipped_indexes(self, question):
        while True:
            answer = input(question)
            if answer == 'all':
                skipped_indexes = []
                break
            elif re.fullmatch(r'[0-9]+(,[0-9]+)*?', answer):
                skipped_indexes = [int(i) - 1 for i in answer.split(',')]
                break
            else:
                print('Invalid answer, please input "all" or comma-separated indexes list')
                continue
        return skipped_indexes

    def _categorize_new_records(self):
        for record in self.records:
            self._print_non_categorized_digest_records_count()
            # TODO: Rewrite using FSM
            logger.info(f'Processing record "{record.title}" from date {record.dt}')
            print(f'New record:\n{record}')
            if record.state == DigestRecordState.UNKNOWN:
                self._show_similar_from_previous_digest(record.keywords)
                record.state = self._ask_state(record)
            if record.digest_issue is None:
                record.digest_issue = self._current_digest_issue
            if record.state in (DigestRecordState.IN_DIGEST,
                                DigestRecordState.OUTDATED):
                if record.is_main is None:
                    is_main = self._ask_bool(f'Please input whether or no "{record.title}" is main (y/n): ')
                    logger.info(f'{"Marking" if is_main else "Not marking"} "{record.title}" as one of main records')
                    record.is_main = is_main

                if record.content_type is None or record.content_type == DigestRecordContentType.UNKNOWN:
                    guessed_content_type = self._guess_content_type(record.title, record.url)
                    if guessed_content_type is not None:
                        msg = f'Guessed content_type is "{DIGEST_RECORD_CONTENT_TYPE_RU_MAPPING[guessed_content_type.value]}". Accept? y/n: '
                        accepted = self._ask_bool(msg)
                        if accepted:
                            logger.info(f'Setting content_type of record "{record.title}" to "{DIGEST_RECORD_CONTENT_TYPE_RU_MAPPING[guessed_content_type.value]}"')
                            record.content_type = guessed_content_type

                    if guessed_content_type != DigestRecordContentType.OTHER and record.content_category is None:
                        guessed_content_categories, matched_subcategories_keywords = self._guess_content_category(record.title, record.url)
                        if guessed_content_categories:
                            if matched_subcategories_keywords:
                                matched_subcategories_keywords_translated = {}
                                for matched_content_category, keywords in matched_subcategories_keywords.items():
                                    matched_subcategories_keywords_translated[DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING[matched_content_category if matched_content_category != 'databases' else 'db']] = keywords
                                print(f'Matched subcategories keywords:\n{pformat(matched_subcategories_keywords_translated)}')
                            if len(guessed_content_categories) == 1:
                                guessed_content_category = guessed_content_categories[0]
                                msg = f'Guessed content_category is "{DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING[guessed_content_category.value]}". Accept? y/n: '
                                accepted = self._ask_bool(msg)
                                if accepted:
                                    logger.info(f'Setting content_category of record "{record.title}" to "{DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING[guessed_content_category.value]}"')
                                    record.content_category = guessed_content_category
                            else:
                                msg = f'Guessed subcategories are:'
                                for guessed_content_category_i, guessed_content_category in enumerate(guessed_content_categories):
                                    msg += f'\n{guessed_content_category_i + 1}. {DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING[guessed_content_category.value]}'
                                msg += f'\nType guessed content_category index or "n" if no match: '
                                guessed_content_category_index = self._ask_guessed_content_category_index(msg,
                                                                                                len(guessed_content_categories))
                                if guessed_content_category_index is not None:
                                    guessed_content_category = guessed_content_categories[guessed_content_category_index - 1]
                                    logger.info(f'Setting content_category of record "{record.title}" to "{DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING[guessed_content_category.value]}"')
                                    record.content_category = guessed_content_category

                if record.content_type == DigestRecordContentType.UNKNOWN or record.content_type is None:
                    record.content_type = self._ask_content_type(record,
                                                             DIGEST_RECORD_CONTENT_TYPE_RU_MAPPING)
                if record.content_category is None:
                    if record.content_type != DigestRecordContentType.OTHER:
                        record.content_category = self._ask_content_category(record,
                                                                        DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING)

                if record.state == DigestRecordState.IN_DIGEST \
                        and record.content_type is not None \
                        and record.content_category is not None:
                    current_records_with_similar_categories = self._similar_digest_records(record.digest_issue,
                                                                                           record.content_type,
                                                                                           record.content_category)
                    similar_records_lists_without_record_itself = {}
                    similar_records_without_record_itself = []
                    if current_records_with_similar_categories:
                        for similar_records in current_records_with_similar_categories['similar_records']:
                            similar_records_one_without_record_itself = []
                            for dr in similar_records['digest_records']:
                                if dr['url'] != record.url:
                                    similar_records_one_without_record_itself.append(dr)
                            if similar_records_one_without_record_itself:
                                similar_records_lists_without_record_itself[similar_records['id']] = similar_records_one_without_record_itself
                    if current_records_with_similar_categories:
                        for similar_record in current_records_with_similar_categories['records']:
                            if similar_record['url'] != record.url:
                                similar_records_without_record_itself.append(similar_record)
                    if similar_records_lists_without_record_itself or similar_records_without_record_itself:
                        if len(similar_records_lists_without_record_itself) + len(similar_records_without_record_itself) == 1:
                            if similar_records_lists_without_record_itself:
                                obj = list(similar_records_lists_without_record_itself.values())[0]
                                text = f'[{"; ".join([dr["title"] + " " + dr["url"] for dr in obj])}]'
                                options_indexes = [list(similar_records_lists_without_record_itself.keys())[0]]
                            else:
                                obj = similar_records_without_record_itself[0]
                                text = f'"{obj["title"]}" {obj["url"]}'
                                options_indexes = [obj['id']]
                            question = f'Is the record(s) {text} similar to current (y/n)? '
                            confirmation = self._ask_bool(question)
                            if confirmation:
                                option_index = 0
                            else:
                                option_index = None
                        else:
                            print(f'Are there any similar records for digest record "{record.title}" ({record.url})? Here is list of possible ones:')
                            i = 1
                            options_indexes = []
                            for option_id, option_values in similar_records_lists_without_record_itself.items():
                                print(f'{i}. {"; ".join([dr["title"] + " " + dr["url"] for dr in option_values])}')
                                options_indexes.append(option_id)
                                i += 1
                            for option in similar_records_without_record_itself:
                                print(f'{i}. {option["title"]} {option["url"]}')
                                options_indexes.append(option['id'])
                                i += 1
                            option_index = self._ask_option_index_or_no(i - 1)
                        print(Style.RESET_ALL, end='')
                        if option_index is not None:
                            if current_records_with_similar_categories['similar_records'] and option_index <= len(current_records_with_similar_categories['similar_records']):
                                existing_drids = []
                                for option in current_records_with_similar_categories['similar_records']:
                                    if option['id'] == options_indexes[option_index - 1]:
                                        existing_drids = [dr['id'] for dr in option['digest_records']]
                                self._add_digest_record_do_similar(options_indexes[option_index - 1], existing_drids, record.drid)
                                logger.info('Added to existing similar records item')  # TODO: More details
                            else:
                                self._create_similar_digest_records_item(record.digest_issue, [options_indexes[option_index - 1], record.drid])
                                logger.info('New similar records item created')  # TODO: More details
                        else:
                            logger.info('No similar records specified')
                    else:
                        logger.info('Similar digest records not found')

            self._upload_record(record)

    def _upload_record(self, record, additional_fields_keys=None):
        logger.info(f'Uploading record #{record.drid} to FNGS')
        url = f'{self.gatherer_api_url}/digest-record/{record.drid}/'
        base_fields = {
            'id': record.drid,
            'digest_issue': record.digest_issue,
        }
        all_additional_fields = {
            'state': record.state.name if record.state is not None else None,
            'is_main': record.is_main,
            'content_type': record.content_type.name if record.content_type is not None else None,
            'content_category': record.content_category.name if record.content_category is not None else None,
        }
        if additional_fields_keys is None:
            additional_fields = all_additional_fields
        else:
            additional_fields = {k: v for k, v in all_additional_fields.items() if k in additional_fields_keys}
        selected_fields = dict(**base_fields, **additional_fields)
        data = json.dumps(selected_fields)
        response = self.patch_with_retries(url=url,
                                           headers=self._auth_headers,
                                           data=data)
        if response.status_code != 200:
            raise Exception(f'Invalid response code from FNGS patch - {response.status_code} (request data was {data}): {response.content.decode("utf-8")}')
        logger.info(f'Uploaded record #{record.drid} for digest #{record.digest_issue} to FNGS')
        logger.info(f'If you want to change some parameters that you\'ve set - go to {self.admin_url}/gatherer/digestrecord/{record.drid}/change/')

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

    def _ask_digest_issue(self):
        while True:
            digest_issue_str = input(f'Please input current digest number: ')
            if digest_issue_str.isnumeric():
                digest_issue = int(digest_issue_str)
                return digest_issue
            else:
                print('Invalid digest number, it should be integer')
        raise NotImplementedError

    def _ask_guessed_content_category_index(self,
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

    def _ask_content_type(self,
                      record: DigestRecord,
                      translations: Dict[str, str] = None):
        return self._ask_enum('digest record content_type', DigestRecordContentType, record, translations)

    def _ask_content_category(self,
                         record: DigestRecord,
                         translations: Dict[str, str] = None):
        enum_name = 'digest record content_category'
        if record.content_type != DigestRecordContentType.UNKNOWN and record.content_type != DigestRecordContentType.OTHER:
            return self._ask_enum(enum_name, DigestRecordContentCategory, record, translations)
        else:
            raise NotImplementedError

    def _similar_digest_records(self,
                                digest_issue,
                                content_type,
                                content_category):
        logger.debug(f'Getting records looking similar for digest number #{digest_issue}, content_type "{content_type.value}" and content_category "{content_category.value}"')
        url = f'{self.gatherer_api_url}/digest-record/similar/?digest_issue={digest_issue}&content_type={content_type.name}&content_category={content_category.name}'
        results = self.get_results_from_all_pages(url, self._auth_headers, timeout=5*NETWORK_TIMEOUT_SECONDS)
        if not results:
            logger.info('No similar records found')
            return None
        options_similar_records = []
        options_records = []
        for similar_record_i, similar_record in enumerate(results):
            similar_records_item = similar_record['similar_records']
            if similar_records_item:
                for similar_records_item_one in similar_records_item:
                    options_similar_records.append(similar_records_item_one)
            else:
                options_records.append({'id': similar_record['id'], 'title': similar_record['title'], 'url': similar_record['url']})
        options_similar_records_filtered = []
        for option_similar_records_one in options_similar_records:
            similar_digest_records = []
            for similar_digest_records_record in option_similar_records_one['digest_records']:
                similar_digest_records.append({'id': similar_digest_records_record['id'], 'title': similar_digest_records_record['title'], 'url': similar_digest_records_record['url']})
            exists = False
            for option_similar_records_filtered in options_similar_records_filtered:
                if option_similar_records_filtered['id'] == option_similar_records_one['id']:
                    exists = True
                    break
            if not exists:
                options_similar_records_filtered.append({'id': option_similar_records_one['id'], 'digest_records': similar_digest_records})
        return {
            'similar_records': options_similar_records_filtered,
            'records': options_records,
        }

    def _add_digest_record_do_similar(self, similar_digest_records_item_id, existing_drids, digest_record_id):
        logger.debug(f'Adding digest record #{digest_record_id} to similar digest records item #{similar_digest_records_item_id}')
        url = f'{self.gatherer_api_url}/similar-digest-record/{similar_digest_records_item_id}/'
        data = {
            'id': similar_digest_records_item_id,
            'digest_records': existing_drids + [digest_record_id],
        }
        response = self.patch_with_retries(url=url,
                                           data=json.dumps(data),
                                           headers=self._auth_headers)
        if response.status_code != 200:
            logger.error(f'Failed to update similar digest records item, status code {response.status_code}, response: {response.content}')
            # TODO: Raise exception and handle above

    def _create_similar_digest_records_item(self,
                                            digest_issue,
                                            digest_records_ids,
                                            ):
        logger.debug(f'Creating similar digest records item from #{digest_records_ids}')
        url = f'{self.gatherer_api_url}/similar-digest-record/'
        data = {
            'digest_issue': digest_issue,
            'digest_records': digest_records_ids,
        }
        logger.debug(f'POSTing data {data} to URL {url}')
        response = self.post_with_retries(url,
                                          data=json.dumps(data),
                                          headers=self._auth_headers)
        if response.status_code != 201:
            logger.error(f'Failed to create similar digest records item, status code {response.status_code}, response: {response.content}')
            # TODO: Raise exception and handle above

    def _digest_record_by_id(self, digest_record_id):
        logger.debug(f'Loading digest record #{digest_record_id}')
        url = f'{self.gatherer_api_url}/digest-record/{digest_record_id}'
        response = self.get_with_retries(url, headers=self._auth_headers)
        if response.status_code != 200:
            logger.error(f'Failed to retrieve digest record, status code {response.status_code}, response: {response.content}')
            # TODO: Raise exception and handle above
            return None
        # logger.debug(f'Received response: {response.content}')  # TODO: Make "super debug" level and enable for it only
        response_str = response.content.decode()
        response = json.loads(response_str)
        if not response:
            # TODO: Raise exception and handle above
            logger.error('No digest record in response')
            return None
        return response

    def _similar_digest_records_by_digest_record(self, digest_record_id):
        logger.debug(f'Checking if there are similar records for digest record #{digest_record_id}')
        url = f'{self.gatherer_api_url}/similar-digest-record/detailed/?digest_record={digest_record_id}'
        results = self.get_results_from_all_pages(url, self._auth_headers)
        if not results:
            logger.debug(f'No similar records found for digest record #{digest_record_id}')
            return None
        return results[0] # TODO: Handle multiple case

    def _ask_enum(self,
                  enum_name,
                  enum_class,
                  record: DigestRecord,
                  translations: Dict[str, str] = None):
        while True:
            logger.info(f'Waiting for {enum_name}')
            print(f'Available values:')
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
