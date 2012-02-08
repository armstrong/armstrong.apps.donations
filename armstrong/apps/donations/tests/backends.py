from authorize import aim
import billing
from django.conf import settings
import fudge
from fudge.inspector import arg
import os
import random
import unittest

from ._utils import TestCase

from .. import backends
from .. import forms


class AuthorizeNetBackendTestCase(TestCase):
    def get_api_stub(self, response=None, reason_text=None, successful=True):
        if response is None:
            response = {
                "reason_code": u"1" if successful else u"2",
                "reason_text": "Some Random Reason %d" % (
                        random.randint(100, 200)),
            }
        if reason_text:
            response["reason_text"] = reason_text
        api = fudge.Fake()
        api.provides("transaction").returns(response)
        get_api = fudge.Fake().is_callable().returns(api)
        return get_api

    @property
    def test_settings(self):
        fake = fudge.Fake()
        fake.has_attr(AUTHORIZE={
            # Login/password 2k4NuTk6cS
            "LOGIN": u"5A77vX8HxE",
            "KEY": u"6T29u7p67xKeEW33",
        })
        return fake

    @property
    def random_donation_and_form(self):
        donation = self.random_donation
        data = self.get_base_random_data(name=donation.donor.name,
                amount=donation.amount)
        donation_form = forms.CreditCardDonationForm(data)
        donation_form.is_valid()
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

    def test_dispatches_to_authorize_to_create_transaction(self):
        donation, donation_form = self.random_donation_and_form

        api = fudge.Fake("api")
        api.expects("transaction").with_args(
                amount=donation.amount,
                card_num=donation_form.cleaned_data["card_number"],
                card_code=donation_form.cleaned_data["ccv_code"],
                exp_date=u"%02d-%04d" % (
                        int(donation_form.cleaned_data["expiration_month"]),
                        int(donation_form.cleaned_data["expiration_year"])),
                description=u"Donation: $%d" % donation.amount,
                first_name=unicode(donation.donor.name.split(" ")[0]),
                last_name=unicode(donation.donor.name.split(" ", 1)[-1]),
                address=donation.donor.address.address,
                city=donation.donor.address.city,
                state=donation.donor.address.state,
                zip=donation.donor.address.zipcode,
        ).returns({"reason_code": u"1", "reason_text": u"Some random Reason"})
        get_api = fudge.Fake().expects_call().returns(api)

        backend = backends.AuthorizeNetBackend()
        with fudge.patched_context(backend, "get_api", get_api):
            backend.purchase(donation, donation_form)
        fudge.verify()

    @unittest.skipIf(os.environ.get("FULL_TEST_SUITE", False) != "1",
            "Only run when FULL_TEST_SUITE env is set")
    def test_can_communicate_with_real_authorize_backend(self):
        class TestableApi(aim.Api):
            def __init__(self, *args, **kwargs):
                kwargs["is_test"] = True
                super(TestableApi, self).__init__(*args, **kwargs)

            def transaction(self, **kwargs):
                kwargs["test_request"] = u"TRUE"
                return super(TestableApi, self).transaction(**kwargs)

        donation, donation_form = self.random_donation_and_form
        donation_form.data["card_number"] = u"4222222222222"  # Set to test CC
        donation.amount = 1
        backend = backends.AuthorizeNetBackend(api_class=TestableApi,
                settings=self.test_settings)
        result = backend.purchase(donation, donation_form)
        self.assertTrue(result["status"])

    def test_mark_donation_as_processed(self):
        donation, donation_form = self.random_donation_and_form
        self.assertFalse(donation.processed, msg="sanity check")
        backend = backends.AuthorizeNetBackend()
        with fudge.patched_context(backend, "get_api", self.get_api_stub()):
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
        get_api = self.get_api_stub()
        backend = backends.AuthorizeNetBackend()
        with fudge.patched_context(backend, "get_api", get_api):
            response = backend.purchase(donation, donation_form)
        self.assertTrue(response["status"])

    def test_purchase_returns_false_status_if_successful(self):
        donation, donation_form = self.random_donation_and_form
        get_api = self.get_api_stub(successful=False)
        backend = backends.AuthorizeNetBackend()
        with fudge.patched_context(backend, "get_api", get_api):
            response = backend.purchase(donation, donation_form)
        self.assertFalse(response["status"])

    def test_returned_dict_contains_response_reason_text_as_reason(self):
        random_text = "Some Random Text (%d)" % random.randint(1000, 2000)
        donation, donation_form = self.random_donation_and_form
        get_api = self.get_api_stub(reason_text=random_text)
        backend = backends.AuthorizeNetBackend()
        with fudge.patched_context(backend, "get_api", get_api):
            result = backend.purchase(donation, donation_form)
        self.assertTrue("reason" in result, msg="sanity check")
        self.assertEqual(result["reason"], random_text)

    def test_returned_dict_contains_raw_response_dict(self):
        random_response = {
            "reason_code": u"%d" % random.randint(100, 200),
            "reason_text": "Some Random Reason %d" % random.randint(100, 200),
        }
        get_api = self.get_api_stub(response=random_response)
        donation, donation_form = self.random_donation_and_form
        backend = backends.AuthorizeNetBackend()
        with fudge.patched_context(backend, "get_api", get_api):
            result = backend.purchase(donation, donation_form)
        self.assertTrue("response" in result, msg="sanity check")
        self.assertEqual(result["response"], random_response)
