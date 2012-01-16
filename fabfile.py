from armstrong.dev.tasks import *


settings = {
    'DEBUG': True,
    'INSTALLED_APPS': (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'armstrong.apps.donations',
        'south',
    ),
    'SITE_ID': 1,
}

main_app = "donations"
full_name = "armstrong.apps.donations"
tested_apps = (main_app,)
