from django.db import models


class DonorManager(models.Manager):
    def create_for_user(self, user):
        return self.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name
        )


class DonationManager(models.Manager):
    def create(self, **kwargs):
        if "donation_type" in kwargs and not "amount" in kwargs:
            kwargs["amount"] = kwargs["donation_type"].amount
        if "code" in kwargs:
            kwargs["amount"] = kwargs["code"].calculate(kwargs["amount"])
        return super(DonationManager, self).create(**kwargs)
