from copy import copy
from django import forms
from django.conf import settings
from django.contrib.auth.models import User

from .constants import MONTH_CHOICES
from .constants import YEAR_CHOICES
from .constants import MAILING_SAME_AS_BILLING

from . import models
from . import text

state_kwargs_fields = {}
if hasattr(settings, "ARMSTRONG_INITIAL_STATE"):
    state_kwargs_fields["initial"] = settings.ARMSTRONG_INITIAL_STATE


class BaseDonationForm(forms.Form):
    """
    Provides the basic fields common to all donation forms

    This is meant to be overridden by the forms returned by a
    ``Backend.get_form_class`` to provide specific implementations.
    """
    first_name = forms.CharField()
    last_name = forms.CharField()
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
            "attribution": self.cleaned_data["attribution"],
            "anonymous": bool(self.cleaned_data["anonymous"]),
        }

    def is_valid(self, donation_only=False):
        parent = super(BaseDonationForm, self)
        donation_is_valid = parent.is_valid()
        if not donation_is_valid and "amount" in self.errors:
            donation_type_field = self.add_prefix("donation_type_pk")
            if donation_type_field in self.data:
                donation_type_pk = self.data[donation_type_field]
                try:
                    dt = models.DonationTypeOption.objects.get(pk=donation_type_pk)

                    # We've made it this far, so create a copy of the data (which is
                    # most likely an immutable `QueryDict`) and adjust the amount to
                    # the correct value before re-running is_valid().
                    self.data = copy(self.data)
                    self.data["amount"] = dt.amount
                    self._errors = None
                    donation_is_valid = parent.is_valid()
                except models.DonationTypeOption.DoesNotExist:
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
        if (promo_code_field_name in self.data
                and self.data[promo_code_field_name]):
            donation.code = models.PromoCode.objects.get(
                    code=self.data[promo_code_field_name])
        if self.add_prefix("donation_type_pk") in self.data:
            donation.donation_type = models.DonationTypeOption.objects.get(
                    pk=self.data[self.add_prefix("donation_type_pk")])
        donor = self.donor_form.save(commit=False)
        try:
            user = User.objects.get(pk=self.data[self.add_prefix("user_pk")])
            donor.user = user
            if not donor.email:
                donor.email = user.email
        except (KeyError, ValueError):
            pass
        if self.billing_address_form.is_valid():
            donor.address = self.billing_address_form.save()
            donor.mailing_address = self.mailing_address_form.save() if \
                    not self.mailing_same_as_billing else donor.address
        donor.save()
        donation.donor = donor
        donation.save()
        return donation


class StripSensitiveFields(object):
    """
    Mixin for stripping sensitive information from an invalid form

    This is meant to be used by a ``Form`` object and strips the fields
    listed in ``fields_to_strip`` if ``is_valid`` fails.
    """
    fields_to_strip = []

    def is_valid(self, *args, **kwargs):
        r = super(StripSensitiveFields, self).is_valid(*args, **kwargs)
        if not r and self.fields_to_strip:
            empty_values = [""] * len(self.fields_to_strip)
            new_data = dict(zip(self.fields_to_strip, empty_values))
            self.data = copy(self.data)
            self.data.update(new_data)
        return r


class CreditCardDonationForm(StripSensitiveFields, BaseDonationForm):
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

    fields_to_strip = ["card_number", "ccv_code", ]

    def get_data_for_charge(self, donation, **kwargs):
        """
        Returns the data for charges

        This is used to build a dictionary of data that can not be
        retrieved directly from the ``Donation`` model.
        """
        raise NotImplementedError


class AuthorizeDonationForm(CreditCardDonationForm):
    """
    Represents a ``CreditCardDonationForm`` form for Authorize.net

    This form is returned by the ``AuthorizeNetBackend.get_form_class``
    and should not be accessed directly.
    """
    def get_data_for_charge(self, donation, recurring=False):
        """Returns the data for charges"""
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
    """Simple ``ModelForm`` for the ``Donor`` model"""
    class Meta:
        model = models.Donor
        excludes = ("address", "mailing_address", )


class DonorAddressForm(forms.ModelForm):
    """Simple ``ModelForm`` for the ``DonorAddress`` model"""
    address = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = models.DonorAddress
