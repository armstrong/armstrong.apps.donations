from ._utils import TestCase

from .. import forms


class DonorFormTestCase(TestCase):
    def test_saves_a_donor_model(self):
        random_donor_name = self.random_donor_name
        form = forms.DonorForm({
            "name": random_donor_name
        })
        self.assertTrue(form.is_valid())
        donor = form.save()
        self.assertEqual(random_donor_name, donor.name)


class DonationInlineFormsetTestCase(TestCase):
    def get_data_as_formset(self, data, prefix="donation_set",
            total_forms=u"1", initial_forms=u"0", max_num_forms=u""):
        return super(DonationInlineFormsetTestCase, self).get_data_as_formset(
                data, prefix=prefix, total_forms=total_forms,
                initial_forms=initial_forms, max_num_forms=max_num_forms)

    def test_saves_donation_for_donor(self):
        donor = self.random_donor
        data = self.get_data_as_formset({
            "amount": self.random_amount,
        })

        formset = forms.DonationInlineFormset(data, instance=donor)
        self.assertTrue(formset.is_valid())
        donation = formset.save()[0]
        self.assertEqual(donation.donor, donor)
