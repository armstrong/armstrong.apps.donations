import billing
from django import forms
from django.conf import settings
from django.forms.models import modelformset_factory

from .constants import MONTH_CHOICES
from .constants import YEAR_CHOICES
from .constants import MAILING_SAME_AS_BILLING

from . import models
from . import text

state_kwargs_fields = {}
if hasattr(settings, "ARMSTRONG_INITIAL_STATE"):
    state_kwargs_fields["initial"] = settings.ARMSTRONG_INITIAL_STATE


class BaseDonationForm(forms.Form):
    name = forms.CharField()
    amount = forms.DecimalField()
    attribution = forms.CharField(required=False,
            help_text=text.get("donation.help_text.attribution"))
    anonymous = forms.BooleanField(required=False,
            label=text.get("donation.label.anonymous"))

    def __init__(self, *args, **kwargs):
        # TODO: provide custom prefixes to each sub-form
        self.donor_form = self.get_donor_form(*args, **kwargs)
        self.address_formset = self.get_address_formset(*args, **kwargs)
        super(BaseDonationForm, self).__init__(*args, **kwargs)

    def get_donor_form(self, *args, **kwargs):
        return DonorForm(*args, **kwargs)

    def _formset_is_populated(self, *args, **kwargs):
        # TODO: there has to be a better way to do this...?
        if "data" in kwargs:
            data = kwargs["data"]
        elif len(args):
            data = args[0]
        else:
            data = {}
        for key in data.keys():
            if key.startswith("form-"):
                return True
        return False

    def get_address_formset(self, *args, **kwargs):
        if self._formset_is_populated(*args, **kwargs):
            return DonorAddressFormset(*args, **kwargs)
        return DonorAddressFormset()

    def get_donation_kwargs(self):
        if not self.is_valid():
            # TODO: raise here?
            return {}
        return {
            "amount": self.cleaned_data["amount"],
        }

    def is_valid(self):
        return all([
            super(BaseDonationForm, self).is_valid(),
            self.donor_form.is_valid(),
            self.address_formset.is_valid(),
        ])

    # TODO: support commit=True?
    def save(self, **kwargs):
        donation = models.Donation(**self.get_donation_kwargs())
        donor = self.donor_form.save(commit=False)
        self.address_formset.save(donor)
        donor.save()
        donation.donor = donor
        donation.save()
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


BaseDonorAddressFormset = modelformset_factory(models.DonorAddress)


class DonorAddressFormset(BaseDonorAddressFormset):
    def __init__(self, data=None, **kwargs):
        self.mailing_same_as_billing = False
        if data and MAILING_SAME_AS_BILLING in data:
            self.mailing_same_as_billing = True
        super(DonorAddressFormset, self).__init__(data=data, **kwargs)

    def save(self, donor, **kwargs):
        instances = super(DonorAddressFormset, self).save(**kwargs)
        if len(instances):
            donor.address = instances[0]
            if len(instances) is 2:
                donor.mailing_address = instances[1]
            elif self.mailing_same_as_billing:
                donor.mailing_address = donor.address
        return instances
