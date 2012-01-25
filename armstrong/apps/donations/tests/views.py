from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.client import Client
import os
from unittest import expectedFailure

from ._utils import TestCase

from .. import forms
from .. import models
from .. import views


class BaseDonationFormViewTestCase(TestCase):
    view_class = views.DonationFormView
    view_name = "donations_form"

    @property
    def url(self):
        # TODO: move this into armstrong.dev
        return reverse(self.view_name)

    def setUp(self):
        super(BaseDonationFormViewTestCase, self).setUp()
        # TODO: move this to armstrong.dev
        self.client = Client()

        # TODO: make this based off of class name and move into armstrong.dev
        settings.TEMPLATE_DIRS = (
            os.path.join(os.path.dirname(__file__), "_templates"),
        )
        self.client

    def assert_in_context(self, response, name):
        # TODO: move this into armstrong.dev
        self.assertTrue(name in response.context,
                msg="%s was not in the context" % name)

    def assert_type_in_context(self, response, name, expected_type):
        self.assert_in_context(response, name)
        self.assertTrue(isinstance(response.context[name], expected_type),
                msg="%s in the context, but does not have a class of %s" % (
                        name, expected_type.__name__))

    def assert_value_in_context(self, response, name, expected_value):
        self.assert_in_context(response, name)
        self.assertEqual(response.context[name], expected_value,
                msg="%s in the context, but not equal to '%s'" % (
                        name, expected_value))

    def assert_template(self, template, response):
        template_names = [a.name for a in response.templates]
        self.assertTrue(template in template_names,
                msg="%s not found in templates: %s" % (
                        template, response.templates))

    def assert_form_has_errors(self, response, form_name, error_fields=None):
        self.assert_in_context(response, form_name)
        form = response.context[form_name]
        self.assertNotEqual(form.errors, [],
                msg="%s.errors was empty?" % form_name)
        if error_fields:
            for field in error_fields:
                self.assertTrue(field in form.errors,
                        msg="%s not in the errors" % field)

    def get_view_object(self):
        view = self.view_class()
        view.request = self.factory.get(self.url)
        return view

    def get_response(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code, msg="sanity check")
        return response


# TODO: move to armstrong.dev
def get_response(func):
    from functools import wraps
    @wraps(func)
    def inner(self):
        func(self, self.get_response())
    return inner


class DonationFormViewGetTestCase(BaseDonationFormViewTestCase):
    @get_response
    def test_adds_form_action_url_to_context(self, response):
        self.assert_value_in_context(response, "form_action_url", "")

    @get_response
    def test_adds_donor_form_to_context(self, response):
        self.assert_type_in_context(response, "donor_form", forms.DonorForm)

    @get_response
    def test_adds_address_formset_to_context(self, response):
        self.assert_type_in_context(response, "address_formset",
                forms.DonorAddressFormset)

    @get_response
    def test_adds_donation_formset_to_context(self, response):
        self.assert_type_in_context(response, "donation_form",
                forms.BaseDonationForm)

    def test_get_donation_form_returns_credit_card_form_by_default(self):
        # TODO: make sure in "default" state
        view = self.get_view_object()
        donation_form = view.get_donation_form()
        self.assertIsA(donation_form, forms.CreditCardDonationForm)


class DonationFormViewPostTestCase(BaseDonationFormViewTestCase):
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

    def test_saves_donation_on_post_with_minimal_information(self):
        donor_name = self.random_donor_name
        random_amount = self.random_amount
        data = {
            "name": donor_name,
            "amount": random_amount,
        }
        data.update(self.get_data_as_formset())

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
        address = models.DonorAddress.objects.get(**address_kwargs)
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

        self.assertEqual(0, len(models.DonorAddress.objects.all()),
            msg="sanity check")
        self.client.post(self.url, data)
        self.assertEqual(2, len(models.DonorAddress.objects.all()))
        address = models.DonorAddress.objects.get(**address_kwargs)
        mailing_address = models.DonorAddress.objects.get(
                **mailing_address_kwargs)
        self.assertNotEqual(address, mailing_address)

        donor = models.Donor.objects.get(name=donor_name)
        self.assertEqual(address, donor.address)
        self.assertEqual(mailing_address, donor.mailing_address)

    @expectedFailure
    def test_only_saves_donor_once(self):
        """This will pass if #17594 is merged in"""
        data = self.random_post_data
        with self.assertNumQueries(2):
            self.client.post(self.url, data)

    def test_only_saves_donor_once_with_buggy_modelformset(self):
        data = self.random_post_data
        with self.assertNumQueries(3, msg="will fail if #17594 is merged"):
            self.client.post(self.url, data)

    def test_saves_mailing_address_if_same_as_billing_is_checked(self):
        data = self.random_post_data
        data["mailing_same_as_billing"] = u"1"
        self.client.post(self.url, data)
        donor = models.Donor.objects.get(name=data["name"])
        self.assertEqual(donor.address, donor.mailing_address)

    def test_redirects_to_success_url_after_successful_save(self):
        data = self.random_post_data
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("donations_thanks"))

    @expectedFailure
    def test_saves_donation_information(self):
        self.fail()

    def test_displays_errors_on_donor_validation_error(self):
        data = self.random_post_data
        del data["name"]
        response = self.client.post(self.url, data)
        self.assert_template("armstrong/donations/donation.html", response)
        self.assert_form_has_errors(response, "donor_form", ["name", ])

    @expectedFailure
    def test_displays_errors_on_address_validation_error(self):
        self.fail()

    @expectedFailure
    def test_redirects_to_success_url_on_success(self):
        self.fail()

    @expectedFailure
    def test_displays_errors_when_payment_method_authorization_fails(self):
        self.fail()
