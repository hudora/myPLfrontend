# -*- coding: utf-8 -*-
"""
Forms for myplfrontend.

Created by Johan Otten on 2009-10-30 for HUDORA.
Copyright (c) 2009 HUDORA. All rights reserved.
"""

from django import forms


class palletheightForm(forms.Form):
    """Form for settings the pallet height with a maximum and minimum value."""
    height = forms.IntegerField(min_value=900, max_value=2100)
