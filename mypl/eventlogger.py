# -*- coding: utf-8 -*-

"""
Logger system for mypl based on Jens Ohlig's code.

Created on 2008-11-11 by Christian Klein.
Kölle Alaaf!
"""

from mypl.models import Event
import warnings


def log(identifier, **kwargs):
    """Log an event."""

    try:
        logentry = Event.objects.get(action_id=identifier)
    except Event.MultipleObjectsReturned:
        warnings.warn('Multiple Events for %s' % identifier)
        logentry = Event.objects.filter(action_id=identifier).latest()
    except Event.DoesNotExist:
        logentry = Event(action_id=identifier)

    for attr, value in kwargs.items():
        setattr(logentry, attr, value)
    logentry.save()
