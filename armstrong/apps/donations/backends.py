from armstrong.utils.backends import GenericBackend
from authorize import aim
from billing import get_gateway
from django.conf import settings as django_settings

from . import forms


class AuthorizeNetBackend(object):
    def __init__(self, api_class=None, settings=None):
        if api_class is None:
            api_class = aim.Api
        self.api_class = api_class
        if settings is None:
            settings = django_settings
        self.settings = settings

    def get_api(self):
        return self.api_class(self.settings.AUTHORIZE["LOGIN"],
                self.settings.AUTHORIZE["KEY"], delimiter=u"|")

    def get_form_class(self):
        return forms.CreditCardDonationForm

    def new_purchase(self, donation, form):
        api = self.get_api()
        data = form.get_data_for_charge(donation.donor)
        donor = donation.donor
        data.update({
            "amount": donation.amount,
            "description": u"Donation: $%d" % donation.amount,
            "first_name": unicode(donor.name.split(" ")[0]),
            "last_name": unicode(donor.name.split(" ", 1)[-1]),

            # TODO: extract and be conditional
            "address": donor.address.address,
            "city": donor.address.city,
            "state": donor.address.state,
            "zip": donor.address.zipcode,
        })
        response = api.transaction(**data)
        return {
            "status": response["reason_code"] == u"1",
            "response": response,
        }

    def purchase(self, donation, form):
        authorize = get_gateway("authorize_net")
        result = authorize.purchase(donation.amount,
                form.get_credit_card(donation.donor),
                options=self.get_options(donation))
        if result["status"] == "SUCCESS":
            donation.processed = True
        return {
            "status": donation.processed,
            "reason": result["response"].response_reason_text,
            "response": result["response"],
        }

    def get_options(self, donation):
        donor = donation.donor
        r = {}
        if donor.address:
            r["billing_address"] = {
                "name": donor.name,
                "address1": donor.address.address,
                "city": donor.address.city,
                "state": donor.address.state,
                # TODO: Support other countries
                "country": "US",
                "zip": donor.address.zipcode,
            }
        if donor.mailing_address:
            r["shipping_address"] = {
                "name": donor.name,
                "address1": donor.mailing_address.address,
                "city": donor.mailing_address.city,
                "state": donor.mailing_address.state,
                # TODO: Support other countries
                "country": "US",
                "zip": donor.mailing_address.zipcode,
            }
        return r


raw_backend = GenericBackend("ARMSTRONG_DONATIONS_BACKEND", defaults=[
    "armstrong.apps.donations.backends.AuthorizeNetBackend",
])

get_backend = raw_backend.get_backend
