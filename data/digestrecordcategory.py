from enum import Enum


class DigestRecordCategory(Enum):
    UNKNOWN = 'unknown'
    NEWS = 'news'
    ARTICLES = 'articles'
    VIDEOS = 'videos'
    RELEASES = 'releases'
    OTHER = 'other'

    @staticmethod
    def from_name(name: str):
        return DigestRecordCategory(name.lower())


DIGEST_RECORD_CATEGORY_RU_MAPPING = {
    'unknown': 'Неизвестно',
    'news': 'Новости',
    'articles': 'Статьи',
    'videos': 'Видео',
    'releases': 'Релизы',
    'other': 'Прочее',
}


DIGEST_RECORD_CATEGORY_EN_MAPPING = {
    'unknown': 'Unknown',
    'news': 'News',
    'articles': 'Articles',
    'videos': 'Videos',
    'releases': 'Releases',
    'other': 'Other',
}


DIGEST_RECORD_CATEGORY_VALUES = [category.value for category in DigestRecordCategory]
