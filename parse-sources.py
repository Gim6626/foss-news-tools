#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import sys
from abc import ABCMeta, abstractmethod
from typing import List, Dict
from enum import Enum
import datetime
import argparse
import argcomplete
import requests
import xml.etree.ElementTree as ET
import dateutil.parser
from lxml import html
from pprint import pprint
import logging
import re


days_count = None

LOGGING_SETTINGS = {
    'level': logging.INFO,
    'format': '[%(asctime)s] %(levelname)s: %(message)s',
    'stream': sys.stderr,
}

logging.basicConfig(**LOGGING_SETTINGS)

logger = logging.getLogger('foss-news-sources-parser')
logging.getLogger("requests").setLevel(logging.WARNING)


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


def init_command_line_args():
    parser = argparse.ArgumentParser(description='Parse sources for FOSS News')
    parser.add_argument('MODULE',
                        nargs='+',
                        choices=PARSING_MODULES_TYPES + ('ALL',),
                        help='Parsing modules')
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help='Enable debugging output')
    parser.add_argument('-o',
                        '--output-path',
                        default='output.html',
                        help='Output HTML path')
    parser.add_argument('-D',
                        '--days',
                        default=7,
                        help='Days count for which gather news')
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if args.MODULE == ['ALL']:
        args.modules = [ParsingModuleType(m) for m in PARSING_MODULES_TYPES]
    else:
        args.modules = [ParsingModuleType(m) for m in args.MODULE]
    args.log_level = logging.DEBUG if args.debug else logging.INFO
    return args


def posts_data_from_multiple_sources_to_html(posts_data_from_multiple_sources: List[PostsData]):
    html = '''
<html>
    <head>
        <title>FOSS News Parsed Sources Data</title>
    </head>
    <body>
    '''
    for posts_data_from_one_source in posts_data_from_multiple_sources:
        warning = posts_data_from_one_source.warning
        source_name = posts_data_from_one_source.source_name
        posts_data: List[PostData] = posts_data_from_one_source.posts_data_list
        html += f'''
        <h1>{source_name}</h1>
        '''
        if warning is not None:
            html += f'''
            <p style="color: red"><i><b>WARNING</b>: {warning}</i></p>
            '''
        if posts_data:
            html += '''
            <ol>
            '''
            for post_data in posts_data:
                html += f'''
                <li style="margin-bottom: 10px">{post_data.dt} {post_data.title} <a href="{post_data.url}">{post_data.url}</a></li>
                '''
            html += '''
            </ol>
            '''
    html += '''
    </body>
</html>
    '''
    return html


def main():
    command_line_args = init_command_line_args()
    logger.setLevel(command_line_args.log_level)
    global days_count
    days_count = int(command_line_args.days)
    parsing_modules = ParsingModuleFactory.create(command_line_args.modules)
    posts_data_from_multiple_sources: List[PostsData] = []
    for parsing_module in parsing_modules:
        posts_data = parsing_module.parse()
        posts_data_one = PostsData(parsing_module.source_name,
                                   posts_data,
                                   parsing_module.warning)
        posts_data_from_multiple_sources.append(posts_data_one)
    html = posts_data_from_multiple_sources_to_html(posts_data_from_multiple_sources)
    with open(command_line_args.output_path, 'w') as fout:
        fout.write(html)
    logger.info(f'Output saved to "{command_line_args.output_path}"')


if __name__ == "__main__":
    sys.exit(main())
