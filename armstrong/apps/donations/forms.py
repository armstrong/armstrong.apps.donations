from django import forms
from django.conf import settings
from django.contrib.localflavor.us import forms as us
from django.forms.models import modelformset_factory

from .constants import MONTH_CHOICES
from .constants import YEAR_CHOICES

from . import models
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

    def get_donation_kwargs(self):
        if not self.is_valid():
            # TODO: raise here?
            return {}
        return {
            "amount": self.cleaned_data["amount"],
        }

    # TODO: support commit=True?
    def save(self, **kwargs):
        donation = models.Donation(**self.get_donation_kwargs())
        return donation

    def process_payment(self):
        """
        Required by any form implementing a donation form
        """
        raise NotImplementedError()


class CreditCardDonationForm(BaseDonationForm):
    """

    .. todo:: Add widget that is smart for expiration dates
    """
    card_number = forms.CharField()
    ccv_code = forms.CharField()
    expiration_month = forms.ChoiceField(choices=MONTH_CHOICES)
    expiration_year = forms.ChoiceField(choices=YEAR_CHOICES)


class DonorForm(forms.ModelForm):
    class Meta:
        model = models.Donor
        excludes = ("address", "mailing_address", )

DonorAddressFormset = modelformset_factory(models.DonorAddress)
