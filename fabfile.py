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
    'ROOT_URLCONF': 'armstrong.apps.donations.tests._urls',
    'TEMPLATE_DIRS': [
        os.path.join(os.path.dirname(__file__),
                     "armstrong", "apps", "donations", "tests", "_templates"),
    ],
    'MERCHANT_TEST_MODE': True,

    # For testing against Authorize
    "AUTHORIZE": {
        # Login/password 2k4NuTk6cS
        "LOGIN": u"5A77vX8HxE",
        "KEY": u"6T29u7p67xKeEW33",
    }
}

main_app = "donations"
full_name = "armstrong.apps.donations"
tested_apps = (main_app,)
