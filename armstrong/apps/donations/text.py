from django.utils.translation import ugettext as _

default_labels = {
    "donation.label.anonymous": "Keep my donation anonymous",
}


def get(key):
    """

    .. todo:: Make the dictionary configurable
    """
    if key in default_labels:
        return _(default_labels[key])
    return ""
