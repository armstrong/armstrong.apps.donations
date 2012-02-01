from armstrong.utils.backends import GenericBackend
from billing import get_gateway

from . import forms


class AuthorizeNetBackend(object):
    def get_form_class(self):
        return forms.CreditCardDonationForm

    def purchase(self, donation, form):
        authorize = get_gateway("authorize_net")
        authorize.purchase(donation.amount,
                form.get_credit_card(donation.donor),
                options=self.get_options(donation))

    def get_options(self, donation):
        donor = donation.donor
        return {
            "billing_address": {
                "name": donor.name,
                "address1": donor.address.address,
                "city": donor.address.city,
                "state": donor.address.state,
                # TODO: Support other countries
                "country": "US",
                "zip": donor.address.zipcode,
            },
            "shipping_address": {
                "name": donor.name,
                "address1": donor.mailing_address.address,
                "city": donor.mailing_address.city,
                "state": donor.mailing_address.state,
                # TODO: Support other countries
                "country": "US",
                "zip": donor.mailing_address.zipcode,
            }
        }

raw_backend = GenericBackend("ARMSTRONG_DONATIONS_BACKEND", defaults=[
    "armstrong.apps.donations.backends.AuthorizeNetBackend",
])

get_backend = raw_backend.get_backend
