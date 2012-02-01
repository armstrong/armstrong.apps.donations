import billing
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


class CreditCardDonationForm(BaseDonationForm):
    """
    Form representing the credit card donation process for Authorize.net

    It's possible that this can work with other backends, but it has not
    been tested.

    Each specific Donation form should create what is necessary for their
    backend's implemenation of `purchase`.

    .. todo:: Add widget that is smart for expiration dates
    """
    card_number = forms.CharField()
    ccv_code = forms.CharField()
    expiration_month = forms.ChoiceField(choices=MONTH_CHOICES)
    expiration_year = forms.ChoiceField(choices=YEAR_CHOICES)

    def get_credit_card(self, donor):
        self.is_valid()  # TODO: do something when bad data is here

        name = donor.name
        first_name, last_name = name.split(" ", 1)
        return billing.CreditCard(
            first_name=first_name,
            last_name=last_name,
            number=self.cleaned_data["card_number"],
            month=self.cleaned_data["expiration_month"],
            year=self.cleaned_data["expiration_year"],
            verification_value=self.cleaned_data["ccv_code"],
        )


class DonorForm(forms.ModelForm):
    class Meta:
        model = models.Donor
        excludes = ("address", "mailing_address", )

DonorAddressFormset = modelformset_factory(models.DonorAddress)
