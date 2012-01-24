from armstrong.dev.tests.utils.base import ArmstrongTestCase
from armstrong.dev.tests.utils.users import generate_random_user
import random

from ..models import (DonorMailingAddress, Donor, DonationType, PromoCode)


class TestCase(ArmstrongTestCase):
    @property
    def random_donor_name(self):
        return "Bob Example (%d)" % random.randint(100, 200)

    @property
    def random_address_kwargs(self):
        return {
            "address": "%d Some St" % random.randint(1000, 2000),
            "city": "Anytown",
            "state": "TX",
        }

    @property
    def random_address(self):
        return DonorMailingAddress.objects.create(**self.random_address_kwargs)

    @property
    def random_donor(self):
        return Donor.objects.create(
            name=self.random_donor_name,
            address=self.random_address,
            mailing_address=self.random_address
        )

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

    @property
    def random_amount(self):
        return random.randint(1, 100)

    def get_data_as_formset(self, data=None, prefix="form", total_forms=None,
            initial_forms=u"0", max_num_forms=u""):
        if data is None:
            data = []
        # TODO: write tests for this
        if type(data) is dict:
            data = [data, ]
        if not total_forms:
            total_forms = len(data)
        r = {
            "%s-TOTAL_FORMS" % prefix: total_forms,
            "%s-INITIAL_FORMS" % prefix: initial_forms,
            "%s-MAX_NUM_FORMS" % prefix: max_num_forms,
        }
        for idx, a in zip(range(len(data)), data):
            for k, v in a.items():
                r["%s-%d-%s" % (prefix, idx, k)] = v
        return r
