from armstrong.dev.tasks import *
import os


settings = {
    'DEBUG': True,
    'TEMPLATE_DEBUG': True,
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
    'ROOT_URLCONF': 'armstrong.apps.donations.urls',
    'TEMPLATE_DIRS': [
        os.path.join(os.path.dirname(__file__),
                     "armstrong", "apps", "donations", "tests", "_templates"),
    ]
}

main_app = "donations"
full_name = "armstrong.apps.donations"
tested_apps = (main_app,)
