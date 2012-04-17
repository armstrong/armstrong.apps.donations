armstrong.apps.donations
=========================
This package provides the base pieces required to accept donations on an
Armstrong site.

``armstrong.apps.donations`` provides everything you need to accept donations
except templates.  It defaults to Authorize.net for its payment processing, but
all payment processing can be configured.


Usage
-----
``armstrong.apps.donations`` ships with a default set of URL routes that may
work for you without any tweaking.  Simply add the URL configuration you would
like and include ``armstrong.apps.donations.urls``.  For example, you could
configure it to respond to ``/donate/`` like this inside your main ``urls``
module.

::

    # This assumes you already have a urlpatterns variable
    urlpatterns += patterns('',
        url(r'^/donate/', include('armstrong.apps.donations.urls')),
    )

This adds a ``DonationFormView`` view for you at ``/donate/`` and a thanks page
via ``ThanksView`` at ``/donate/thanks/``.  You need to add templates for each.
The default templates are:

* ``armstrong/donations/donation.html``
* ``armstrong/donations/thanks.html``

You need to use the ``donation_form`` context value to display the
``DonationForm`` inside the ``DonationFormView``.


Installation & Configuration
----------------------------
You can install the latest release of ``armstrong.apps.donations`` using `pip`_:

::

    pip install armstrong.apps.donations

Make sure to add ``armstrong.apps.donations`` and ``armstrong.apps.content`` to
your ``INSTALLED_APPS``.  You can add this however you like.  This works as a
copy-and-paste solution:

::

	INSTALLED_APPS += ["armstrong.apps.donations", ]

Once installed, you have to run either ``syncdb``, or ``migrate`` if you are
using `South`_.

You can configure the payment backend using the ``ARMSTRONG_DONATIONS_BACKEND``
setting.  It defaults to:

::

    ARMSTRONG_DONATIONS_BACKEND = "armstrong.apps.donations.backends.AuthorizeNetBackend"

This utilizes `armstrong.utils.backends`_ for its backend processing.

.. _pip: http://www.pip-installer.org/
.. _South: http://south.aeracode.org/
.. _armstrong.utils.backends: https://github.com/armstrong/armstrong.utils.backends

State of Project
----------------
Armstrong is an open-source news platform that is freely available to any
organization.  It is the result of a collaboration between the `Texas Tribune`_
and `Bay Citizen`_, and a grant from the `John S. and James L. Knight
Foundation`_.

To follow development, be sure to join the `Google Group`_.

``armstrong.apps.donations`` is part of the `Armstrong`_ project.  You're
probably looking for that.


.. _Armstrong: http://www.armstrongcms.org/
.. _Bay Citizen: http://www.baycitizen.org/
.. _John S. and James L. Knight Foundation: http://www.knightfoundation.org/
.. _Texas Tribune: http://www.texastribune.org/
.. _Google Group: http://groups.google.com/group/armstrongcms
