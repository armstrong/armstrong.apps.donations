from armstrong.utils.backends import GenericBackend

from . import forms


class AuthorizeNetBackend(object):
    def get_form_class(self):
        return forms.CreditCardDonationForm

    def purchase(self, model, form):
        pass


raw_backend = GenericBackend("ARMSTRONG_DONATIONS_BACKEND", defaults=[
    "armstrong.apps.donations.backends.AuthorizeNetBackend",
])

get_backend = raw_backend.get_backend
