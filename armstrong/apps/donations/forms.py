from django.forms.models import (inlineformset_factory, modelform_factory)

from .models import Donation, Donor


DonationInlineFormset = inlineformset_factory(Donor, Donation,
        extra=1, can_delete=False, max_num=1)
DonorForm = modelform_factory(Donor, exclude=("user", ))
