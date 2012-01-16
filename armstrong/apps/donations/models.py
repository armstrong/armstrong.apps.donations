from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Donor(models.Model):
    user = models.ForeignKey(User, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def save(self, **kwargs):
        if self.user:
            if not self.first_name:
                self.first_name = self.user.first_name
            if not self.last_name:
                self.last_name = self.user.last_name
        super(Donor, self).save(**kwargs)


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


class Donation(models.Model):
    donor = models.ForeignKey(Donor)
    donation_type = models.ForeignKey(DonationType, null=True, blank=True)
    code = models.ForeignKey(PromoCode, null=True, blank=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True)

    def save(self, **kwargs):
        if self.donation_type and not self.amount:
            self.amount = self.donation_type.amount
        if self.code:
            self.amount = self.code.calculate(self.amount)
        return super(Donation, self).save(**kwargs)
