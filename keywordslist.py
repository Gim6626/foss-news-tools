#!/usr/bin/env python3

from data.generalkeywords import GENERAL_KEYWORDS
from data.lfkeywords import LF_KEYWORDS
import yaml
import os

keywords = {
    'generic': [],
    'specific': [],
}
keywords['specific'] += GENERAL_KEYWORDS
keywords['specific'] += LF_KEYWORDS

subcategories_keywords_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                           'data',
                                           'digestrecordsubcategorykeywords.yaml')
with open(subcategories_keywords_path, 'r') as fin:
    subcategories_keywords = yaml.safe_load(fin)

for subcategory, subcategory_keywords in subcategories_keywords.items():
    for keywords_type in ('generic', 'specific'):
        keywords[keywords_type] += subcategory_keywords[keywords_type]

for keywords_type in ('generic', 'specific'):
    keywords[keywords_type] = sorted(list(set(keywords[keywords_type])))

print(yaml.dump(keywords, allow_unicode=True))
