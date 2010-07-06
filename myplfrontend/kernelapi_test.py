#!/usr/bin/env python
# encoding: utf-8

"""
kernelapi_test.py

Performs simple working tests for the get() functions of the kernelapi module
"""

from myplfrontend.kernelapi import Kerneladapter

artnr = Kerneladapter().get_article_list()[0]
Kerneladapter().get_article_list()
Kerneladapter().get_article(artnr)
Kerneladapter().get_article_audit(artnr)

movementid = Kerneladapter().get_movements_list()[0]
Kerneladapter().get_movements_list()
if movementid:
    Kerneladapter().get_movement(movementid)

pickid = Kerneladapter().get_picks_list()[0]
Kerneladapter().get_picks_list()
if pickid:
    Kerneladapter().get_pick(pickid)

kommiauftragnr = Kerneladapter().get_kommiauftrag_list()[0]
Kerneladapter().get_kommiauftrag_list()
if kommiauftragnr:
    Kerneladapter().get_kommiauftrag(kommiauftragnr)

kommischeinnr = Kerneladapter().get_kommischein_list()[0]
Kerneladapter().get_kommischein_list()
if kommischeinnr:
    Kerneladapter().get_kommischein(kommischeinnr)

mui = Kerneladapter().get_units_list()[0]
Kerneladapter().get_units_list()
if mui:
    Kerneladapter().get_unit_info(mui)

location = Kerneladapter().get_location_list()[0]
Kerneladapter().get_location_list()
if location:
    Kerneladapter().get_location(location)

Kerneladapter().get_statistics()
