from .. urls import *

urlpatterns += patterns('',
    url(r"^require_confirm/?$", views.DonationFormView.as_view(confirm=True),
            name="donations_form_confirm"),
)
