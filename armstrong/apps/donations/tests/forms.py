import fudge
import random
from ._utils import TestCase

from .. import constants
from .. import forms
from .. import models


class BaseDonationFormTestCase(TestCase):
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
            "%s-name" % prefix: "Bob Example",
            "%s-promo_code" % prefix: promo_code.code,
        }
        form = forms.BaseDonationForm(prefix=prefix, data=data)
        donation = form.save()
        self.assertEqual(promo_code, donation.code)

    def test_errors_if_more_than_two_digits_are_provided(self):
        form = forms.BaseDonationForm(data={"amount": "100.123"})
        self.assertFalse(form.is_valid(donation_only=True))
        self.assertTrue("amount" in form.errors)

    def test_donation_type_is_used_if_present(self):
        random_type = self.random_type
        form = forms.BaseDonationForm(data={
            "amount": "100",
            "name": "Bob Example",
            "donation_type": random_type.name,
        })
        donation = form.save()
        self.assertEqual(random_type, donation.donation_type)

    def test_donation_type_works_with_prefixed_forms(self):
        random_type = self.random_type
        prefix = "random%d" % random.randint(1, 9)
        form = forms.BaseDonationForm(prefix=prefix, data={
            "%s-amount" % prefix: "100",
            "%s-name" % prefix: "Bob Example",
            "%s-donation_type" % prefix: random_type.name,
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
                "name": "Foo",
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
                "name": "Foo",
                "amount": "10.00",
                constants.MAILING_SAME_AS_BILLING: u"1",
        })
        attrs = ["billing_address_form", "donor_form"]
        for attr in attrs:
            setattr(form, attr, is_valid_true)
        form.mailing_address_form = is_valid_false
        self.assertTrue(form.is_valid())

    def test_saves_mailing_address_if_present(self):
        donor_name = self.random_donor_name
        address_kwargs = self.random_address_kwargs
        mailing_address_kwargs = self.random_address_kwargs
        data = self.get_base_random_data(name=donor_name)
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

        donor = models.Donor.objects.get(name=donor_name)
        # import ipdb; ipdb.set_trace()
        self.assertEqual(address, donor.address)
        self.assertEqual(mailing_address, donor.mailing_address)


class CreditCardDonationFormTestCase(TestCase):
    def setUp(self):
        data = self.get_base_random_data()
        self.donor = self.random_donor
        data = self.get_base_random_data(name=self.donor.name)
        self.amount = data["amount"]
        self.donation_form = forms.CreditCardDonationForm(data)
        self.card_number = data["card_number"]
        self.ccv_code = data["ccv_code"]
        self.expiration_month = data["expiration_month"]
        self.expiration_year = data["expiration_year"]

    # TODO: test get_data_for_charge directly
