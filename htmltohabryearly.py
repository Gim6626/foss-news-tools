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
import lxml.html.clean as lxml_cleaner

from pprint import pprint

from fntools import (
    logger,
)


def main():
    # TODO: Exclude common code from here and from weekly digests converter
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
                                                     ('a', 'span', 'img', 'ul', 'ol'))
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
    annotation_passed = False
    toc_added = False
    h2_i = 1
    for tag in tags:
        if not annotation_passed and 'Аннотация' in tag.html_src:
            annotation_passed = True
        if not annotation_passed:
            continue
        if tag.ttype == TagType.H1:
            continue
        if tag.ttype == TagType.H2:
            if tag.cleared_html_src == 'Заключение':
                label = 'outro'
            elif tag.cleared_html_src == 'Аннотация':
                label = 'intro'
            else:
                label = f'section-{h2_i}'
                h2_i += 1
            if 'Аннотация' not in tag.html_src and not toc_added:
                toc_tag = Tag(TagType.H2,
                              '<h2>Оглавление</h2>',
                              'toc')
                tags_fixed.append(toc_tag)
                toc_added = True
            toc_item = TocItem(tag.ttype, tag.cleared_html_src, [], label)
            toc.items.append(toc_item)
            tag_with_label = Tag(tag.ttype,
                                 f'<anchor>{label}</anchor>{tag.html_src}',
                                 label)
            tags_fixed.append(tag_with_label)
        else:
            # TODO: Process categories and subcategories
            # TODO: Process lists
            # TODO: Process dash before link in main news
            if '[←] Предыдущий выпуск' in tag.html_src:
                re_match = re.search(r'(\[←\])\s+(Предыдущий выпуск)\s+.\s+(https?://[^<]+)', tag.html_src)
                if re_match:
                    processed_html_src = tag.html_src.replace(re_match.group(0), f'<a href="{re_match.group(3)}">{re_match.group(1)}</a> {re_match.group(2)}')
                else:
                    raise Exception(f'Bad string "{tag.html_src}" format')
            elif 'Подписывайтесь на наш' in tag.html_src:
                processed_html_src = '<p>Подписывайтесь на <a href="https://t.me/permlug_channel">наш Telegram канал</a>, <a href="https://vk.com/permlug">группу ВКонтакте</a> или <a href="http://permlug.org/rss">RSS</a> чтобы не пропустить новые выпуски FOSS News.</p>'
            elif len(re.findall('https?://', tag.html_src)) == 1:
                re_match = re.search(r'(https?://[^<\s]+)(\s+\(en\))?', tag.html_src)
                if re_match:
                    to_replace = re_match.group(0)
                    link = re_match.group(1)
                    en = re_match.group(2)
                    processed_html_src = tag.html_src.replace(to_replace,
                                                              f'<a href="{link}">[→{en if en is not None else ""}]</a>')
                else:
                    raise Exception(f'Bad string "{tag}" format')
            elif len(re.findall('https?://', tag.html_src)) > 1:
                re_matches = re.findall(r'(https?://[^<\s]+)(\s+\(en\))?', tag.html_src)
                links = []
                for i, re_match in enumerate(re_matches):
                    url: str = re_match[0]
                    if i < len(re_matches) - 1:
                        url = url.strip(',')
                    en: str = re_match[1]
                    link = f'<a href="{url}">{i + 1}{en if en else ""}</a>'
                    links.append(link)
                links_str = ', '.join(links)
                processed_html_src = re.sub(r'https?://[^<$]+',
                                            f'[→ {links_str}]',
                                            tag.html_src)
            else:
                processed_html_src = tag.html_src
            tag.html_src = processed_html_src
            tags_fixed.append(tag)

    with open(args.DESTINATION, 'w') as fout:
        in_list = False
        for tag in tags_fixed:
            if tag.ttype == TagType.LI and not in_list:
                print('<ol>', file=fout)
                in_list = True
            if tag.ttype != TagType.LI and in_list:
                print('</ol>', file=fout)
                in_list = False
            print(tag.html_src, file=fout)
            if tag.label == 'toc':
                toc.print_html(file=fout)


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
                   offset='',
                   file=None):
        html = f'{offset}<li><a href="#{self.label}">{self.title}</a>'
        if self.subitems:
            print(html, file=file)
            print(f'{offset}<ol>', file=file)
        else:
            html += '</li>'
            print(html, file=file)
        for subitem in self.subitems:
            subitem.print_html(offset + '    ', file=file)
        if self.subitems:
            print(f'{offset}</ol></li>', file=file)

    def __str__(self):
        return f'<{self.tag_type.value}> {self.title} #{self.label}'


class TOC:

    def __init__(self):
        self.items = []

    def print_plain(self):
        for toc_item in self.items:
            toc_item.print_plain()

    def print_html(self, file=None):
        print('<ol>', file=file)
        for toc_item in self.items:
            toc_item.print_html('    ', file=file)
        print('</ol>', file=file)


class TagType(Enum):

    H1 = 'h1'
    H2 = 'h2'
    H3 = 'h3'
    H4 = 'h4'
    P = 'p'
    # UL = 'ul'
    # OL = 'ol'
    LI = 'li'

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
