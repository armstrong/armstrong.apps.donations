from cbv_utils.views import (InlineFormsetMixin, ProcessInlineFormsetView)
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.views.generic.detail import (
        SingleObjectTemplateResponseMixin)

from . import forms
from . import models


class BaseInlineCreateView(InlineFormsetMixin, ProcessInlineFormsetView):
    def get(self, request, *args, **kwargs):
        self.object = None
        return super(BaseInlineCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        return super(BaseInlineCreateView, self).post(request, *args, **kwargs)


class InlineCreateView(SingleObjectTemplateResponseMixin,
        BaseInlineCreateView):
    pass


class LandingView(TemplateView):
    template_name = "armstrong/donations/landing.html"


class DonationFormView(TemplateView):
    template_name = "armstrong/donations/donation.html"
    donor_form_initial = {}

    @property
    def is_write_request(self):
        return self.request.method in ("POST", "PUT")

    _form_action_url = ""

    @property
    def form_action_url(self):
        return self._form_action_url

    @form_action_url.setter
    def set_form_action_url(self, name):
        self._form_action_url = reverse(name)


    _success_url = ""

    @property
    def success_url(self):
        return self._success_url

    @success_url.setter
    def set_success_url(self, name):
        self._success_url = reverse(name)

    def add_data_if_write_request(self, kwargs):
        if self.is_write_request:
            kwargs.update({
                "data": self.request.POST,
                "files": self.request.FILES,
            })
        return kwargs

    def get_form_kwargs(self, key):
        kwargs = {"initial": getattr(self, "%s_form_initial" % key)}
        return self.add_data_if_write_request(kwargs)

    def get_formset_kwargs(self, key):
        # TODO: make initial work
        kwargs = {"initial": []}
        return self.add_data_if_write_request(kwargs)

    def get_donor_form(self):
        # return forms.DonorForm(**self.get_form_kwargs("donor"))
        return ""

    def get_donation_form(self):
        # return forms.DonationForm(**self.get_form_kwargs("donation"))
        return ""

    def get_address_formset(self):
        # return forms.AddressFormset(**self.get_formset_kwargs("address"))
        return ""

    def get_context_data(self, **kwargs):
        context = {
            "form_action_url": self.form_action_url,
            "donor_form": self.get_donor_form(),
            "donation_form": self.get_donation_form(),
            "address_formset": self.get_address_formset(),
        }
        context.update(kwargs)
        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        donor = models.Donor.objects.create(name=request.POST["name"])
        address_formset = forms.DonorMailingAddressFormset(data=request.POST)
        addresses = address_formset.save()
        if len(addresses):
            donor.address = addresses[0]
            donor.save()
        return HttpResponse("")
