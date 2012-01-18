from cbv_utils.views import (InlineFormsetMixin, ProcessInlineFormsetView)
from django.views.generic import TemplateView
from django.views.generic.detail import (
        SingleObjectTemplateResponseMixin)

from . import forms


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
    template_name = "donations/landing.html"


class DonationFormView(InlineCreateView):
    form_class = forms.DonorForm
    inline_formset_class = forms.DonationInlineFormset
    template_name = "donations/donation.html"
