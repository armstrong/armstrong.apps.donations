from django.conf.urls.defaults import patterns, url
from . import views

urlpatterns = patterns('',
    url(r"^/?$", views.DonationFormView.as_view(), name="donations_form"),
)
