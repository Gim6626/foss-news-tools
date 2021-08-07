#!/usr/bin/env python3

import sys
import argparse
import logging
import re
import html
import os
import subprocess
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


class HtmlMode(Enum):
    HABR = 'habr'
    PERMLUG = 'permlug'


def main():
    # TODO: Refactor
    # TODO: Remove hardcode
    args = parse_command_line_args()
    logger.setLevel(args.log_level)
    if re.search(r'\.html$', args.SOURCE):
        html_path = args.SOURCE
        logger.debug('HTML file passed, will work with it')
    elif re.search(r'\.zip$', args.SOURCE):
        logger.debug('ZIP archive passed, extracting HTML from it')
        html_path = html_from_zip(os.path.abspath(args.SOURCE))
        logger.debug(f'Extracted HTML "{html_path}", will work with it')
    else:
        raise Exception('Unsupported SOURCE file type, only HTML and ZIP are supported')
    logger.debug('Reading HTML')
    with open(html_path, 'r') as fin:
        src_content = fin.read()
    logger.debug('Processing HTML')
    src_content_unescaped = html.unescape(src_content)
    cleaner = lxml_cleaner.Cleaner(safe_attrs=frozenset())
    src_content_unescaped_cleaned = cleaner.clean_html(src_content_unescaped)
    src_content_unescaped_cleaned_2 = clear_tags(src_content_unescaped_cleaned,
                                                 ('a', 'span', 'img', '<ul>', '<ol>'))
    tags_names_for_parsing = (tag_type.value for tag_type in TagType)
    regexps = (tag_regexp_from_tag_name(tag_name) for tag_name in tags_names_for_parsing)
    regexp = '|'.join(regexps)
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
            if args.MODE == HtmlMode.HABR.value:
                header_html = f'<anchor>{label}</anchor>{tag.html_src}'
            elif args.MODE == HtmlMode.PERMLUG.value:
                header_html = f'<a id="{label}"></a>{tag.html_src}'
            else:
                raise NotImplementedError
            tag_with_label = Tag(tag.ttype,
                                 header_html,
                                 label)
            tags_fixed.append(tag_with_label)
        elif tag.ttype == TagType.H3:
            if current_toc_h2_item.title == 'Главное':
                label = f'main-{len(current_toc_h2_item.subitems) + 1}'
            elif current_toc_h2_item.title == 'Короткой строкой':
                if tag.cleared_html_src == 'Новости':
                    label = 'news'
                elif tag.cleared_html_src == 'Видео':
                    label = 'videos'
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
            if args.MODE == HtmlMode.HABR.value:
                header_html = f'<anchor>{label}</anchor>{tag.html_src}'
            elif args.MODE == HtmlMode.PERMLUG.value:
                header_html = f'<a id="{label}"></a>{tag.html_src}'
            else:
                raise NotImplementedError
            tag_with_label = Tag(tag.ttype,
                                 header_html,
                                 label)
            tags_fixed.append(tag_with_label)
        elif tag.ttype == TagType.H4:
            if current_toc_h3_item.title == 'Новости':
                label = f'news-{len(current_toc_h3_item.subitems) + 1}'
            elif current_toc_h3_item.title == 'Видео':
                label = f'videos-{len(current_toc_h3_item.subitems) + 1}'
            elif current_toc_h3_item.title == 'Статьи':
                label = f'articles-{len(current_toc_h3_item.subitems) + 1}'
            elif current_toc_h3_item.title == 'Релизы':
                label = f'releases-{len(current_toc_h3_item.subitems) + 1}'
            else:
                raise NotImplementedError
            toc_item = TocItem(tag.ttype, tag.cleared_html_src, [], label)
            current_toc_h3_item.subitems.append(toc_item)
            if args.MODE == HtmlMode.HABR.value:
                header_html = f'<anchor>{label}</anchor>{tag.html_src}'
            elif args.MODE == HtmlMode.PERMLUG.value:
                header_html = f'<a id="{label}"></a>{tag.html_src}'
            else:
                raise NotImplementedError
            tag_with_label = Tag(tag.ttype,
                                 header_html,
                                 label)
            tags_fixed.append(tag_with_label)
        else:
            if '[←] Предыдущий выпуск' in tag.html_src:
                re_match = re.search(r'(\[←\])\s+(Предыдущий выпуск)\s+.\s+(https?://[^<]+)', tag.html_src)
                if re_match:
                    processed_html_src = tag.html_src.replace(re_match.group(0), f'<a href="{re_match.group(3)}">{re_match.group(1)}</a> {re_match.group(2)}')
                else:
                    raise Exception(f'Bad string "{tag.html_src}" format')
            elif 'Подписывайтесь на наш' in tag.html_src:
                # TODO: Remove hardcode, process text from source document
                processed_html_src = '<p>Подписывайтесь на наш Telegram канал <a href="https://t.me/permlug">наш Telegram канал</a> или <a href="http://permlug.org/rss">RSS</a> чтобы не пропустить новые выпуски FOSS News. Также мы есть во всех основных соцсетях:</p>'
            elif 'Категория:' in tag.html_src:
                re_match = re.search(r'Категория:\s+([^<$]+)', tag.html_src)
                if re_match:
                    if args.MODE == HtmlMode.HABR.value:
                        processed_html_src = f'<i><b>Категория:</b> {re_match.group(1)}</i>'
                    elif args.MODE == HtmlMode.PERMLUG.value:
                        processed_html_src = f'<em><strong>Категория:</strong> {re_match.group(1)}</em>'
                    else:
                        raise NotImplementedError
                else:
                    raise NotImplementedError
            elif len(re.findall('https?://', tag.html_src)) == 1:
                re_match = re.search(r'(https?://[^<\s]+)(\s+\(en\))?', tag.html_src)
                if re_match:
                    to_replace = re_match.group(0)
                    if to_replace[-2:] == '/,':
                        # OpenNET handling at the conclusion section
                        to_replace = to_replace[:-1]
                    link = re_match.group(1)
                    if link[-2:] == '/,':
                        # OpenNET handling at the conclusion section
                        link = link[:-1]
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

    logger.debug(f'Saving convertation results to "{args.DESTINATION}"')
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
    parser.add_argument('MODE',
                        help='HTML mode',
                        choices=[mode.value for mode in HtmlMode])
    parser.add_argument('SOURCE',
                        help='Source file')
    parser.add_argument('DESTINATION',
                        help='Destination file')
    args = parser.parse_args()
    args.log_level = logging.DEBUG if args.debug else logging.INFO
    return args


def html_from_zip(zip_absolute_path: str):
    base_tmp_path = '/tmp/fossnews'
    if not os.path.exists(base_tmp_path):
        os.mkdir(base_tmp_path)
    elif not os.path.isdir(base_tmp_path):
        raise NotImplementedError
    specific_tmp_path = os.path.join(base_tmp_path, os.path.basename(zip_absolute_path).replace('.zip', ''))
    cmd = f'unzip -o "{zip_absolute_path}" -d "{specific_tmp_path}"'
    logger.debug(f'Executing "{cmd}"')
    proc = subprocess.run(cmd,
                          shell=True,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise Exception(f'Failed to unzip: {proc.stderr}')
    logger.debug(f'Extracted HTML to "{specific_tmp_path}"')
    for file_name in os.listdir(specific_tmp_path):
        if re.search(r'\.html$', file_name):
            return f'{specific_tmp_path}/{file_name}'
    raise Exception('HTML not found in archive')


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
