from enum import Enum


class DigestRecordContentCategory(Enum):
    EVENTS = 'events'
    INTROS = 'intros'
    OPENING = 'opening'
    ORG = 'org'
    DIY = 'diy'
    LAW = 'law'
    KnD = 'knd'
    SPECIAL = 'special'
    EDUCATION = 'education'
    DATABASES = 'db'
    MULTIMEDIA = 'multimedia'
    MOBILE = 'mobile'
    SECURITY = 'security'
    SYSTEM = 'system'
    SYSADM = 'sysadm'
    DEVOPS = 'devops'
    DATA_SCIENCE = 'data_science'
    WEB = 'web'
    DEV = 'dev'
    TESTING = 'testing'
    HISTORY = 'history'
    MANAGEMENT = 'management'
    USER = 'user'
    GAMES = 'games'
    HARDWARE = 'hardware'
    MESSENGERS = 'messengers'
    MISC = 'misc'

    @staticmethod
    def from_name(name: str):
        return DigestRecordContentCategory(name.lower() if name.lower() != 'databases' else 'db')


DIGEST_RECORD_CONTENT_CATEGORY_RU_MAPPING = {
    'events': 'Мероприятия',
    'intros': 'Внедрения',
    'opening': 'Открытие кода и данных',
    'org': 'Дела организаций',
    'diy': 'DIY',
    'law': 'Юридические вопросы',
    'knd': 'Ядро Linux, дистрибутивы на его основе и прочие ОС',
    'special': 'Специальное',
    'education': 'Обучение',
    'db': 'Базы данных',
    'multimedia': 'Мультимедиа',
    'mobile': 'Мобильные',
    'security': 'Безопасность',
    'system': 'Системное',
    'sysadm': 'Системное администрирование',
    'devops': 'DevOps',
    'data_science': 'AI, ML и Data Science',
    'web': 'Web и подобное',
    'dev': 'Разработка',
    'testing': 'Тестирование',
    'history': 'История',
    'management': 'Менеджмент',
    'user': 'Пользовательское',
    'games': 'Игры',
    'hardware': 'Железо',
    'messengers': 'Мессенджеры',
    'misc': 'Разное',
}


DIGEST_RECORD_CONTENT_CATEGORY_EN_MAPPING = {
    'events': 'Events',
    'intros': 'Introductions',
    'opening': 'Code and data opening',
    'org': 'Organizations related',
    'diy': 'DIY',
    'law': 'Law',
    'knd': 'Linux Kernel, Distributions Based on It and other OS',
    'special': 'Special',
    'education': 'Education',
    'db': 'Databases',
    'multimedia': 'Multimedia',
    'mobile': 'Mobile',
    'security': 'Security',
    'system': 'System',
    'sysadm': 'System Administration',
    'devops': 'DevOps',
    'data_science': 'AI & Data Science',
    'web': 'Web and Related',
    'dev': 'Development',
    'testing': 'Testing',
    'history': 'History',
    'management': 'Management',
    'user': 'Basic User Things',
    'games': 'Games',
    'hardware': 'Hardware',
    'messengers': 'Messengers',
    'misc': 'Miscellaneous',
}


DIGEST_RECORD_CONTENT_CATEGORY_VALUES = [category.value for category in DigestRecordContentCategory]
