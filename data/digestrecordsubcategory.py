from enum import Enum

class DigestRecordSubcategory(Enum):
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
    MISC = 'misc'

    @staticmethod
    def from_name(name: str):
        return DigestRecordSubcategory(name.lower() if name.lower() != 'databases' else 'db')


DIGEST_RECORD_SUBCATEGORY_RU_MAPPING = {
    'events': 'Мероприятия',
    'intros': 'Внедрения',
    'opening': 'Открытие кода и данных',
    'org': 'Дела организаций',
    'diy': 'DIY',
    'law': 'Юридические вопросы',
    'knd': 'Ядро и дистрибутивы',
    'special': 'Специальное',
    'education': 'Обучение',
    'db': 'Базы данных',
    'multimedia': 'Мультимедиа',
    'mobile': 'Мобильные',
    'security': 'Безопасность',
    'sysadm': 'Системное администрирование',
    'devops': 'DevOps',
    'data_science': 'AI & Data Science',
    'web': 'Web',
    'dev': 'Для разработчиков',
    'testing': 'Тестирование',
    'history': 'История',
    'management': 'Менеджмент',
    'user': 'Пользовательское',
    'games': 'Игры',
    'hardware': 'Железо',
    'misc': 'Разное',
}


DIGEST_RECORD_SUBCATEGORY_VALUES = [category.value for category in DigestRecordSubcategory]
