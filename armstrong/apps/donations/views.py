from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from . import backends


class LandingView(TemplateView):
    template_name = "armstrong/donations/landing.html"


class ThanksView(TemplateView):
    template_name = "armstrong/donations/thanks.html"


class DonationFormView(TemplateView):
    template_name = "armstrong/donations/donation.html"

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

    _success_url = None

    @property
    def success_url(self):
        if not self._success_url:
            self._success_url = reverse("donations_thanks")
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

    def get_donation_form_kwargs(self):
        kwargs = {"initial": getattr(self, "donation_form_initial", None)}
        return self.add_data_if_write_request(kwargs)

    def get_donation_form_class(self):
        return backends.get_backend().get_form_class()

    def get_donation_form(self):
        donation_form_class = self.get_donation_form_class()
        return donation_form_class(**self.get_donation_form_kwargs())

    def get_context_data(self, **kwargs):
        donation_form = self.get_donation_form()
        context = {
            "form_action_url": self.form_action_url,
            "donor_form": donation_form.donor_form,
            "donation_form": donation_form,
            "address_formset": donation_form.address_formset,
        }
        context.update(kwargs)
        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        donation_form = self.get_donation_form()
        if not donation_form.is_valid():
            return self.forms_are_invalid()
        donation = donation_form.save()
        return self.forms_are_valid(donation=donation,
                donation_form=donation_form)

    def forms_are_invalid(self, **kwargs):
        return self.render_to_response(self.get_context_data())

    def forms_are_valid(self, donation, donation_form, **kwargs):
        response = backends.get_backend().purchase(donation, donation_form)
        if not response["status"]:
            return self.purchase_failed(response)
        return HttpResponseRedirect(self.success_url)

    def purchase_failed(self, backend_response):
        context = {
            "error_msg": "Unable to process payment",
            "reason": backend_response["reason"],
            "response": backend_response["response"],
        }
        context.update(self.get_context_data())
        return self.render_to_response(context)
