from django.http import QueryDict
import fudge
import random
from urllib import urlencode
from ._utils import TestCase

from .. import constants
from .. import forms
from .. import models


class DjangoFormAssertionsMixin(object):
    def assert_field_error(self, form, field_name):
        self.assertFalse(form.is_valid(), msg="sanity check")
        self.assert_(field_name in form.errors,
                msg="%s not in form errors" % field_name)


class BaseDonationFormTestCase(DjangoFormAssertionsMixin, TestCase):
    def test_attribution_is_stored(self):
        random_attribution = "Random Attribution %d" % random.randint(100, 200)
        data = self.get_base_random_data()
        data["attribution"] = random_attribution
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertEqual(random_attribution, donation.attribution)

    def test_anonymous_is_off_by_default_with_no_attribution_provided(self):
        data = self.get_base_random_data()
        if "anonymous" in data:
            del data["anonymous"]
        donation = forms.BaseDonationForm(data).save()
        self.assertFalse(donation.anonymous)

    def test_anonymous_is_off_if_an_empty_anonymous_value_is_provided(self):
        data = self.get_base_random_data()
        data["anonymous"] = ""
        donation = forms.BaseDonationForm(data).save()
        self.assertFalse(donation.anonymous)

    def test_anonymous_is_checked_if_present(self):
        data = self.get_base_random_data()
        data["anonymous"] = "1"
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertTrue(donation.anonymous)

    def test_applies_promo_code(self):
        promo_code = self.random_discount
        data = self.get_base_random_data()
        data["promo_code"] = promo_code.code
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertEqual(promo_code, donation.code)

    def test_applies_promo_code_with_prefixed_form(self):
        prefix = "random%d" % random.randint(1, 9)
        promo_code = self.random_discount
        data = {
            "%s-amount" % prefix: "100",
            "%s-first_name" % prefix: "Bob",
            "%s-last_name" % prefix: "Example",
            "%s-promo_code" % prefix: promo_code.code,
        }
        form = forms.BaseDonationForm(prefix=prefix, data=data)
        donation = form.save()
        self.assertEqual(promo_code, donation.code)

    def test_can_save_with_an_empty_promo_code(self):
        data = self.get_base_random_data()
        data["promo_code"] = ""
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertEqual(None, donation.code)

    def test_does_not_save_user_by_default(self):
        data = self.get_base_random_data()
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertEqual(None, donation.donor.user)

    def test_saves_user_if_user_pk_is_submitted(self):
        user = self.random_user
        data = self.get_base_random_data()
        data["user_pk"] = user.pk
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertEqual(user.pk, donation.donor.user.pk)

    def test_behaves_if_an_empty_user_pk_is_given(self):
        data = self.get_base_random_data()
        data["user_pk"] = ""
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertEqual(None, donation.donor.user)

    def test_saves_email_if_submitted(self):
        data = self.get_base_random_data()
        data["email"] = "bob@example.com"
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertEqual("bob@example.com", donation.donor.email)

    def test_uses_user_email_if_no_email_is_present(self):
        user = self.random_user
        user.email = "alice@example.com"
        user.save()
        data = self.get_base_random_data()
        data["user_pk"] = user.pk
        data["email"] = ""
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertEqual("alice@example.com", donation.donor.email)

    def test_saves_user_if_user_pk_is_submitted_on_prefixed_form(self):
        prefix = "prefix%d" % random.randint(100, 200)
        user = self.random_user
        form = forms.BaseDonationForm(prefix=prefix, data={
            "%s-amount" % prefix: "100",
            "%s-first_name" % prefix: "Bob",
            "%s-last_name" % prefix: "Example",
            "%s-donation_type_pk" % prefix: self.random_type.pk,
            "%s-user_pk" % prefix: user.pk,
        })
        donation = form.save()
        self.assertEqual(user.pk, donation.donor.user.pk)

    def test_errors_if_more_than_two_digits_are_provided(self):
        form = forms.BaseDonationForm(data={"amount": "100.123"})
        self.assertFalse(form.is_valid(donation_only=True))
        self.assertTrue("amount" in form.errors)

    def test_donation_type_is_used_if_present(self):
        random_type = self.random_type
        form = forms.BaseDonationForm(data={
            "amount": "100",
            "first_name": "Bob",
            "last_name": "Example",
            "donation_type_pk": random_type.pk,
        })
        donation = form.save()
        self.assertEqual(random_type, donation.donation_type)

    def test_donation_type_works_with_prefixed_forms(self):
        random_type = self.random_type
        prefix = "random%d" % random.randint(1, 9)
        form = forms.BaseDonationForm(prefix=prefix, data={
            "%s-amount" % prefix: "100",
            "%s-first_name" % prefix: "Bob",
            "%s-last_name" % prefix: "Example",
            "%s-donation_type_pk" % prefix: random_type.pk,
        })
        donation = form.save()
        self.assertEqual(random_type, donation.donation_type)

    def test_billing_address_form_is_a_donoraddressform(self):
        f = forms.BaseDonationForm()
        self.assertIsA(f.billing_address_form, forms.DonorAddressForm)

    def test_mailing_address_form_is_aa_donoraddressform(self):
        f = forms.BaseDonationForm()
        self.assertIsA(f.mailing_address_form, forms.DonorAddressForm)

    def test_is_valid_uses_mailing_address_form_by_default(self):
        is_valid_true = fudge.Fake().provides("is_valid").returns(True)
        is_valid_false = fudge.Fake().provides("is_valid").returns(False)
        form = forms.BaseDonationForm(data={
                "first_name": "Foo",
                "last_name": "Bar",
                "amount": "10.00",
        })
        attrs = ["billing_address_form", "donor_form", "mailing_address_form"]
        for attr in attrs:
            setattr(form, attr, is_valid_true)
        self.assertTrue(form.is_valid())

        form.mailing_address_form = is_valid_false
        self.assertFalse(form.is_valid())

    def test_is_valid_ignores_mailing_if_same_checked(self):
        is_valid_true = fudge.Fake().provides("is_valid").returns(True)
        is_valid_false = fudge.Fake().provides("is_valid").returns(False)
        form = forms.BaseDonationForm(data={
                "first_name": "Foo",
                "last_name": "Bar",
                "amount": "10.00",
                constants.MAILING_SAME_AS_BILLING: u"1",
        })
        attrs = ["billing_address_form", "donor_form"]
        for attr in attrs:
            setattr(form, attr, is_valid_true)
        form.mailing_address_form = is_valid_false
        self.assertTrue(form.is_valid())

    def test_saves_mailing_address_if_present(self):
        name_kwargs = self.random_donor_kwargs
        address_kwargs = self.random_address_kwargs
        mailing_address_kwargs = self.random_address_kwargs
        data = self.get_base_random_data(**name_kwargs)
        data.update(self.prefix_data(address_kwargs, prefix="billing"))
        data.update(self.prefix_data(mailing_address_kwargs, prefix="mailing"))
        del data[constants.MAILING_SAME_AS_BILLING]

        self.assertEqual(0, len(models.DonorAddress.objects.all()),
            msg="sanity check")
        form = forms.BaseDonationForm(data=data)
        form.save()
        self.assertEqual(2, len(models.DonorAddress.objects.all()))
        address = models.DonorAddress.objects.get(**address_kwargs)
        mailing_address = models.DonorAddress.objects.get(
                **mailing_address_kwargs)
        self.assertNotEqual(address, mailing_address)

        donor = models.Donor.objects.get(**name_kwargs)
        # import ipdb; ipdb.set_trace()
        self.assertEqual(address, donor.address)
        self.assertEqual(mailing_address, donor.mailing_address)

    def test_is_valid_is_true_if_donation_type_provided_and_no_amount(self):
        donation_type = self.random_type
        address_kwargs = self.random_address_kwargs
        data = self.get_base_random_data(donation_type_pk=donation_type.pk)
        data.update(self.prefix_data(address_kwargs, prefix="billing"))
        del data["amount"]

        form = forms.BaseDonationForm(data=data)
        self.assertTrue(form.is_valid())

    def test_cleaned_data_is_available_with_dt_and_no_amount(self):
        donation_type = self.random_type
        address_kwargs = self.random_address_kwargs
        data = self.get_base_random_data(donation_type_pk=donation_type.pk)
        data.update(self.prefix_data(address_kwargs), prefix="billing")
        del data["amount"]

        form = forms.BaseDonationForm(data=data)
        form.is_valid()
        self.assertEqual(form.cleaned_data["amount"], donation_type.amount)

    def test_is_valid_returns_false_with_invalid_donation_type(self):
        address_kwargs = self.random_address_kwargs
        data = self.get_base_random_data(
                donation_type="unknown and unknowable")
        data.update(self.prefix_data(address_kwargs, prefix="billing"))
        del data["amount"]

        form = forms.BaseDonationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_is_valid_respects_form_even_with_valid_donation_type(self):
        donation_type = self.random_type
        address_kwargs = self.random_address_kwargs
        data = self.get_base_random_data(donation_type_pk=donation_type.pk)
        data.update(self.prefix_data(address_kwargs, prefix="billing"))
        del data["amount"]
        del data["first_name"]

        form = forms.BaseDonationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_is_valid_works_with_sub_forms(self):
        donation_type = self.random_type
        address_kwargs = self.random_address_kwargs
        data = self.get_base_random_data(donation_type_pk=donation_type.pk)
        data.update(self.prefix_data(address_kwargs, prefix="billing"))
        del data["amount"]

        class MyAwesomeForm(forms.BaseDonationForm):
            extra_field = forms.forms.BooleanField()

        form = MyAwesomeForm(data=data)
        self.assertFalse(form.is_valid())

    def test_has_a_donor_form_property(self):
        form = forms.BaseDonationForm()
        self.assertIsA(form.donor_form, forms.DonorForm)

    def test_is_valid_returns_false_if_donor_form_invalid_donor(self):
        for field_name in ["first_name", "last_name", ]:
            data = self.get_base_random_data()
            del data[field_name]
            form = forms.BaseDonationForm(data=data)
            self.assertFalse(form.is_valid())
            self.assert_field_error(form.donor_form, field_name)


