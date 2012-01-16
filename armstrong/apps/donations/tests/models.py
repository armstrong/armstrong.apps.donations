from django.core.exceptions import ValidationError
import random
from ._utils import generate_random_user
from ._utils import TestCase

from ..models import (Donor, Donation, DonationType, PromoCode)


class DonorTestCase(TestCase):
    def test_can_be_created_from_user_with_profile(self):
        user = generate_random_user()
        donor = Donor.objects.create(user=user)
        expected = "%s %s" % (user.first_name, user.last_name)
        self.assertEqual(expected, donor.name)

    def test_name_is_given_priority_if_specified_with_user(self):
        user = generate_random_user()
        name = "Bob (%d)" % random.randint(1, 10)
        d = Donor.objects.create(user=user, name=name)
        self.assertEqual(name, d.name)


class DonationTypeTestCase(TestCase):
    def test_can_not_have_both_monthly_and_yearly(self):
        with self.assertRaises(ValidationError) as e:
            d = DonationType.objects.create(name="Will Fail",
                    yearly=100, monthly=10)
            # Calling clean() here the way a ModelForm would
            d.clean()
        self.assertEqual(
            "You cannot use both yearly and monthly",
            e.exception.messages[0]
        )

    def test_amount_uses_yearly_if_available(self):
        r = random.randint(1, 100)
        a = DonationType.objects.create(name="Basic", yearly=r)
        self.assertEqual(r, a.amount)

    def test_amount_uses_monthly_if_available(self):
        r = random.randint(1, 100)
        a = DonationType.objects.create(name="Basic", monthly=r)
        self.assertEqual(r, a.amount)


class DonationWorkFlowTestCase(TestCase):
    @property
    def random_donor(self):
        return Donor.objects.create(name="Bob Example")

    @property
    def random_type(self):
        return DonationType.objects.create(
            name="Basic $20/year",
            yearly=20
        )

    @property
    def random_discount(self):
        r = random.randint(10, 30)
        return PromoCode.objects.create(
            code="for_testing",
            amount=r
        )

    def test_donations_can_be_free_form_amounts(self):
        donor = self.random_donor

        random_amount = random.randint(1, 100)
        donation = Donation.objects.create(
            amount=random_amount,
            donor=donor
        )

        self.assertEqual(random_amount, donation.amount)
        self.assertEqual(donor, donation.donor)

    def test_donations_with_a_type_use_that_information(self):
        donor = self.random_donor
        donation_type = self.random_type
        donation = Donation.objects.create(
            donation_type=donation_type,
            donor=donor
        )

        self.assertEqual(20, donation.amount)

    def test_promocodes_subtract_from_the_amount_with_a_type(self):
        donor = self.random_donor
        donation_type = self.random_type
        discount = self.random_discount
        d = Donation.objects.create(
            donation_type=donation_type,
            donor=donor,
            code=discount
        )
        self.assertEqual(discount.calculate(donation_type.amount), d.amount)
