import billing
import fudge
from fudge.inspector import arg

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
                }).returns({"status": "SUCCESS"})

        get_gateway = fudge.Fake()
        get_gateway.is_callable().returns(fake)

        with fudge.patched_context(backends, "get_gateway", get_gateway):
            backend = backends.AuthorizeNetBackend()
            backend.purchase(donation, donation_form)
        fudge.verify()

    def get_payment_stub(self, successful=True):
        fake = fudge.Fake()
        fake.expects("purchase") \
            .with_args(arg.any(), arg.any(), options=arg.any()) \
            .returns({"status": "SUCCESS" if successful else "FAILURE"})
        return fake

    def get_gateway_stub(self, payment_stub=None, successful=True):
        if not payment_stub:
            payment_stub = self.get_payment_stub(successful=successful)
        fake = fudge.Fake()
        fake.is_callable().returns(payment_stub)
        return fake

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
