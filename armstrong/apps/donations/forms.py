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
    amount = forms.DecimalField(decimal_places=2)
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

    def get_address_formset(self, *args, **kwargs):
        data = kwargs["data"] if "data" in kwargs else (
                args[0] if len(args) else {})
        if "form-TOTAL_FORMS" in data:
            return DonorAddressFormset(*args, **kwargs)
        return DonorAddressFormset()

    def get_donation_kwargs(self):
        if not self.is_valid(donation_only=True):
            return {}
        return {
            "amount": self.cleaned_data["amount"],
        }

    def is_valid(self, donation_only=False):
        donation_is_valid = super(BaseDonationForm, self).is_valid()
        if donation_only:
            return donation_is_valid
        return all([
            donation_is_valid,
            self.donor_form.is_valid(),
            self.address_formset.is_valid(),
        ])

    # TODO: support commit=True?
    def save(self, **kwargs):
        donation = models.Donation(**self.get_donation_kwargs())
        if self.add_prefix("promo_code") in self.data:
            donation.code = models.PromoCode.objects.get(
                    code=self.data[self.add_prefix("promo_code")])
        if self.add_prefix("donation_type") in self.data:
            donation.donation_type = models.DonationType.objects.get(
                    name=self.data[self.add_prefix("donation_type")])
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

    def get_data_for_charge(self, donor, **kwargs):
        raise NotImplementedError


class AuthorizeDonationForm(CreditCardDonationForm):
    def get_data_for_charge(self, donor, recurring=False):
        self.is_valid()
        card_number = "card_num" if not recurring else "card_number"
        data = {
            card_number: self.cleaned_data["card_number"],
            "card_code": self.cleaned_data["ccv_code"],
        }

        if recurring:
            data["expiration_date"] = u"%04d-%02d" % (
                    int(self.cleaned_data["expiration_year"]),
                    int(self.cleaned_data["expiration_month"]))
        else:
            data["exp_date"] = u"%02d-%04d" % (
                    int(self.cleaned_data["expiration_month"]),
                    int(self.cleaned_data["expiration_year"]))
        return data


class DonorForm(forms.ModelForm):
    class Meta:
        model = models.Donor
        excludes = ("address", "mailing_address", )


BaseDonorAddressFormset = modelformset_factory(models.DonorAddress)


class DonorAddressFormset(BaseDonorAddressFormset):
    def __init__(self, data=None, **kwargs):
        self.mailing_same_as_billing = False
        if (data and MAILING_SAME_AS_BILLING in data
                and data[MAILING_SAME_AS_BILLING]):
            self.mailing_same_as_billing = True
        super(DonorAddressFormset, self).__init__(data=data, **kwargs)

    def save(self, donor, **kwargs):
        instances = super(DonorAddressFormset, self).save(**kwargs)
        if len(instances):
            donor.address = instances[0]
            if self.mailing_same_as_billing:
                donor.mailing_address = donor.address
            elif len(instances) > 1:
                donor.mailing_address = instances[1]
        return instances
