from billing import CreditCard
import random
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
