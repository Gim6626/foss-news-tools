from enum import Enum


class DigestRecordCategory(Enum):
    UNKNOWN = 'unknown'
    NEWS = 'news'
    ARTICLES = 'articles'
    VIDEOS = 'videos'
    RELEASES = 'releases'
    OTHER = 'other'


DIGEST_RECORD_CATEGORY_RU_MAPPING = {
    'unknown': 'Неизвестно',
    'news': 'Новости',
    'articles': 'Статьи',
    'videos': 'Видео',
    'releases': 'Релизы',
    'other': 'Прочее',
}


DIGEST_RECORD_CATEGORY_VALUES = [category.value for category in DigestRecordCategory]
