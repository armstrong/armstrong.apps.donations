from decimal import Decimal
from django.contrib.auth.models import User
from django.contrib.localflavor.us import models as us
from django.db import models
from django.utils.translation import ugettext_lazy as _


class DonorAddress(models.Model):
    """
    Address associated with a ``Donor``
    """
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=20)
    state = us.USStateField()
    zipcode = models.CharField(max_length=10)

    def __unicode__(self):
        return "%(address)s, %(city)s, %(state)s, %(zipcode)s" % self.__dict__


class Donor(models.Model):
    user = models.ForeignKey(User, blank=True, null=True)
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    address = models.ForeignKey(DonorAddress, related_name="addresses",
            null=True, blank=True)
    mailing_address = models.ForeignKey(DonorAddress,
            related_name="mailing_addresses", null=True, blank=True)
    # TODO: Make sure form widget is USPhoneNumberField
    phone = models.CharField(max_length=10, null=True, blank=True)

    def save(self, **kwargs):
        if self.user:
            if not self.first_name:
                self.first_name = self.user.first_name
            if not self.last_name:
                self.last_name = self.user.last_name
        super(Donor, self).save(**kwargs)

    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)


class DonationType(models.Model):
    name = models.CharField(
        max_length=100, help_text=_(u"Name of Donation Type")
    )

    def __unicode__(self):
        return self.name


class DonationTypeOption(models.Model):
    donation_type = models.ForeignKey(DonationType, related_name="options")
    amount = models.PositiveIntegerField(help_text=_(u"Amount to donate"))
    length = models.PositiveIntegerField(default=1,
        help_text=_(u"Number of months per repeat "
                u"(1 is one month, 12 is one year)")
    )
    repeat = models.PositiveIntegerField(
        default=0, null=True, blank=True,
        help_text=_(u"Number of times (if any) this donation will repeat")
    )

    @property
    def name(self):
        return self.donation_type.name

    @property
    def is_repeating(self):
        return self.repeat > 0

    def __unicode__(self):
        return "%s (%d)" % (self.donation_type, self.amount)


class PromoCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    amount = models.FloatField(
        help_text=_("Percent discount: 0 is no discount, 100 if free")
    )

    def __unicode__(self):
        return u"%s (%s%%)" % (self.code, self.amount)

    def calculate(self, donation):
        d = donation.amount * Decimal(1 - self.amount / 100.0)
        return Decimal(round(d, 2))


class Donation(models.Model):
    donor = models.ForeignKey(Donor)
    donation_type = models.ForeignKey(DonationTypeOption, null=True,
            blank=True)
    code = models.ForeignKey(PromoCode, null=True, blank=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    attribution = models.CharField(max_length=255, default="")
    anonymous = models.BooleanField()

    def save(self, **kwargs):
        if self.donation_type and not self.amount:
            self.amount = self.donation_type.amount
        if self.code:
            self.amount = self.code.calculate(self)
        return super(Donation, self).save(**kwargs)

    def purchase(self, form):
        from . import backends
        return backends.get_backend().purchase(self, form)

    @property
    def is_repeating(self):
        return self.donation_type and self.donation_type.is_repeating or False

    def __unicode__(self):
        return "%s donated %s" % (self.donor, self.amount)
