from armstrong.dev.tasks import *
import os


os.environ["FULL_TEST_SUITE"] = "1"
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
        'billing',
    ),
    'SITE_ID': 1,
    'ROOT_URLCONF': 'armstrong.apps.donations.urls',
    'TEMPLATE_DIRS': [
        os.path.join(os.path.dirname(__file__),
                     "armstrong", "apps", "donations", "tests", "_templates"),
    ],
    'MERCHANT_TEST_MODE': True,

    # For testing against Authorize
    'AUTHORIZE_LOGIN_ID': u'4u42L5wJu',
    'AUTHORIZE_TRANSACTION_KEY': u'5V6E7x6bFx4z7Z5e',
}

main_app = "donations"
full_name = "armstrong.apps.donations"
tested_apps = (main_app,)
