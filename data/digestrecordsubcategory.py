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
    MANAGEMENT = 'management'
    USER = 'user'
    GAMES = 'games'
    HARDWARE = 'hardware'
    MISC = 'misc'


DIGEST_RECORD_SUBCATEGORY_KEYWORDS_MAPPING = {
    'events': (),
    'intros': (),
    'opening': (),
    'news': (
        'GitHub',
    ),
    'diy': (),
    'law': (),
    'knd': (
        'дистрибутив',
        '4MLinux',
        'Armbian',
        'GhostBSD',
        'MidnightBSD',
        'KDE Neon',
        'Kubuntu',
        'Ubuntu',
        'Chrome OS',
        'Tails',
        'Solaris',
        'Kali Linux',
        'Альт',
        'ELKS',
        'Void Linux',
    ),
    'system': (
        'Grub',
        'systemd',
        'Xorg',
        'Mir',
        'Wayland',
        'PowerShell',
        'Guix',
        'bash',
        'i3wm',
        'ZFS',
        'Btrfs',
        'sysvinit',
        'Coreboot',
    ),
    'special': (
        'XCP-NG',
        'Proxmox',
        'Coq',
        'KStars',
        'Wine',
    ),
    'education': (
        'GCompris',
        'course',
    ),
    'db': (
        'libmdbx',
        'postgresql',
        'mysql',
    ),
    'multimedia': (
        'MPV',
        'Ardour',
        'PulseAudio',
        'Paint',
        'LazPaint',
        'GIMP',
        'Blender',
    ),
    'mobile': (
        'Android',
        'Ubuntu Touch',
        'KDE Plasma Mobile',
        'PinePhone',
    ),
    'security': (
        'LibreSSL',
    ),
    'devops': (
        'Docker',
        'Kubernetes',
        'Terraform',
        'Kafka',
    ),
    'data_science': (),
    'web': (
        'nginx',
        'Firefox',
        'Chrome'
        'SeaMonkey',
        'GNUnet',
        'Tor Browser',
        'Thunderbird',
        'Chromium',
        'Pale Moon',
    ),
    'dev': (
        'Git',
        'Kivy',
        'BPF',
        'cSvn',
        'Rust',
        'Scala',
        'Node.js',
        'Javascript',
        'Electron',
        'make',
        'PHP',
        'Perl',
    ),
    'history': (),
    'management': (),
    'user': (
        'LibreOffice',
        'Cinnamon',
        'Regolith',
        'motd',
    ),
    'games': (
        'Verloren',
    ),
    'hardware': (
        'Raspberry Pi',
    ),
    'misc': (),
}


DIGEST_RECORD_SUBCATEGORY_RU_MAPPING = {
    'events': 'Мероприятия',
    'intros': 'Внедрения',
    'opening': 'Открытие кода и данных',
    'news': 'Новости FOSS организаций',
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
