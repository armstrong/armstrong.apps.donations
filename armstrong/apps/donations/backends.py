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

    def purchase(self, donation, form):
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
        status = response["reason_code"] == u"1"
        if status:
            donation.processed = True
        return {
            "status": status,
            "reason": response["reason_text"],
            "response": response,
        }


raw_backend = GenericBackend("ARMSTRONG_DONATIONS_BACKEND", defaults=[
    "armstrong.apps.donations.backends.AuthorizeNetBackend",
])

get_backend = raw_backend.get_backend
