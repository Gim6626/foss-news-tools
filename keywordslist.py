#!/usr/bin/env python3

from data.digestrecordsubcategorykeywords import DIGEST_RECORD_SUBCATEGORY_KEYWORDS_MAPPING
from data.generalkeywords import GENERAL_KEYWORDS
from data.lfkeywords import LF_KEYWORDS

keywords = []
keywords += GENERAL_KEYWORDS
keywords += LF_KEYWORDS
for subcategory, subcategory_keywords in DIGEST_RECORD_SUBCATEGORY_KEYWORDS_MAPPING.items():
    keywords += subcategory_keywords

keywords.sort()

for keyword in keywords:
    print(keyword)
