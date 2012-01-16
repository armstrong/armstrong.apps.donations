from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _


class DonorManager(models.Manager):
    def create_for_user(self, user):
        return self.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name
        )


class Donor(models.Model):
    user = models.ForeignKey(User, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    objects = DonorManager()


class DonationType(models.Model):
    name = models.CharField(
        max_length=100, help_text=_(u"Name of Donation Type")
    )
    yearly = models.PositiveIntegerField(
        default=None, null=True, blank=True,
        help_text=_(u"Amount to donate for the year")
    )
    monthly = models.PositiveIntegerField(
        default=None, null=True, blank=True,
        help_text=_(u"Amount to donate for the month")
    )
    repeat = models.PositiveIntegerField(
        default=None, null=True, blank=True,
        help_text=_(u"Number of times (if any) this donation will repeat")
    )

    @property
    def amount(self):
        return self.yearly if self.yearly else self.monthly

    def clean(self):
        """
        Validate that this model is in the state you'd except

        This is called by the various ModelForms that interact with it.
        Keep in mind that this is not called when you explicitly create
        a model via `objects.create()`.
        """
        from django.core.exceptions import ValidationError
        if self.yearly and self.monthly:
            raise ValidationError(_(u"You cannot use both yearly and monthly"))


class PromoCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    amount = models.FloatField(
        help_text=_("Percent discount: 0 is no discount, 100 if free")
    )

    def __unicode__(self):
        return u"%s (%s%%)" % (self.code, self.amount)

    def calculate(self, amount):
        return amount * (1 - self.amount / 100.0)


class DonationManager(models.Manager):
    def create(self, **kwargs):
        if "donation_type" in kwargs and not "amount" in kwargs:
            kwargs["amount"] = kwargs["donation_type"].amount
        if "code" in kwargs:
            kwargs["amount"] = kwargs["code"].calculate(kwargs["amount"])
        return super(DonationManager, self).create(**kwargs)


class Donation(models.Model):
    donor = models.ForeignKey(Donor)
    donation_type = models.ForeignKey(DonationType, null=True, blank=True)
    code = models.ForeignKey(PromoCode, null=True, blank=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True)

    objects = DonationManager()
