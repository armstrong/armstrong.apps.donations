from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.client import Client
import os

from ._utils import TestCase

from .. import forms


class DonationFormPage(TestCase):
    def setUp(self):
        self.client = Client()
        settings.TEMPLATE_DIRS = (
            os.path.join(os.path.dirname(__file__), "_templates"),
        )

    def get_donation_form_response(self):
        url = reverse("donations_form")
        response = self.client.get(url)
        self.assertEqual(200, response.status_code, msg="sanity check")
        return response

    def assert_in_context(self, response, name):
        self.assertTrue(name in response.context,
                msg="%s was not in the context")

    def assert_type_in_context(self, response, name, expected_type):
        self.assert_in_context(response, name)
        self.assertEqual(response.context[name].__class__, expected_type,
                msg="%s in the context, but does not have a class of %s" % (
                        name, expected_type.__name__))

    def assert_value_in_context(self, response, name, expected_value):
        self.assert_in_context(response, name)
        self.assertEqual(response.context[name], expected_value,
                msg="%s in the context, but not equal to '%s'" % (
                        name, expected_value))

    def test_adds_form_action_url_to_context(self):
        response = self.get_donation_form_response()
        self.assert_value_in_context(response, "form_action_url", "")
