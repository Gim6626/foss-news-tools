import sys
import time
from abc import ABCMeta, abstractmethod
from typing import List, Dict
from enum import Enum
import datetime
import requests
import xml.etree.ElementTree as ET
import dateutil.parser
from lxml import html
import logging
import re


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


def shorten_text(s: str, max_length: int = 20):
    if len(s) < max_length:
        return s
    else:
        return s[:max_length - 3] + '...'


class PostData:

    def __init__(self,
                 dt: datetime.datetime,
                 title: str,
                 url: str,
                 brief: str):
        self.dt = dt
        self.title = title
        self.url = url
        self.brief = brief

    def __str__(self):
        return f'{self.dt} -- {self.url} -- {self.title} -- {shorten_text(self.brief)}'


class PostsData:

    def __init__(self,
                 source_name: str,
                 posts_data_list: List[PostData],
                 warning: str = None):
        self.source_name = source_name
        self.posts_data_list = posts_data_list
        self.warning = warning


class ParsingModuleType(Enum):
    OPEN_NET_RU = 'OpenNetRu'
    LINUX_COM = 'LinuxCom'
    OPEN_SOURCE_COM = 'OpenSourceCom'
    ITS_FOSS_COM = 'ItsFossCom'
    LINUX_ORG_RU = 'LinuxOrgRu'
    HABR_COM_OPEN_SOURCE = 'HabrComOpenSource'
    HABR_COM_LINUX = 'HabrComLinux'
    HABR_COM_LINUX_DEV = 'HabrComLinuxDev'
    HABR_COM_NIX = 'HabrComNix'
    HABR_COM_DEVOPS = 'HabrComDevOps'
    HABR_COM_SYS_ADM = 'HabrComSysAdm'
    HABR_COM_GIT = 'HabrComGit'
    YOUTUBE_COM_ALEKSEY_SAMOILOV = 'YouTubeComAlekseySamoilov'
    LOSST_RU = 'LosstRu'
    PINGVINUS_RU = 'PingvinusRu'


PARSING_MODULES_TYPES = tuple((t.value for t in ParsingModuleType))


class BasicParsingModule(metaclass=ABCMeta):

    source_name = None
    warning = None

    def parse(self) -> List[PostData]:
        posts_data: List[PostData] = self._parse()
        filtered_posts_data: List[PostData] = self._filter_out_old(posts_data)
        return filtered_posts_data

    @abstractmethod
    def _parse(self) -> List[PostData]:
        pass

    def _filter_out_old(self, posts_data: List[PostData]) -> List[PostData]:
        filtered_posts_data: List[PostData] = []
        dt_now = datetime.datetime.now(tz=dateutil.tz.tzlocal())
        for post_data in posts_data:
            dt_diff = dt_now - post_data.dt
            if dt_diff.days > days_count:
                logger.debug(f'"{post_data.title}" from "{self.source_name}" filtered as too old ({post_data.dt})')
            else:
                filtered_posts_data.append(post_data)
        return filtered_posts_data


class RssBasicParsingModule(BasicParsingModule):

    rss_url = None
    item_tag_name = None
    title_tag_name = None
    pubdate_tag_name = None
    link_tag_name = None
    description_tag_name = None

    def __init__(self):
        self.rss_data_root = None

    def _parse(self):
        posts_data: List[PostData] = []
        response = requests.get(self.rss_url)
        # TODO: Check response code
        self.rss_data_root = ET.fromstring(response.text)
        for rss_data_elem in self.rss_items_root():
            if self.item_tag_name in rss_data_elem.tag:
                dt = None
                title = None
                url = None
                brief = None
                for rss_data_subelem in rss_data_elem:
                    tag = rss_data_subelem.tag
                    text = rss_data_subelem.text
                    if self.title_tag_name in tag:
                        title = text
                    elif self.pubdate_tag_name in tag:
                        dt = dateutil.parser.parse(text)
                    elif self.link_tag_name in tag:
                        if text:
                            url = text
                        elif 'href' in rss_data_subelem.attrib:
                            url = rss_data_subelem.attrib['href']
                        else:
                            logger.error(f'Could not find URL for "{title}" feed record')
                    elif self.description_tag_name in tag:
                        brief = text
                post_data = PostData(dt, title, self.process_url(url), brief)
                posts_data.append(post_data)
        return posts_data

    def process_url(self, url):
        return url

    @abstractmethod
    def rss_items_root(self):
        pass


class SimpleRssBasicParsingModule(RssBasicParsingModule):

    item_tag_name = 'item'
    title_tag_name = 'title'
    pubdate_tag_name = 'pubDate'
    link_tag_name = 'link'
    description_tag_name = 'description'

    def rss_items_root(self):
        return self.rss_data_root[0]


class OpenNetRuParsingModule(SimpleRssBasicParsingModule):

    source_name = "OpenNET.ru"
    rss_url = 'https://www.opennet.ru/opennews/opennews_all_utf.rss'


class LinuxComParsingModule(SimpleRssBasicParsingModule):

    source_name = "Linux.com"
    rss_url = 'https://www.linux.com/topic/feed/'


