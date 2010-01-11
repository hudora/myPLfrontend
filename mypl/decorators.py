#!/usr/bin/env python
# encoding: utf-8
"""
mypl/decorators.py

Custom decorators for mypl

Created by Christian Klein on 2009-04-20.
Copyright (c) 2009 HUDORA GmbH. All rights reserved.
"""

from django.conf import settings
from mypl.models import MyPLConfig

try:
    from functools import update_wrapper
except ImportError:
    from django.utils.functional import update_wrapper


def SETTINGS_check_if_enabled(feature=None, response=None):
    """Decorator that checks if given myPL function is enabled.

    Add the following lines to your settings.py:
    MYPL_FUNCTIONS = {
        'zurueckmelden': True,
        'picklist_holen': True,
        'movement_holen': True,
        'retrieval_holen': True,
        'stapler_holen': True
    }

    TODO: use
    """

    def test_func(feature):
        if not hasattr(settings.MYPL_FUNCTIONS):
            return True
        return settings.MYPL_FUNCTIONS.get(feature, True)

    def decorate(func):
        return _CheckFeature(func, test_func, feature, response)
    return decorate


def MODEL_check_if_enabled(feature=None, response=None):
    """Decorator that checks if given myPL function is enabled.

    The configuration is driven by the Django model  'MyPLConfiguration'.
    Use the Django admin interface.
    """

    def test_func(feature):
        try:
            obj = MyPLConfig.objects.get(feature=feature)
        except MyPLConfig.DoesNotExist:
            return True
        return obj.enabled

    def decorate(func):
        return _CheckFeature(func, test_func, feature, response)

    return decorate


class _CheckFeature(object):
    def __init__(self, func, test_func, feature, response=None):
        self.func = func
        self.feature = feature
        self.test_func = test_func
        self.response = response

        # See django/contrib/auth/decorators.py
        update_wrapper(self, func, updated=())
        for k in func.__dict__:
            if k not in self.__dict__:
                self.__dict__[k] = func.__dict__[k]

    def __get__(self, obj, cls=None):
        func = self.func.__get__(obj, cls)
        return _CheckFeature(func, feature)

    def __call__(self, *args, **kwargs):

        passed = self.test_func(self.feature)

        if passed:
            return self.func(*args, **kwargs)
        elif callable(self.response):
            return self.response(*args, **kwargs)
        else:
            return self.response