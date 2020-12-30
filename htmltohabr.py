#!/usr/bin/env python3

import sys
import argparse
import logging
import re
import html
from enum import Enum
from typing import List
from bs4 import BeautifulSoup
import lxml.html.clean as lxml_cleaner

from pprint import pprint

from fntools import (
    logger,
)


def main():
    args = parse_command_line_args()
    logger.setLevel(args.log_level)
    with open(args.SOURCE, 'r') as fin:
        src_content = fin.read()
        src_content_unescaped = html.unescape(src_content)
        cleaner = lxml_cleaner.Cleaner(safe_attrs=frozenset())
        src_content_unescaped_cleaned = cleaner.clean_html(src_content_unescaped)
        src_content_unescaped_cleaned_2 = clear_tags(src_content_unescaped_cleaned,
                                                     ['a', 'span', 'img'])
    tags_names_for_parsing = (tag_type.value for tag_type in TagType)
    regexps = (tag_regexp_from_tag_name(tag_name) for tag_name in tags_names_for_parsing)
    regexp = '|'.join(regexps)
    logger.debug(f'Searching for regexp "{regexp}" in source file content')
    # TODO: Maybe we could remove BS from here and requirements, seems that it is not needed
    # bs_obj = BeautifulSoup(src_content_unescaped_cleaned_2)
    # pretty_src_content_unescaped_cleaned_2_prettified = bs_obj.prettify()
    # pretty_src_content_unescaped_cleaned_2_prettified_2 = clear_tags(pretty_src_content_unescaped_cleaned_2_prettified,
    #                                                                  ['p'])
    # print(pretty_src_content_unescaped_cleaned_2_prettified_2)
    # return
    src_tags_contents_all = re.findall(regexp,
                                       src_content_unescaped_cleaned_2,
                                       re.MULTILINE | re.DOTALL)
    tags: List[Tag] = []
    for src_tag_content in src_tags_contents_all:
        tag_type: TagType = TagType.from_html(src_tag_content)
        tag: Tag = Tag(tag_type, src_tag_content)
        print(tag_type, '->', src_tag_content)
    src_tags_filtered = []


def parse_command_line_args():
    parser = argparse.ArgumentParser(
                        description='FOSS News HTML to Habr format converter')
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help='Enable debugging output')
    parser.add_argument('SOURCE',
                        help='Source file')
    parser.add_argument('DESTINATION',
                        help='Destination file')
    args = parser.parse_args()
    args.log_level = logging.DEBUG if args.debug else logging.INFO
    return args


def tag_regexp_from_tag_name(tag_name: str):
    return f'<{tag_name}[^>]*>.*?</{tag_name}>'


def clear_tags(src_html: str,
               bad_tag_names: List[str]):
    cleared_html = src_html
    for bad_tag_name in bad_tag_names:
        cleared_html = re.sub(f'</?{bad_tag_name}/?>', '', cleared_html)
    return cleared_html


class TagType(Enum):

    H1 = 'h1'
    H2 = 'h2'
    H3 = 'h3'
    H4 = 'h4'
    P = 'p'
    UL = 'ul'
    OL = 'ol'

    @staticmethod
    def from_html(src_tag_content: str):
        tag_type: TagType
        for tag_type in TagType:
            regexp = tag_regexp_from_tag_name(tag_type.value)
            if re.fullmatch(regexp, src_tag_content):
                return tag_type


class Tag:

    def __init__(self,
                 tag_type: TagType,
                 tag_html_src: str):
        self.ttype = tag_type
        self.html_src = tag_html_src


if __name__ == "__main__":
    sys.exit(main())
