"""

.. todo:: Fix issue if this were to stay in memory across a new year
"""
import datetime
now = datetime.datetime.now()

MONTHS = ["%02d" % (i + 1) for i in range(12)]
MONTH_CHOICES = zip(MONTHS, MONTHS)

YEARS = range(now.year, now.year + 10)
YEAR_CHOICES = zip(YEARS, YEARS)