class CreditCardDonationFormTestCase(TestCase):
    form_class = forms.CreditCardDonationForm

    def setUp(self):
        name_kwargs = self.random_address_kwargs
        data = self.get_base_random_data(**name_kwargs)
        self.amount = data["amount"]
        self.card_number = data["card_number"]
        self.ccv_code = data["ccv_code"]
        self.expiration_month = data["expiration_month"]
        self.expiration_year = data["expiration_year"]
        self.data = data

    def get_form(self, *args, **kwargs):
        return self.form_class(*args, **kwargs)

    def get_invalid_form(self):
        del self.data["amount"]
        return self.get_form(data=self.data)

    def assert_value_is_empty(self, field):
        form = self.get_invalid_form()
        form.data = QueryDict(urlencode(form.data))
        form.fields_to_strip = ["card_number", "ccv_code"]
        self.assertFalse(form.is_valid())
        self.assertEqual("", form[field].value())

    def assert_value_is_not_empty(self, field):
        form = self.get_invalid_form()
        form.fields_to_strip = []
        self.assertFalse(form.is_valid())
        self.assertNotEqual("", form[field].value())

    def test_clears_credit_card_numbers_if_form_is_invalid(self):
        self.assert_value_is_empty("card_number")

    def test_clears_ccv_card_numbers_if_form_is_invalid(self):
        self.assert_value_is_empty("ccv_code")

    def test_does_not_clear_card_numbers_if_form_is_invalid(self):
        self.assert_value_is_not_empty("card_number")

    def test_does_not_clear_ccv_codes_if_form_is_invalid(self):
        self.assert_value_is_not_empty("ccv_code")

    def test_can_configure_the_fields_to_strip(self):
        form = self.get_invalid_form()
        form.fields_to_strip = ["card_number", ]
        form.is_valid()

        self.assertEqual("", form["card_number"].value())
        self.assertNotEqual("", form["ccv_code"].value())


class AuthorizeDonationFormTestCase(CreditCardDonationFormTestCase):
    form_class = forms.AuthorizeDonationForm
