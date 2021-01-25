#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import sys
from fntools import (
    logger,
    HabrPostsStatisticsGetter,
    VkPostsStatisticsGetter,
)


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
