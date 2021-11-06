#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import sys
import argparse
import logging

from fntools import (
    logger,
    HabrPostsStatisticsGetter,
    VkPostsStatisticsGetter,
)


def main():
    args = parse_command_line_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    config_path = args.FNGS_CONFIG
    vk_posts_statistics_getter = VkPostsStatisticsGetter(args.SESSIONS_COUNT)
    vk_posts_statistics = vk_posts_statistics_getter.gather_posts_statistics()
    stats_str = f'{vk_posts_statistics[0]}\t'
    habr_posts_statistics_getter = HabrPostsStatisticsGetter(config_path, args.SESSIONS_COUNT)
    habr_posts_statistics = habr_posts_statistics_getter.gather_posts_statistics()
    for number in range(max(habr_posts_statistics.keys()) + 1):
        if number in habr_posts_statistics:
            stats_str += f'{habr_posts_statistics[number]}\t'
    fout_name = 'stats.csv'
    fout = open(fout_name, 'w')
    fout.write(stats_str)
    logger.info(f'Statistics string saved to "{fout_name}"')


def parse_command_line_args():
    parser = argparse.ArgumentParser(description='FOSS News Gathering Client')
    parser.add_argument('SESSIONS_COUNT',
                        type=int,
                        help='Browser sessions count')
    parser.add_argument('FNGS_CONFIG',
                        help='Config with data for access to remote FOSS News Gathering Server server')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    sys.exit(main())
