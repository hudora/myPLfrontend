# encoding: utf-8
"""
decorators.py - Decorators for stapler

Created by Christian Klein on 2010-03-26.
Copyright (c) 2010 HUDORA GmbH. All rights reserved.
"""

from django.http import HttpResponse

def login_required(viewfunc):
    """Login-Decorator"""
    def decorator(request, *args, **kwargs):
        if request.user.is_authenticated():
            return viewfunc(request, *args, **kwargs)
        else:
            return HttpResponse("Not logged in", status=403)
    return decorator
