from enum import Enum

class DigestRecordSubcategory(Enum):
    EVENTS = 'events'
    INTROS = 'intros'
    OPENING = 'opening'
    NEWS = 'news'
    DIY = 'diy'
    LAW = 'law'
    KnD = 'knd'
    SYSTEM = 'system'
    SPECIAL = 'special'
    EDUCATION = 'education'
    DATABASES = 'db'
    MULTIMEDIA = 'multimedia'
    MOBILE = 'mobile'
    SECURITY = 'security'
    DEVOPS = 'devops'
    DATA_SCIENCE = 'data_science'
    WEB = 'web'
    DEV = 'dev'
    HISTORY = 'history'
    MANAGEMENT = 'management'
    USER = 'user'
    GAMES = 'games'
    HARDWARE = 'hardware'
    MISC = 'misc'


DIGEST_RECORD_SUBCATEGORY_RU_MAPPING = {
    'events': 'Мероприятия',
    'intros': 'Внедрения',
    'opening': 'Открытие кода и данных',
    'news': 'Внутренние дела организаций',
    'diy': 'DIY',
    'law': 'Юридические вопросы',
    'knd': 'Ядро и дистрибутивы',
    'system': 'Системное',
    'special': 'Специальное',
    'education': 'Обучение',
    'db': 'Базы данных',
    'multimedia': 'Мультимедиа',
    'mobile': 'Мобильные',
    'security': 'Безопасность',
    'devops': 'DevOps',
    'data_science': 'AI & Data Science',
    'web': 'Web',
    'dev': 'Для разработчиков',
    'history': 'История',
    'management': 'Менеджмент',
    'user': 'Пользовательское',
    'games': 'Игры',
    'hardware': 'Железо',
    'misc': 'Разное',
}


DIGEST_RECORD_SUBCATEGORY_VALUES = [category.value for category in DigestRecordSubcategory]
