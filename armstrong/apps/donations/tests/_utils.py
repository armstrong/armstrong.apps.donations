from armstrong.dev.tests.utils.base import ArmstrongTestCase
from armstrong.dev.tests.utils.users import generate_random_user
import datetime
from django.test.client import RequestFactory
import fudge
import random

from .. import forms
from ..models import (Donation, DonorAddress, Donor, DonationType, PromoCode)


def no_initial_patched_objects(func):
    def inner(self, *args, **kwargs):
        self.restore_patched_objects()
        self.patched = []
        return func(self, *args, **kwargs)
    return inner


class TestCase(ArmstrongTestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        # TODO: move this to armstrong.dev
        self.factory = RequestFactory()

    def tearDown(self):
        self.restore_patched_objects()

    def restore_patched_objects(self):
        if hasattr(self, "patches"):
            [p.restore() for p in self.patches]

    @property
    def random_donor_name(self):
        return "Bob Example (%d)" % random.randint(100, 200)

    @property
    def random_address_kwargs(self):
        return {
            "address": "%d Some St" % random.randint(1000, 2000),
            "city": "Anytown",
            "state": "TX",
            "zipcode": "787%02d" % random.randint(1, 99),
        }

    @property
    def random_address(self):
        return DonorAddress.objects.create(**self.random_address_kwargs)

    @property
    def random_donor(self):
        return Donor.objects.create(
            name=self.random_donor_name,
            address=self.random_address,
            mailing_address=self.random_address
        )

    @property
    def random_donation(self):
        return Donation.objects.create(
            amount=self.random_amount,
            donor=self.random_donor,
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

    @property
    def random_card_number(self):
        card_numbers = {
            "amex": "370000000000002",
            "discover": "6011000000000012",
            "visa": "4222222222222222",
            "mastercard": "5555555555554444",
        }
        return card_numbers.values()[random.randint(0, 3)]

    def get_base_random_data(self, **kwargs):
        now = datetime.datetime.now()
        data = {
            "name": self.random_donor_name,
            "amount": self.random_amount,
            "card_number": self.random_card_number,
            "ccv_code": "123",
            "expiration_month": "%02d" % now.month,
            "expiration_year": "%04d" % (now + datetime.timedelta(365)).year,
            "name": self.random_donor_name,
            "mailing_same_as_billing": u"1",
        }
        data.update(kwargs)
        return data

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

    def get_payment_stub(self, successful=True, response_reason_text="Foobar"):
        fake_response = self.get_fake_purchase_response(successful,
                response_reason_text)
        fake = fudge.Fake()
        fake.provides("purchase") \
            .returns(fake_response)
        return fake

    def get_fake_purchase_response(self, successful=True,
            response_reason_text="Foobar"):
        fake = fudge.Fake()
        fake.has_attr(response_reason_text=response_reason_text)
        return {
            "status": "SUCCESS" if successful else "FAILURE",
            "response": fake,
        }

    def get_gateway_stub(self, payment_stub=None, successful=True,
            response_reason_text="Foobar"):
        if not payment_stub:
            payment_stub = self.get_payment_stub(successful=successful,
                    response_reason_text=response_reason_text)
        fake = fudge.Fake()
        fake.is_callable().returns(payment_stub)
        return fake

    def get_backend_stub(self, successful=True, reason="Foobar"):
        backend = fudge.Fake()
        backend.provides("get_form_class").returns(
                forms.CreditCardDonationForm)
        backend.provides("purchase").returns({
            "status": successful,
            "reason": reason,
            "response": "Foobar",
        })
        fake = fudge.Fake()
        fake.provides("get_backend").returns(backend)
        return fake
