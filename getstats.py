#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import sys
from fntools import (
    logger,
    HabrPostsStatisticsGetter,
    VkPostsStatisticsGetter,
)


def main():
    vk_posts_statistics_getter = VkPostsStatisticsGetter()
    vk_posts_statistics = vk_posts_statistics_getter.posts_statistics()
    stats_str = f'{vk_posts_statistics[0]}\t'
    habr_posts_statistics_getter = HabrPostsStatisticsGetter()
    habr_posts_statistics = habr_posts_statistics_getter.posts_statistics()
    for number in range(max(habr_posts_statistics.keys()) + 1):
        if number in habr_posts_statistics:
            stats_str += f'{habr_posts_statistics[number]}\t'
    fout_name = 'stats.csv'
    fout = open(fout_name, 'w')
    fout.write(stats_str)
    logger.info(f'Statistics string saved to "{fout_name}"')


if __name__ == "__main__":
    sys.exit(main())
