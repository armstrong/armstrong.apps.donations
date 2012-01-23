from django import forms
from django.conf import settings
from django.contrib.localflavor.us import forms as us

from .constants import MONTH_CHOICES
from .constants import YEAR_CHOICES

from . import text

state_kwargs_fields = {}
if hasattr(settings, "ARMSTRONG_INITIAL_STATE"):
    state_kwargs_fields["initial"] = settings.ARMSTRONG_INITIAL_STATE


class BaseDonationForm(forms.Form):
    name = forms.CharField()
    amount = forms.CharField()
    attribution = forms.CharField(required=False,
            help_text=text.get("donation.help_text.attribution"))
    anonymous = forms.BooleanField(required=False,
            label=text.get("donation.label.anonymous"))

    def process_payment(self):
        """
        Required by any form implementing a donation form
        """
        raise NotImplementedError()


class CreditCardDonationForm(BaseDonationForm):
    """

    .. todo:: Add widget that is smart for expiration dates
    """
    names = forms.CharField()
    card_number = forms.CharField()
    ccv_code = forms.CharField()
    expiration_month = forms.ChoiceField(choices=MONTH_CHOICES)
    expiration_year = forms.ChoiceField(choices=YEAR_CHOICES)

    def process_payment(self):
        pass


class AddressForm(forms.Form):
    address = forms.CharField(widget=forms.Textarea)
    city = forms.CharField()
    state = us.USStateField(widget=us.USStateSelect(), **state_kwargs_fields)
    zip_code = us.USZipCodeField()

# TODO: Add formset
