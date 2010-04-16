#!/usr/bin/env python
# encoding: utf-8
"""
models.py

Created by Christian Klein on 2010-04-16.
Copyright (c) 2010 HUDORA GmbH. All rights reserved.
"""

from django.db import models


class MyPLModel(models.Model):
    class Meta:
        permissions = (("can_view_provpipeline", "Can view Provisioning Pipeline"),
                       ("can_initiate_provisioning", "Can initiate Provisioning"),
                       ("can_cancel_movement", "Can cancel a Movement"),
                       ("can_push_provisioning", "Can push Provisioning"),
                       ("can_change_priority", "Can change Provisioning priority"),
                       ("can_zeroise_provisioning", "Can zeroise a Provisioning"),
                      )
