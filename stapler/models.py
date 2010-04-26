# encoding: utf-8
"""
models.py

Created by Axel Schlueter and Christian Klein on 2010-03-26.
Copyright (c) 2010 HUDORA GmbH. All rights reserved.
"""

import datetime
from django.db import models
from django.contrib.auth.models import User
try:
    import json
except ImportError:
    import simplejson as json

from myplfrontend.tools import format_locname


STAPLERJOB_STATUS = (
    ('open', 'offen'),
    ('closed', 'abgeschlossen'),
    ('canceled', 'storniert'),
)


import sys

def make_job(user, movement):
    """ Erzeuge Staplerjob für Movement aus dem myPL kernelE. """
    if not movement:
        return None
    for key in ['from_location', 'to_location']:
        movement[key] = format_locname(movement[key])
    job = Staplerjob.objects.create(user=user, movement_id=movement['oid'],
                                    serialized_movement=json.dumps(movement, indent=2),
                                    status="open",
                                    created_at=datetime.datetime.now())
    return job


class Staplerjob(models.Model):
    """Represents a stored Movement for Stapler."""
    
    movement_id = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=STAPLERJOB_STATUS, default="open")
    user = models.ForeignKey(User)
    serialized_movement = models.TextField()
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField() #auto_now_add=True) - Häh?
    
    def __unicode__(self):
        return u'ID: %s, User: %s, Movement ID: %s' % (self.id, self.user, self.movement_id)
    
    @property
    def deserialized(self):
        if not hasattr(self, '_deserialized'):
            self._deserialized = json.loads(self.serialized_movement)
        return self._deserialized
    
    def __unicode__(self):
        try:
            return "%(oid)s: %(artnr)s von %(from_location)s nach %(to_location)s" % self.deserialized
        except KeyError:
            return unicode(self.movement_id)
    
    def from_location(self):
        return self.deserialized.get('from_location')
    
    def to_location(self):
        return self.deserialized.get('to_location')
    
    class Meta:
        get_latest_by = "created_at"
        ordering = ["-created_at"]
        verbose_name = "Staplerjob"
        verbose_name_plural = "Staplerjobs"
