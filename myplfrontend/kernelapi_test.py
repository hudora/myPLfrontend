#!/usr/bin/env python
# encoding: utf-8

"""
kernelapi_test.py

Performs simple working tests for the get() functions of the kernelapi module
"""

import myplfrontend.kernelapi

artnr = myplfrontend.kernelapi.get_article_list()[0]
myplfrontend.kernelapi.get_article_list()
myplfrontend.kernelapi.get_article(artnr)
myplfrontend.kernelapi.get_article_audit(artnr)

movementid = myplfrontend.kernelapi.get_movements_list()[0]
myplfrontend.kernelapi.get_movements_list()
if movementid:
    myplfrontend.kernelapi.get_movement(movementid)

pickid = myplfrontend.kernelapi.get_picks_list()[0]
myplfrontend.kernelapi.get_picks_list()
if pickid:
    myplfrontend.kernelapi.get_pick(pickid)

kommiauftragnr = myplfrontend.kernelapi.get_kommiauftrag_list()[0]
myplfrontend.kernelapi.get_kommiauftrag_list()
if kommiauftragnr:
    myplfrontend.kernelapi.get_kommiauftrag(kommiauftragnr)

kommischeinnr = myplfrontend.kernelapi.get_kommischein_list()[0]
myplfrontend.kernelapi.get_kommischein_list()
if kommischeinnr:
    myplfrontend.kernelapi.get_kommischein(kommischeinnr)

mui = myplfrontend.kernelapi.get_units_list()[0]
myplfrontend.kernelapi.get_units_list()
if mui:
    myplfrontend.kernelapi.get_unit(mui)

location = myplfrontend.kernelapi.get_location_list()[0]
myplfrontend.kernelapi.get_location_list()
if location:
    myplfrontend.kernelapi.get_location(location)

myplfrontend.kernelapi.get_statistics()
