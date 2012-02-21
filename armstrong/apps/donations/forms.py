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

    def __init__(self, data=None, prefix=None, *args, **kwargs):
        # TODO: provide custom prefixes to each sub-form
        self.mailing_same_as_billing = False
        # TODO: make this work with prefixes
        if (data and MAILING_SAME_AS_BILLING in data and
                data[MAILING_SAME_AS_BILLING]):
            self.mailing_same_as_billing = True
        self.donor_form = self.get_donor_form(data=data, prefix=prefix,
                *args, **kwargs)
        billing_address_prefix = "%sbilling" % ("" if not prefix else prefix)
        self.billing_address_form = self.get_billing_address_form(
                data=data, prefix=billing_address_prefix, empty_permitted=True,
                *args, **kwargs)
        self.billing_address_form.empty_permitted = True
        mailing_address_prefix = "%smailing" % ("" if not prefix else prefix)
        self.mailing_address_form = self.get_mailing_address_form(
                data=data, prefix=mailing_address_prefix, *args, **kwargs)
        self.mailing_address_form.empty_permitted = True
        super(BaseDonationForm, self).__init__(data=data, prefix=prefix,
                *args, **kwargs)

    def get_billing_address_form(self, *args, **kwargs):
        return DonorAddressForm(*args, **kwargs)

    def get_mailing_address_form(self, *args, **kwargs):
        return DonorAddressForm(*args, **kwargs)

    def get_donor_form(self, *args, **kwargs):
        return DonorForm(*args, **kwargs)

    def get_donation_kwargs(self):
        if not self.is_valid(donation_only=True):
            return {}
        return {
            "amount": self.cleaned_data["amount"],
        }

    def is_valid(self, donation_only=False):
        donation_is_valid = super(BaseDonationForm, self).is_valid()
        if not donation_is_valid:
            donation_type_field = self.add_prefix("donation_type")
            if donation_type_field in self.data:
                donation_type_name = self.data[self.add_prefix("donation_type")]
                try:
                    models.DonationType.objects.get(name=donation_type_name)
                    donation_is_valid = True
                except models.DonationType.DoesNotExist:
                    donation_is_valid = False

        if donation_only:
            return donation_is_valid
        mailing_address_validity = self.billing_address_form.is_valid() \
                if self.mailing_same_as_billing \
                else self.mailing_address_form.is_valid()
        return all([
            donation_is_valid,
            self.donor_form.is_valid(),
            self.billing_address_form.is_valid(),
            mailing_address_validity,
        ])

    # TODO: support commit=True?
    def save(self, **kwargs):
        donation = models.Donation(**self.get_donation_kwargs())
        promo_code_field_name = self.add_prefix("promo_code")
        if promo_code_field_name in self.data and self.data[promo_code_field_name]:
            donation.code = models.PromoCode.objects.get(
                    code=self.data[promo_code_field_name])
        if self.add_prefix("donation_type") in self.data:
            donation.donation_type = models.DonationType.objects.get(
                    name=self.data[self.add_prefix("donation_type")])
        donor = self.donor_form.save(commit=False)
        if self.billing_address_form.is_valid():
            donor.address = self.billing_address_form.save()
            donor.mailing_address = self.mailing_address_form.save() if \
                    not self.mailing_same_as_billing else donor.address
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


class DonorAddressForm(forms.ModelForm):
    address = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = models.DonorAddress
