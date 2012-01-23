from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.client import Client
import os

from ._utils import TestCase

from .. import models


class DonationFormViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        settings.TEMPLATE_DIRS = (
            os.path.join(os.path.dirname(__file__), "_templates"),
        )

    @property
    def url(self):
        return reverse("donations_form")

    def get_donation_form_response(self):
        response = self.client.get(self.url)
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

    def _test_saves_donation_on_post_with_minimal_information(self):
        donor_name = self.random_donor_name
        random_amount = self.random_amount
        data = {
            "name": donor_name,
            "amount": random_amount,
        }

        # sanity check
        self.assertRaises(models.Donor.DoesNotExist,
                models.Donor.objects.get, name=donor_name)
        self.client.post(self.url, data)
        donor = models.Donor.objects.get(name=donor_name)
        self.assertEqual(donor.name, donor_name)

    def test_saves_address_if_present(self):
        donor_name = self.random_donor_name
        address_kwargs = self.random_address_kwargs
        address_formset = self.get_data_as_formset(address_kwargs)
        data = {
            "name": donor_name,
        }
        data.update(address_formset)

        self.client.post(self.url, data)
        address = models.DonorMailingAddress.objects.get(**address_kwargs)
        donor = models.Donor.objects.get(name=donor_name)
        self.assertEqual(address, donor.address)
        self.assertEqual(None, donor.mailing_address)

    def test_saves_mailing_address_if_present(self):
        donor_name = self.random_donor_name
        address_kwargs = self.random_address_kwargs
        mailing_address_kwargs = self.random_address_kwargs
        address_formset = self.get_data_as_formset([
            address_kwargs,
            mailing_address_kwargs,
        ])
        data = {
            "name": donor_name,
        }
        data.update(address_formset)

        self.assertEqual(0, len(models.DonorMailingAddress.objects.all()),
            msg="sanity check")
        self.client.post(self.url, data)
        self.assertEqual(2, len(models.DonorMailingAddress.objects.all()))
        address = models.DonorMailingAddress.objects.get(**address_kwargs)
        mailing_address = models.DonorMailingAddress.objects.get(
                **mailing_address_kwargs)
        self.assertNotEqual(address, mailing_address)

        donor = models.Donor.objects.get(name=donor_name)
        self.assertEqual(address, donor.address)
        self.assertEqual(mailing_address, donor.mailing_address)

    @property
    def random_post_data(self):
        donor_name = self.random_donor_name
        address_kwargs = self.random_address_kwargs
        address_formset = self.get_data_as_formset(address_kwargs)
        data = {
            "name": donor_name,
        }
        data.update(address_formset)
        return data

    def test_saves_mailing_address_if_same_as_billing_is_checked(self):
        data = self.random_post_data
        data["mailing_same_as_billing"] = u"1"
        self.client.post(self.url, data)
        donor = models.Donor.objects.get(name=data["name"])
        self.assertEqual(donor.address, donor.mailing_address)
