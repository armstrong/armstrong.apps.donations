from authorize import aim, arb
import datetime
from django.conf import settings
import fudge
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

    def get_onetime_purchase_stub(self, successful=True):
        onetime_purchase = fudge.Fake().is_callable().returns({
                "status": successful,
        })
        return onetime_purchase

    @property
    def test_settings(self):
        fake = fudge.Fake()
        fake.has_attr(AUTHORIZE={
            # Login/password 2k4NuTk6cS
            "LOGIN": u"5A77vX8HxE",
            "KEY": u"6T29u7p67xKeEW33",
        })
        return fake

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

    def test_recurring_api_class_defaults_to_authorize_api(self):
        backend = backends.AuthorizeNetBackend()
        self.assertEqual(backend.recurring_api_class, arb.Api)

    def test_recurring_api_class_can_be_injected(self):
        r = random.randint(10000, 20000)
        backend = backends.AuthorizeNetBackend(recurring_api_class=r)
        self.assertEqual(backend.recurring_api_class, r)

    def test_get_recurring_api_instantiates_with_configured_settings(self):
        random_login = "some random login %d" % random.randint(100, 200)
        random_key = "some random key %d" % random.randint(100, 200)
        random_return = "some random return %d" % random.randint(100, 200)
        settings = fudge.Fake().has_attr(
            AUTHORIZE={
                "LOGIN": random_login,
                "KEY": random_key,
        })

        recurring_api_class = (fudge.Fake().expects_call()
                .with_args(random_login, random_key)
                .returns(random_return))
        fudge.clear_calls()

        backend = backends.AuthorizeNetBackend(settings=settings,
                    recurring_api_class=recurring_api_class)
        result = backend.get_recurring_api()
        self.assertEqual(result, random_return)
        fudge.verify()

    def test_get_form_returns_credit_card_form(self):
        backend = backends.get_backend()
        self.assertEqual(backend.get_form_class(),
                forms.AuthorizeDonationForm)

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
        try:
            self.assertTrue(result["status"], msg="This ")
        except AssertionError:
            # This is a known issue where Authorize.net randomly returns
            # a bad response in test mode.  Yup, you read that correctly.
            # A system designed to process your money can't actually figure
            # out how to run a test server in a reliable wayself.
            self.assertEqual(result["reason"],
                    u"(TESTMODE) The credit card number is invalid.",
                    msg="Authorize.net really has failed us")

    @unittest.skipIf(os.environ.get("FULL_TEST_SUITE", False) != "1",
            "Only run when FULL_TEST_SUITE env is set")
    def test_can_communicate_with_real_authorize_backend_for_recurring(self):
        onetime_purchase = fudge.Fake().is_callable().returns({"status": True})

        class TestableApi(arb.Api):
            def __init__(self, *args, **kwargs):
                kwargs["is_test"] = True
                super(TestableApi, self).__init__(*args, **kwargs)

            def create_subscription(self, **kwargs):
                kwargs["test_request"] = u"TRUE"
                return super(TestableApi, self).create_subscription(**kwargs)

        donation, donation_form = self.random_donation_and_form
        donation_form.data["card_number"] = u"4222222222222"  # Set to test CC
        donation.donation_type = self.random_monthly_type
        donation.amount = 1
        backend = backends.AuthorizeNetBackend(recurring_api_class=TestableApi,
                settings=self.test_settings)
        with fudge.patched_context(backend, "onetime_purchase",
                onetime_purchase):
            result = backend.purchase(donation, donation_form)
        try:
            self.assertTrue(result["status"])
        except AssertionError:
            # This is a known issue where Authorize.net randomly returns
            # a bad response in test mode.  Yup, you read that correctly.
            # A system designed to process your money can't actually figure
            # out how to run a test server in a reliable wayself.
            self.assertEqual(result["reason"],
                    u"(TESTMODE) The credit card number is invalid.",
                    msg="Authorize.net really has failed us")

    def test_mark_donation_as_processed(self):
        donation, donation_form = self.random_donation_and_form
        self.assertFalse(donation.processed, msg="sanity check")
        backend = backends.AuthorizeNetBackend()
        with fudge.patched_context(backend, "get_api", self.get_api_stub()):
            backend.purchase(donation, donation_form)

        self.assertTrue(donation.processed)

    def test_donation_processed_is_false_if_not_successfully_charged(self):
        stub = self.get_onetime_purchase_stub(successful=False)
        donation, donation_form = self.random_donation_and_form
        backend = backends.AuthorizeNetBackend()
        with stub_onetime_purchase(backend, stub):
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

    def test_calls_to_recurring_donation_if_donation_is_recurring(self):
        donation, donation_form = self.random_donation_and_form
        donation.donation_type = self.random_monthly_type
        today = datetime.date.today()
        start_date = u"%s" % ((today + datetime.timedelta(days=30))
                .strftime("%Y-%m-%d"))

        recurring_api = fudge.Fake()
        expiration_date = u"%(expiration_year)s-%(expiration_month)s" % (
                donation_form.cleaned_data)
        recurring_api.expects("create_subscription").with_args(
                amount=donation.amount,
                interval_unit=arb.MONTHS_INTERVAL,
                interval_length=u"1",
                card_number=donation_form.cleaned_data["card_number"],
                card_code=donation_form.cleaned_data["ccv_code"],
                expiration_date=expiration_date,
                bill_first_name=u"%s" % donation.donor.name.split(" ")[0],
                bill_last_name=u"%s" % donation.donor.name.split(" ", 1)[-1],
                total_occurrences=donation.donation_type.repeat,
                start_date=start_date,
        ).returns({"messages": {"result_code": {"text_": u"Ok"}}})

        fake = fudge.Fake().expects_call().returns(recurring_api)
        backend = backends.AuthorizeNetBackend()
        with fudge.patched_context(backend, "get_api", self.get_api_stub()):
            with fudge.patched_context(backend, "get_recurring_api", fake):
                backend.purchase(donation, donation_form)
        fudge.verify()

    def test_calls_transaction_prior_to_subscription(self):
        donation, donation_form = self.random_donation_and_form
        donation.donation_type = self.random_monthly_type

        recurring_purchase = (fudge.Fake().expects_call()
                    .with_args(donation, donation_form))
        onetime_purchase = (fudge.Fake().expects_call()
                    .with_args(donation, donation_form)
                    .returns({"status": True}))

        backend = backends.AuthorizeNetBackend()
        with stub_recurring_purchase(backend, recurring_purchase):
            with stub_onetime_purchase(backend, onetime_purchase):
                backend.purchase(donation, donation_form)
        fudge.verify()

    def test_does_not_call_recurring_purchase_on_failed_onetime_purchase(self):
        donation, donation_form = self.random_donation_and_form
        donation.donation_type = self.random_monthly_type

        recurring_purchase = fudge.Fake()
        onetime_purchase = (fudge.Fake().expects_call()
                    .with_args(donation, donation_form)
                    .returns({"status": False}))

        backend = backends.AuthorizeNetBackend()
        with stub_recurring_purchase(backend, recurring_purchase):
            with stub_onetime_purchase(backend, onetime_purchase):
                backend.purchase(donation, donation_form)
        fudge.verify()

    def test_adds_recurring_response_to_return_on_failure(self):
        random_return = random.randint(1000, 2000)
        donation, donation_form = self.random_donation_and_form
        donation.donation_type = self.random_monthly_type

        recurring_purchase = (fudge.Fake().is_callable()
                .returns(random_return))
        onetime_purchase = (fudge.Fake().is_callable()
                .returns({"status": True}))

        backend = backends.AuthorizeNetBackend()
        with stub_recurring_purchase(backend, recurring_purchase):
            with stub_onetime_purchase(backend, onetime_purchase):
                result = backend.purchase(donation, donation_form)
        self.assertTrue("recurring_response" in result)
        self.assertEqual(result["recurring_response"], random_return)


from contextlib import contextmanager


@contextmanager
def stub_recurring_purchase(backend, recurring_purchase):
    with fudge.patched_context(backend, "recurring_purchase",
            recurring_purchase):
        yield


@contextmanager
def stub_onetime_purchase(backend, onetime_purchase):
    with fudge.patched_context(backend, "onetime_purchase",
            onetime_purchase):
        yield