class OpenSourceComParsingModule(SimpleRssBasicParsingModule):

    source_name = 'OpenSource.com'
    rss_url = 'https://opensource.com/feed'

    @property
    def warning(self):
        return f'"{self.source_name}" provider provides RSS feed for less than week, manual checking needed'

    def _parse(self):
        result = super()._parse()
        logger.warning(self.warning)
        return result


class ItsFossComParsingModule(SimpleRssBasicParsingModule):

    source_name = 'ItsFOSS.com'
    rss_url = 'https://itsfoss.com/all-blog-posts/feed/'


class LinuxOrgRuParsingModule(SimpleRssBasicParsingModule):

    source_name = 'Linux.org.ru'
    rss_url = 'https://www.linux.org.ru/section-rss.jsp?section=1'


class HabrComBasicParsingModule(SimpleRssBasicParsingModule):

    source_name = 'Habr.com'
    hub_code = None

    @property
    def rss_url(self):
        return f'https://habr.com/ru/rss/hub/{self.hub_code}/all/?fl=ru'

    def process_url(self, url: str):
        return re.sub('/\?utm_campaign=.*&utm_source=habrahabr&utm_medium=rss',
                      '',
                      url)


class HabrComOpenSourceParsingModule(HabrComBasicParsingModule):

    source_name = f'{HabrComBasicParsingModule.source_name}: Open Source'
    hub_code = 'open_source'


class HabrComLinuxParsingModule(HabrComBasicParsingModule):

    source_name = f'{HabrComBasicParsingModule.source_name}: Linux'
    hub_code = 'linux'


class HabrComLinuxDevParsingModule(HabrComBasicParsingModule):

    source_name = f'{HabrComBasicParsingModule.source_name}: Linux Dev'
    hub_code = 'linux_dev'


class HabrComNixParsingModule(HabrComBasicParsingModule):

    source_name = f'{HabrComBasicParsingModule.source_name}: *nix'
    hub_code = 'nix'


class HabrComDevOpsParsingModule(HabrComBasicParsingModule):

    source_name = f'{HabrComBasicParsingModule.source_name}: DevOps'
    hub_code = 'devops'


class HabrComSysAdmParsingModule(HabrComBasicParsingModule):

    source_name = f'{HabrComBasicParsingModule.source_name}: SysAdm'
    hub_code = 'sys_admin'


class HabrComGitParsingModule(HabrComBasicParsingModule):

    source_name = f'{HabrComBasicParsingModule.source_name}: Git'
    hub_code = 'git'


class YouTubeComBasicParsingModule(RssBasicParsingModule):

    source_name = 'YouTube.com'
    channel_id = None
    item_tag_name = 'entry'
    title_tag_name = 'title'
    pubdate_tag_name = 'published'
    link_tag_name = 'link'
    description_tag_name = 'description'

    def rss_items_root(self):
        return self.rss_data_root

    @property
    def rss_url(self):
        return f'https://www.youtube.com/feeds/videos.xml?channel_id={self.channel_id}'


class YouTubeComAlekseySamoilovParsingModule(YouTubeComBasicParsingModule):

    source_name = f'{YouTubeComBasicParsingModule.source_name}: Aleksey Samoilov Channel'
    channel_id = 'UC3kAbMcYr-JEMSb2xX4OdpA'


class LosstRuParsingModule(SimpleRssBasicParsingModule):

    source_name = 'Losst.ru'
    rss_url = 'https://losst.ru/rss'


class PingvinusRuParsingModule(BasicParsingModule):

    source_name = 'Пингвинус'
    site_url = 'https://pingvinus.ru'

    def __init__(self):
        super().__init__()
        self.news_page_url = f'{self.site_url}/news'

    def _parse(self):
        response = requests.get(self.news_page_url)
        tree = html.fromstring(response.content)
        titles_blocks = tree.xpath('//div[@class="newsdateblock"]//h2/a[contains(@href, "/news/")]')
        dates_blocks = tree.xpath('//div[@class="newsdateblock"]//span[@class="time"]')
        if len(titles_blocks) != len(dates_blocks):
            raise Exception('News titles count does not match dates count')
        rel_urls = tree.xpath('//div[@class="newsdateblock"]//h2/a[contains(@href, "/news/")]/@href')
        titles_texts = [title_block.text for title_block in titles_blocks]
        dates_texts = [date_block.text for date_block in dates_blocks]
        urls = [f'{self.site_url}{rel_url}' for rel_url in rel_urls]
        posts = []
        for title, date_str, url in zip(titles_texts, dates_texts, urls):
            dt = datetime.datetime.strptime(date_str, '%d.%m.%Y')
            dt = dt.replace(tzinfo=dateutil.tz.gettz('Europe/Moscow'))
            post_data = PostData(dt, title, url, None)
            posts.append(post_data)
        return posts


class ParsingModuleFactory:

    @staticmethod
    def create(parsing_module_types: List[ParsingModuleType]) -> List[BasicParsingModule]:
        return [ParsingModuleFactory.create_one(parsing_module_type) for parsing_module_type in parsing_module_types]

    @staticmethod
    def create_one(parsing_module_type: ParsingModuleType) -> BasicParsingModule:
        parsing_module_constructor = globals()[parsing_module_type.value + 'ParsingModule']
        parsing_module = parsing_module_constructor()
        return parsing_module
