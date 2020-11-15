#!/usr/bin/python3

import sys
import argparse
import logging
import re
import collections
from pprint import pprint
from fntools import DIGEST_RECORD_SUBCATEGORY_RU_MAPPING

DIGEST_RECORD_SUBCATEGORY_RU_MAPPING_INVERTED = {value: key for key, value in DIGEST_RECORD_SUBCATEGORY_RU_MAPPING.items()}

def main():
    args = parse_command_line_args()
    with open(args.SOURCE, 'r') as fin:
        source_text = fin.read()
        subcategories_existing = {}
        for category in shorts_categories_h3_names_set:
            subcategories_existing[category] = []
        i = 0
        content_lines = source_text.split('\n')
        new_content = {}
        current_section = None
        current_subsection = None
        for line_i, line in enumerate(content_lines):
            line = line.strip()
            if line in shorts_categories_h3_names_set:
                i = 0
                current_section = line
                new_content[line] = {
                    'header': line,
                    'subsections': collections.OrderedDict(),
                }
            elif line in subcategories_h4_names_set:
                new_content[current_section]['subsections'][line] = {
                    'header': line,
                    'lines': [],
                }
                subcategories_existing[current_section].append(line)
                current_subsection = line
                i += 1
            else:
                if line.count('http') == 1:
                    re_match = re.search(r'(https?://\S+)( \(en\))?', line)
                    if re_match:
                        converted_line = line.replace(re_match.group(0), f'<a href="{re_match.group(1)}">[→{re_match.group(2) if re_match.group(2) else ""}]</a>')
                    else:
                        raise Exception(f'Bad string "{line}" format')
                elif line.count('http') > 1:
                    re_matches = re.findall(r'(https?://\S+)( \(en\))?', line)
                    links = []
                    for i, re_match in enumerate(re_matches):
                        url: str = re_match[0]
                        if i < len(re_matches) - 1:
                            url = url.strip(',')
                        en: str = re_match[1]
                        link = f'<a href="{url}">{i + 1}{en if en else ""}</a>'
                        links.append(link)
                    links_str = ', '.join(links)
                    converted_line = re.sub('https?://.*', f'[→ {links_str}]', line)
                else:
                    converted_line = line
                new_content[current_section]['subsections'][current_subsection]['lines'].append(converted_line)

        converted_lines = []
        for section_header in shorts_categories_h3_names_set:
            label = categories_labels[section_header]
            converted_lines.append(f'<anchor>{label}</anchor><h3>{new_content[section_header]["header"]}</h2>')
            converted_lines.append('')
            i = 0
            for header, subsection_data in new_content[section_header]['subsections'].items():
                if subsection_data['lines']:
                    converted_lines.append(f'<anchor>{label}-{i + 1}</anchor><h4>{subsection_data["header"]}</h3>')
                    converted_lines.append('')
                    if len(subsection_data['lines']) > 1:
                        converted_lines.append('<ol>')
                        for line in subsection_data['lines']:
                            converted_lines.append(f'    <li>{line}</li>')
                        converted_lines.append('</ol>')
                    else:
                        converted_lines.append(subsection_data['lines'][0])
                    converted_lines.append('')
                    i += 1
        converted_lines.append('')
        converted_text = '\n'.join(converted_lines)

        with open(args.DEST_TEXT, 'w') as fout_text:
            fout_text.write(converted_text)

        converted_toc_lines = []
        prefix = '        '
        converted_toc_lines.append(f'{prefix}<li><a href="#shorts">Короткой строкой</a>')
        converted_toc_lines.append(f'{prefix}     <ol>')
        for category in shorts_categories_h3_names_set:
            converted_toc_lines.append(f'{prefix}          <li><a href="#{categories_labels[category]}">{category}</a>')
            converted_toc_lines.append(f'{prefix}          <ol>')
            subcategory_i = 0
            for subcategory in subcategories_existing[category]:
                if new_content[category]['subsections'][subcategory]['lines']:
                    converted_toc_lines.append(f'{prefix}              <li><a href="#{categories_labels[category]}-{subcategory_i + 1}">{subcategory}</a></li>')
                    subcategory_i += 1
            converted_toc_lines.append(f'{prefix}          </ol>')
            converted_toc_lines.append(f'{prefix}          </li>')
        converted_toc_lines.append(f'{prefix}      </ol>')
        converted_toc_lines.append(f'{prefix}  </li>')

        toc_text = '\n'.join(converted_toc_lines)
        with open(args.DEST_TOC, 'w')as fout_toc:
            fout_toc.write(toc_text)


def parse_command_line_args():
    parser = argparse.ArgumentParser(
                        description='FOSS News Draft Converter')
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help='Enable debugging output')
    parser.add_argument('SOURCE',
                        help='Source file')
    parser.add_argument('DEST_TEXT',
                        help='Destination file for text')
    parser.add_argument('DEST_TOC',
                        help='Destination file for TOC')
    args = parser.parse_args()
    args.log_level = logging.DEBUG if args.debug else logging.INFO
    return args


shorts_categories_h3_names_set = (
    'Новости',
    'Статьи',
    'Релизы',
)

categories_labels = {
    'Новости': 'news',
    'Статьи': 'articles',
    'Релизы': 'releases',
}


subcategories_h4_names_set = (
    'Мероприятия',
    'Внедрения',
    'Открытие кода и данных',
    'Новости FOSS организаций',
    'DIY',
    'Юридические вопросы',
    'Ядро и дистрибутивы',
    'Системное',
    'Специальное',
    'Базы данных',
    'Мультимедиа',
    'Безопасность',
    'DevOps',
    'AI & Data Science',
    'Web',
    'Для разработчиков',
    'История',
    'Менеджмент',
    'Пользовательское',
    'Игры',
    'Железо',
    'Разное',
)


if __name__ == "__main__":
    sys.exit(main())
