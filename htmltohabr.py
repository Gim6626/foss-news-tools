#!/usr/bin/env python3

import sys
import argparse
import logging
import re
import html
from enum import Enum
from typing import (
    List,
    Tuple,
)
from bs4 import BeautifulSoup
import lxml.html.clean as lxml_cleaner

from pprint import pprint

from fntools import (
    logger,
)


def main():
    # TODO: Refactor
    # TODO: Remove hardcode
    args = parse_command_line_args()
    logger.setLevel(args.log_level)
    with open(args.SOURCE, 'r') as fin:
        src_content = fin.read()
        src_content_unescaped = html.unescape(src_content)
        cleaner = lxml_cleaner.Cleaner(safe_attrs=frozenset())
        src_content_unescaped_cleaned = cleaner.clean_html(src_content_unescaped)
        src_content_unescaped_cleaned_2 = clear_tags(src_content_unescaped_cleaned,
                                                     ('a', 'span', 'img'))
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
        if clear_tags(src_tag_content, ('p',)) == '':
            continue
        tag: Tag = Tag(tag_type, src_tag_content)
        tags.append(tag)
        # print(tag_type, '->', src_tag_content)

    tags_fixed: List[Tag] = []
    toc = TOC()
    current_toc_h2_item: TocItem = None
    current_toc_h3_item: TocItem = None
    annotation_passed = False
    for tag in tags:
        if not annotation_passed and 'Аннотация' in tag.html_src:
            annotation_passed = True
        if not annotation_passed:
            continue
        if tag.ttype == TagType.H1:
            continue
        if tag.ttype == TagType.H2:
            if tag.cleared_html_src == 'Главное':
                label = 'main'
                toc_tag = Tag(TagType.H2,
                              '<h2>Оглавление</h2>',
                              'toc')
                tags_fixed.append(toc_tag)
            elif tag.cleared_html_src == 'Короткой строкой':
                label = 'shorts'
            elif tag.cleared_html_src == 'Что ещё посмотреть':
                label = 'more'
            elif tag.cleared_html_src == 'Заключение':
                label = 'end'
            else:
                raise NotImplementedError
            toc_item = TocItem(tag.ttype, tag.cleared_html_src, [], label)
            toc.items.append(toc_item)
            current_toc_h2_item = toc_item
            current_toc_h3_item = None
            tag_with_label = Tag(tag.ttype,
                                 f'<anchor>{label}</anchor>{tag.html_src}',
                                 label)
            tags_fixed.append(tag_with_label)
        elif tag.ttype == TagType.H3:
            if current_toc_h2_item.title == 'Главное':
                label = f'main-{len(current_toc_h2_item.subitems) + 1}'
            elif current_toc_h2_item.title == 'Короткой строкой':
                if tag.cleared_html_src == 'Новости':
                    label = 'news'
                elif tag.cleared_html_src == 'Статьи':
                    label = 'articles'
                elif tag.cleared_html_src == 'Релизы':
                    label = 'releases'
                else:
                    raise NotImplementedError
            else:
                raise NotImplementedError
            toc_item = TocItem(tag.ttype, tag.cleared_html_src, [], label)
            current_toc_h2_item.subitems.append(toc_item)
            current_toc_h3_item = toc_item
            tag_with_label = Tag(tag.ttype,
                                 f'<anchor>{label}</anchor>{tag.html_src}',
                                 label)
            tags_fixed.append(tag_with_label)
        elif tag.ttype == TagType.H4:
            if current_toc_h3_item.title == 'Новости':
                label = f'news-{len(current_toc_h3_item.subitems) + 1}'
            elif current_toc_h3_item.title == 'Статьи':
                label = f'articles-{len(current_toc_h3_item.subitems) + 1}'
            elif current_toc_h3_item.title == 'Релизы':
                label = f'releases-{len(current_toc_h3_item.subitems) + 1}'
            else:
                raise NotImplementedError
            toc_item = TocItem(tag.ttype, tag.cleared_html_src, [], label)
            current_toc_h3_item.subitems.append(toc_item)
            tag_with_label = Tag(tag.ttype,
                                 f'<anchor>{label}</anchor>{tag.html_src}',
                                 label)
            tags_fixed.append(tag_with_label)
        else:
            tags_fixed.append(tag)

    for tag in tags_fixed:
        print(tag.html_src)
        if tag.label == 'toc':
            toc.print_html()


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
               bad_tag_names: Tuple):
    cleared_html = src_html
    for bad_tag_name in bad_tag_names:
        cleared_html = re.sub(f'</?{bad_tag_name}/?>', '', cleared_html)
    return cleared_html


class TocItem:

    def __init__(self,
                 tag_type: 'TagType',
                 title: str,
                 subitems: List['TocItem'],
                 label: str):
        self.tag_type = tag_type
        self.title = title
        self.subitems = subitems
        self.label = label

    def print_plain(self,
                    offset=''):
        print(f'{offset}{str(self)}')
        for subitem in self.subitems:
            subitem.print_plain(offset + '    ')

    def print_html(self,
                   offset=''):
        html = f'{offset}<li><a href="#{self.label}">{self.title}</a>'
        if self.subitems:
            print(html)
            print(f'{offset}<ol>')
        else:
            html += '</li>'
            print(html)
        for subitem in self.subitems:
            subitem.print_html(offset + '    ')
        if self.subitems:
            print(f'{offset}</ol></li>')

    def __str__(self):
        return f'<{self.tag_type.value}> {self.title} #{self.label}'


class TOC:

    def __init__(self):
        self.items = []

    def print_plain(self):
        for toc_item in self.items:
            toc_item.print_plain()

    def print_html(self):
        print('<ol>')
        for toc_item in self.items:
            toc_item.print_html('    ')
        print('</ol>')


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

    def is_header(self):
        if self in (self.H1, self.H2, self.H3, self.H4):
            return True
        else:
            return False


class Tag:

    def __init__(self,
                 tag_type: TagType,
                 tag_html_src: str,
                 label: str = None):
        self.ttype = tag_type
        self.label = label
        self.html_src = tag_html_src

    @property
    def cleared_html_src(self):
        return re.sub(r'</?.*?/?>', '', self.html_src)


if __name__ == "__main__":
    sys.exit(main())
