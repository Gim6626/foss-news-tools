import requests
import re
from pprint import pprint
import logging
import sys
import time
from abc import ABCMeta, abstractmethod

LOGGING_SETTINGS = {
    'level': logging.INFO,
    'format': '[%(asctime)s] %(levelname)s: %(message)s',
    'stream': sys.stderr,
}

logging.basicConfig(**LOGGING_SETTINGS)

logger = logging.getLogger('foss-news-sources-parser')
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
        self._posts_count = 40

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


def main():
    habr_posts_statistics_getter = HabrPostsStatisticsGetter()
    habr_posts_statistics = habr_posts_statistics_getter.posts_statistics()
    vk_posts_statistics_getter = VkPostsStatisticsGetter()
    vk_posts_statistics = vk_posts_statistics_getter.posts_statistics()
    google_docs_str = ''
    for number in range(max(max(habr_posts_statistics.keys()), max(vk_posts_statistics.keys())) + 1):
        if number in habr_posts_statistics:
            google_docs_str += f'{habr_posts_statistics[number]}\t'
        if number in vk_posts_statistics:
            google_docs_str += f'{vk_posts_statistics[number]}\t'
    fout_name = 'google-docs-stats.csv'
    fout = open(fout_name, 'w')
    fout.write(google_docs_str)
    logger.info(f'Google Docs statistics string saved to "{fout_name}"')


if __name__ == "__main__":
    sys.exit(main())
