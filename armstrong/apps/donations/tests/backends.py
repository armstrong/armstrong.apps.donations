import billing
import fudge
from fudge.inspector import arg

from ._utils import TestCase

from .. import backends
from .. import forms


class AuthorizeNetBackendTestCase(TestCase):
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
                })

        get_gateway = fudge.Fake()
        get_gateway.is_callable().returns(fake)

        with fudge.patched_context(backends, "get_gateway", get_gateway):
            backend = backends.AuthorizeNetBackend()
            backend.purchase(donation, donation_form)
        fudge.verify()
