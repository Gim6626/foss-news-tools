#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import sys
from typing import List
import argparse
import argcomplete
import logging
import fntools
from fntools import (
    logger,
    PARSING_MODULES_TYPES,
    ParsingModuleType,
    PostData,
    PostsData,
    ParsingModuleFactory,
)


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
    fntools.days_count = int(command_line_args.days)
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
