from armstrong.utils.backends import GenericBackend
from authorize import aim
from authorize import arb
import datetime
from django.conf import settings as django_settings

from . import forms
from . import signals


class Backend(object):
    """
    Provides a backend that shows the methods required for a valid backend

    Backends must provide the two methods shown in this class in order to be
    able to process incoming donations.
    """

    def get_form_class(self):
        """
        Returns the form class this backend can process

        You *must* implement this method on any backends you create.

        You can use this to provide a custom form for each backend that adds
        behavior specific to that backend.  For example, the
        ``AuthorizeNetBackend`` provides various methods of representing credit
        card information depending on the context.  Using this method, it
        provides a custom ``forms.AuthorizeDonationForm`` that is capable of
        extracting that data.
        """
        raise NotImplementedError

    def purchase(self, donation, form):
        """
        Finalizes the donation by processing the created donation

        You *must* implement this method on any backends you create.

        This takes both a ``Donation`` model instance and an instance of the
        form returned by ``get_form_class``.  It should handle any
        communication with the processing gateway and should mark
        ``donation.processed`` as ``True`` once it's successfully completed.
        """
        raise NotImplementedError

    def send_successful_purchase(self, donation, form, result):
        """
        Called by ``purchase`` after a donation has been succesfully
        processed.

        This function is used to trigger the ``successful_purchase``
        signal while providing a flex point for developers to perform
        an action based on the successful donation prior to the signal
        being sent.
        """
        signals.successful_purchase.send(sender=self, donation=donation,
                form=form, result=result)


class AuthorizeNetBackend(Backend):
    def __init__(self, api_class=None, recurring_api_class=None,
            settings=None, testing=None):
        if api_class is None:
            api_class = aim.Api
        self.api_class = api_class
        if settings is None:
            settings = django_settings
        self.settings = settings
        if recurring_api_class is None:
            recurring_api_class = arb.Api
        self.recurring_api_class = recurring_api_class
        if testing is None:
            testing = getattr(self.settings, "ARMSTRONG_DONATIONS_TESTING",
                    False)
        self.testing = testing

    def get_form_class(self):
        return forms.AuthorizeDonationForm

    def purchase(self, donation, form):
        result = self.onetime_purchase(donation, form)
        if not result["status"]:
            return result
        if donation.is_repeating:
            response = self.recurring_purchase(donation, form)
            result["recurring_response"] = response
        if result["status"]:
            donation.processed = True
            donation.save()
            self.send_successful_purchase(donation, form, result)
        return result

    def get_api(self):
        return self.api_class(self.settings.AUTHORIZE["LOGIN"],
                self.settings.AUTHORIZE["KEY"], delimiter=u"|",
                is_test=self.testing)

    def get_recurring_api(self):
        return self.recurring_api_class(self.settings.AUTHORIZE["LOGIN"],
                self.settings.AUTHORIZE["KEY"], is_test=self.testing)

    def recurring_purchase(self, donation, form):
        today = datetime.date.today()
        start_date = u"%s" % ((today + datetime.timedelta(days=30))
                .strftime("%Y-%m-%d"))
        api = self.get_recurring_api()
        data = form.get_data_for_charge(donation, recurring=True)
        data.update({
            "amount": donation.amount,
            "interval_unit": arb.MONTHS_INTERVAL,
            "interval_length": u"%d" % donation.donation_type.length,
            "bill_first_name": u"%s" % donation.donor.first_name,
            "bill_last_name": u"%s" % donation.donor.last_name,
            "total_occurrences": donation.donation_type.repeat,
            "start_date": start_date,
        })
        if self.testing:
            data["test_request"] = u"TRUE"
        response = api.create_subscription(**data)
        status = response["messages"]["result_code"]["text_"] == u"Ok"
        return {
            "status": status,
        }

    def onetime_purchase(self, donation, form):
        api = self.get_api()
        data = form.get_data_for_charge(donation)
        donor = donation.donor
        if donation.donation_type:
            suffix = ""
            if donation.donation_type.is_repeating:
                repeats = int(donation.donation_type.repeat + 1)
                suffix = " (Repeats %d)" % repeats
            description = u"Membership: %s%s" % (
                    donation.donation_type.name, suffix)
        else:
            description = u"Donation: $%d" % donation.amount
        data.update({
            "amount": donation.amount,
            "description": description,
            "first_name": unicode(donor.first_name),
            "last_name": unicode(donor.last_name),

            # TODO: extract and be conditional
            "address": donor.address.address,
            "city": donor.address.city,
            "state": donor.address.state,
            "zip": donor.address.zipcode,
        })
        if self.testing:
            data["test_request"] = u"TRUE"
        response = api.transaction(**data)
        status = response["reason_code"] == u"1"
        return {
            "status": status,
            "reason": response["reason_text"],
            "response": response,
        }


raw_backend = GenericBackend("ARMSTRONG_DONATIONS_BACKEND", defaults=[
    "armstrong.apps.donations.backends.AuthorizeNetBackend",
])

get_backend = raw_backend.get_backend
