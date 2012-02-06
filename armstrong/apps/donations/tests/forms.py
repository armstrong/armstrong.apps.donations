from billing import CreditCard
from ._utils import TestCase

from .. import forms


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

    def test_get_credit_card_returns_creditcard_object(self):
        card = self.donation_form.get_credit_card(self.donor)
        self.assertIsA(card, CreditCard)

        expected_first_name = self.donor.name.split(" ")[0]
        self.assertEqual(expected_first_name, card.first_name)
        expected_last_name = self.donor.name.split(" ", 1)[1]
        self.assertEqual(expected_last_name, card.last_name)
        self.assertEqual(self.card_number, card.number)
        self.assertEqual(self.ccv_code, card.verification_value)
        self.assertEqual(int(self.expiration_year), card.year)
        self.assertEqual(int(self.expiration_month), card.month)
