from django.dispatch import Signal

successful_purchase = Signal(providing_args=["donation", "form", "result"])
