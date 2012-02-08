from billing import CreditCard
from ._utils import TestCase

from .. import forms


class BaseDonationFormTestCase(TestCase):
    def test_applies_promo_code(self):
        promo_code = self.random_discount
        data = self.get_base_random_data()
        data["promo_code"] = promo_code.code
        form = forms.BaseDonationForm(data)
        donation = form.save()
        self.assertEqual(promo_code, donation.code)

    def test_errors_if_more_than_two_digits_are_provided(self):
        form = forms.BaseDonationForm(data={"amount": "100.123"})
        self.assertFalse(form.is_valid(donation_only=True))
        self.assertTrue("amount" in form.errors)


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
