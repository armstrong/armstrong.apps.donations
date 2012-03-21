from decimal import Decimal
from django.core.exceptions import ValidationError
import fudge
import random
from ._utils import generate_random_user
from ._utils import TestCase

from .. import backends
from .. import models
from ..models import (Donor, Donation, DonationType)


class DonorAddressTestCase(TestCase):
    def test_outputs_address_as_string(self):
        odd_or_even = random.randint(1, 10) % 2 is 0
        address = "%d Some St" % random.randint(100, 200)
        city = "Pleasantville" if odd_or_even else "Sometown"
        state = "TX" if odd_or_even else "CA"
        zipcode = random.randint(10000, 20000)

        donor_address = models.DonorAddress(address=address, city=city,
                state=state, zipcode=zipcode)

        expected = "%s, %s, %s, %d" % (address, city, state, zipcode)
        self.assertEqual(expected, str(donor_address))


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

    def test_outputs_name_as_string(self):
        random_name = "Random Name %d" % random.randint(100, 200)
        donor = models.Donor(name=random_name)
        self.assertEqual(random_name, str(donor))


class DonationTypeTestCase(TestCase):
    def test_outputs_name_as_string(self):
        random_name = "Random Name %d" % random.randint(1000, 2000)
        dt = models.DonationType(name=random_name)
        self.assertEqual(random_name, str(dt))


class DonationTypeOptionTestCase(TestCase):
    def test_repeat_default_to_zero(self):
        dt = models.DonationTypeOption.objects.create(name="Simple",
                amount=100, donation_type=self.get_base_donation_type())
        self.assertEqual(0, dt.repeat)

    def test_is_repeating_is_false_by_default(self):
        dt = models.DonationTypeOption.objects.create(name="Simple",
                amount=100, donation_type=self.get_base_donation_type())
        self.assertFalse(dt.is_repeating)

    def test_is_repeating_is_true_if_repeats_one_or_more_times(self):
        dt = models.DonationTypeOption.objects.create(name="Simple",
                amount=100, repeat=1,
                donation_type=self.get_base_donation_type())
        self.assertTrue(dt.is_repeating)

    def test_outputs_name_plus_amount_as_string(self):
        random_name = "Random Name %d" % random.randint(1000, 2000)
        random_amount = random.randint(1000, 2000)
        donation_type = models.DonationType.objects.create(name=random_name)
        option = models.DonationTypeOption(donation_type=donation_type,
                amount=random_amount)

        expected = "%s (%d)" % (random_name, random_amount)
        self.assertEqual(expected, str(option))


class DonationTestCase(TestCase):
    def test_is_repeating_is_false_by_default(self):
        d = Donation()
        self.assertFalse(d.is_repeating)

    def test_is_repeating_is_true_if_donation_type_repeats(self):
        dt = models.DonationTypeOption(amount=100, repeat=1,
                donation_type=DonationType.objects.create(name="Simple"))
        d = Donation()
        d.donation_type = dt
        self.assertTrue(d.is_repeating)

    def test_is_repeating_is_false_if_donation_type_does_not_repeat(self):
        dt = models.DonationTypeOption(amount=100,
                donation_type=DonationType.objects.create(name="Simple"))
        d = Donation()
        d.donation_type = dt
        self.assertFalse(d.is_repeating)

    def test_dispatches_to_configured_backend(self):
        m = Donation()
        random_card = "some-random-card-%d" % random.randint(1000, 2000)
        fake_backend = fudge.Fake()
        fake_backend.expects("purchase").with_args(m, random_card)
        fake_get_backend = fudge.Fake()
        fake_get_backend.is_callable().returns(fake_backend)
        with fudge.patched_context(backends, "get_backend", fake_get_backend):
            m.purchase(random_card)

        fudge.verify()

    def test_uses_donation_type_if_no_amount_provided(self):
        dt = DonationType.objects.create(name="$10")
        donation_type = models.DonationTypeOption.objects.create(
                donation_type=dt, amount="10")
        d = Donation()
        d.donation_type = donation_type
        d.donor = self.random_donor

        self.assertEqual(None, d.amount, msg="sanity check")
        d.save()
        self.assertEqual(d.amount, donation_type.amount)

    def test_code_calculate_is_called_on_save_if_present(self):
        random_amount = "%s" % self.random_amount
        d = Donation()
        d.donor = self.random_donor
        d.amount = "1000"

        code = models.PromoCode.objects.create(code="random", amount="0")

        calculate = fudge.Fake()
        calculate.expects_call().with_args(d).returns(random_amount)
        with fudge.patched_context(code, "calculate", calculate):
            d.code = code
            d.save()

        self.assertEqual(random_amount, d.amount)
        fudge.verify()

    def test_has_an_attribution_field(self):
        self.assertModelHasField(models.Donation(), "attribution",
                models.models.CharField)

    def test_has_an_anonymous_field(self):
        self.assertModelHasField(models.Donation(), "anonymous",
                models.models.BooleanField)

    def test_can_be_cast_to_string(self):
        donor = self.random_donor
        amount = self.random_amount
        donation = models.Donation(donor=donor, amount=amount)

        expected = "%s donated %s" % (donor, amount)
        self.assertEqual(expected, str(donation))


class PromoCodeTestCase(TestCase):
    def test_calculate_returns_calculated_amount(self):
        random_amount = self.random_amount
        random_discount = random.randint(10, 30)
        donation = fudge.Fake()
        donation.has_attr(amount=random_amount)

        code = models.PromoCode.objects.create(code="testing",
                amount=random_discount)
        expected = Decimal(round(
                Decimal(random_amount)
                * Decimal(1 - random_discount / 100.00), 2))
        self.assertEqual(expected, code.calculate(donation))

    def test_calculate_can_handle_amount_of_zero(self):
        random_amount = self.random_amount
        donation = fudge.Fake()
        donation.has_attr(amount=random_amount)

        code = models.PromoCode.objects.create(code="zero", amount=0)
        self.assertEqual(random_amount, code.calculate(donation))

    def test_calculate_can_handle_free_discount(self):
        donation = fudge.Fake()
        donation.has_attr(amount=100)

        code = models.PromoCode.objects.create(code="free", amount=100)
        self.assertEqual(0, code.calculate(donation))

    def test_can_handle_rounding_issues(self):
        donation = fudge.Fake().has_attr(amount=100)
        code = models.PromoCode.objects.create(code="causes issues",
                amount=13)
        self.assertEqual(Decimal("87.0"), code.calculate(donation))

    def test_can_handle_less_than_1_rounding(self):
        donation = fudge.Fake().has_attr(amount=1)
        code = models.PromoCode.objects.create(code="< $1", amount=10)
        self.assertAlmostEqual(Decimal("0.90"), code.calculate(donation))


class DonationWorkFlowTestCase(TestCase):
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
        self.assertEqual(discount.calculate(donation_type), d.amount)
