from authorize import aim
import billing
from django.conf import settings
import fudge
from fudge.inspector import arg
import random

from ._utils import TestCase

from .. import backends
from .. import forms


class AuthorizeNetBackendTestCase(TestCase):
    @property
    def random_donation_and_form(self):
        donation = self.random_donation
        data = self.get_base_random_data(name=donation.donor.name,
                amount=donation.amount)
        donation_form = forms.CreditCardDonationForm(data)
        return donation, donation_form

    def test_settings_defaults_to_django_settings(self):
        backend = backends.AuthorizeNetBackend()
        self.assertEqual(backend.settings, settings)

    def test_settings_can_be_injected(self):
        r = random.randint(10000, 20000)
        backend = backends.AuthorizeNetBackend(settings=r)
        self.assertEqual(backend.settings, r)

    def test_api_class_defaults_to_authorize_api(self):
        backend = backends.AuthorizeNetBackend()
        self.assertEqual(backend.api_class, aim.Api)

    def test_api_class_can_be_injected(self):
        r = random.randint(10000, 20000)
        backend = backends.AuthorizeNetBackend(api_class=r)
        self.assertEqual(backend.api_class, r)

    def test_api_instantiates_api_class_with_configured_settings(self):
        random_login = "some random login %d" % random.randint(100, 200)
        random_key = "some random key %d" % random.randint(100, 200)
        random_return = "some random return %d" % random.randint(100, 200)
        settings = fudge.Fake()
        settings.has_attr(AUTHORIZE={
            "LOGIN": random_login,
            "KEY": random_key,
        })
        api_class = fudge.Fake()

        # Note that delimiter is included here because authorize's code
        # can't even keep track of what deliminter it wants to use!
        (api_class.expects_call()
                .with_args(random_login, random_key, delimiter=u"|")
                .returns(random_return))
        fudge.clear_calls()

        backend = backends.AuthorizeNetBackend(api_class=api_class,
                settings=settings)
        result = backend.get_api()
        self.assertEqual(result, random_return)
        fudge.verify()

    def test_get_form_returns_credit_card_form(self):
        backend = backends.get_backend()
        self.assertEqual(backend.get_form_class(),
                forms.CreditCardDonationForm)

    def test_dispatches_to_gateway_purchase(self):
        def is_credit_card(s):
            return isinstance(s, billing.CreditCard)

        donation = self.random_donation
        donor = donation.donor
        data = self.get_base_random_data(name=donor.name,
                amount=donation.amount)
        donation_form = forms.CreditCardDonationForm(data)
        # card = donation_form.get_credit_card(donation.donor)

        fake = fudge.Fake()
        fake.expects("purchase").with_args(donation.amount,
                arg.passes_test(is_credit_card),
                options={
                    "billing_address": {
                        "name": donor.name,
                        "address1": donor.address.address,
                        "city": donor.address.city,
                        "state": donor.address.state,
                        "country": "US",
                        "zip": donor.address.zipcode,
                    },
                    "shipping_address": {
                        "name": donor.name,
                        "address1": donor.mailing_address.address,
                        "city": donor.mailing_address.city,
                        "state": donor.mailing_address.state,
                        "country": "US",
                        "zip": donor.mailing_address.zipcode,
                    }
                }).returns(self.get_fake_purchase_response())

        get_gateway = fudge.Fake()
        get_gateway.is_callable().returns(fake)

        with fudge.patched_context(backends, "get_gateway", get_gateway):
            backend = backends.AuthorizeNetBackend()
            backend.purchase(donation, donation_form)
        fudge.verify()

    def test_mark_donation_as_processed(self):
        donation, donation_form = self.random_donation_and_form
        self.assertFalse(donation.processed, msg="sanity check")
        gateway_stub = self.get_gateway_stub()
        with fudge.patched_context(backends, "get_gateway", gateway_stub):
            backend = backends.AuthorizeNetBackend()
            backend.purchase(donation, donation_form)

        self.assertTrue(donation.processed)

    def test_donation_processed_is_false_if_not_successfully_charged(self):
        donation, donation_form = self.random_donation_and_form
        gateway_stub = self.get_gateway_stub(successful=False)
        with fudge.patched_context(backends, "get_gateway", gateway_stub):
            backend = backends.AuthorizeNetBackend()
            backend.purchase(donation, donation_form)

        self.assertFalse(donation.processed)

    def test_purchase_returns_true_status_if_successful(self):
        donation, donation_form = self.random_donation_and_form
        gateway_stub = self.get_gateway_stub()
        with fudge.patched_context(backends, "get_gateway", gateway_stub):
            backend = backends.AuthorizeNetBackend()
            response = backend.purchase(donation, donation_form)
        self.assertTrue(response["status"])

    def test_purchase_returns_false_status_if_successful(self):
        donation, donation_form = self.random_donation_and_form
        gateway_stub = self.get_gateway_stub(successful=False)
        with fudge.patched_context(backends, "get_gateway", gateway_stub):
            backend = backends.AuthorizeNetBackend()
            response = backend.purchase(donation, donation_form)
        self.assertFalse(response["status"])

    def test_returned_dict_contains_response_reason_text_as_reason(self):
        random_text = "Some Random Text (%d)" % random.randint(1000, 2000)
        donation, donation_form = self.random_donation_and_form
        gateway_stub = self.get_gateway_stub(response_reason_text=random_text)
        with fudge.patched_context(backends, "get_gateway", gateway_stub):
            backend = backends.AuthorizeNetBackend()
            response = backend.purchase(donation, donation_form)
        self.assertTrue("reason" in response, msg="sanity check")
        self.assertEqual(response["reason"], random_text)

    def test_returned_dict_contains_raw_response_model(self):
        donation, donation_form = self.random_donation_and_form
        gateway_stub = self.get_gateway_stub()
        with fudge.patched_context(backends, "get_gateway", gateway_stub):
            backend_response = backends.get_gateway().purchase()["response"]
            backend = backends.AuthorizeNetBackend()
            response = backend.purchase(donation, donation_form)
        self.assertTrue("response" in response, msg="sanity check")
        self.assertEqual(response["response"], backend_response)
