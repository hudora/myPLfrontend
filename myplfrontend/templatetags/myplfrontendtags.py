#!/usr/bin/env python
# encoding: utf-8

"""Template tags for use in myplfrontend."""

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
import myplfrontend.kernelapi

register = template.Library()


def link_location(locname):
    """Returns a XHTML snippet which links to a location name"""
    return mark_safe(('<a href="/myplfrontend/plaetze/%s/">' +
             '%s</a>') % (escape(locname), escape(locname)))
register.filter(link_location)


def link_product(name):
    """Returns a XHTML snippet which links to an product name"""
    if ' ' in name:
        # assue it' in Name (ArtNr) Format
        artnr = name.split()[-1]
        artnr = artnr.strip('(').strip(')')
    else:
        artnr = name
    return mark_safe(('<a href="/myplfrontend/produkte/%s/">' +
             '%s</a>') % (escape(artnr), escape(name)))
register.filter(link_product)


def link_mui(name):
    """Returns a XHTML snippet which links to an mui/NVE"""
    return mark_safe(('<a href="/myplfrontend/unit/%s/">' +
             '%s</a>') % (escape(name), escape(name)))
register.filter(link_mui)


def link_kommiauftrag(name):
    """Returns a XHTML snippet which links to a kommiauftrag."""
    return mark_safe(('<a href="/myplfrontend/kommiauftrag/%s/">' +
                 '%s</a>') % (escape(name), escape(name)))
register.filter(link_kommiauftrag)


def link_kommischein(name):
    """Returns a XHTML snippet which links to a kommischein."""
    return name
    #return mark_safe(('<a href="/myplfrontend/kommischein/%s/">' +
    #             '%s</a>') % (escape(name), escape(name)))
register.filter(link_kommischein)


def link_number(name):
    """Returns a XHTML snippet which links to an myPL id number.
    
    Is smart enough to destinguish between movements/picks/etc."""
    
    if name.startswith('m'):
        base = '/myplfrontend/movements/'
    elif name.startswith('P'):
        base = '/myplfrontend/picks/'
    else:
        return name
    # add p00058594 - picklistlist
    # r00054753 - retrievallist
    return mark_safe(('<a href="%s%s/">%s</a>') % (escape(base), escape(name), escape(name)))
register.filter(link_number)


def fix_timestamp(value):
    """Return a datatime object."""
    return myplfrontend.kernelapi.fix_timestamp(value)
register.filter(fix_timestamp)
