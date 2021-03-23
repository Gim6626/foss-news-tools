#!/usr/bin/env python3

from data.digestrecordsubcategorykeywords import DIGEST_RECORD_SUBCATEGORY_KEYWORDS_MAPPING
from data.generalkeywords import GENERAL_KEYWORDS
from data.lfkeywords import LF_KEYWORDS
import yaml

keywords = {
    'generic': [],
    'specific': [],
}
keywords['specific'] += GENERAL_KEYWORDS
keywords['specific'] += LF_KEYWORDS
for subcategory, subcategory_keywords in DIGEST_RECORD_SUBCATEGORY_KEYWORDS_MAPPING.items():
    for keywords_type in ('generic', 'specific'):
        keywords[keywords_type] += subcategory_keywords[keywords_type]

for keywords_type in ('generic', 'specific'):
    keywords[keywords_type] = sorted(list(set(keywords[keywords_type])))

print(yaml.dump(keywords))
