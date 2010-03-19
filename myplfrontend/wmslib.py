#!/usr/bin/env python
# encoding: utf-8
""" wmslib.py --- Funktionen rund um das Warehouse Management System
"""

# filename
# Created by Christian Klein and Christoph Borgolte on 04-02-2010 for HUDORA.
# Copyright (c) 2010 HUDORA. All rights reserved.


import logging
logging.basicConfig(level=logging.WARNING)

import husoftm.lieferscheine
import cs.messaging as messaging


def kommibeleg_zurueckmelden(kommiauftragnr, zielqueue='erp.cs-wms.rueckmeldung#normal', audit_trail='', nullen=False):
    """Meldet einen Kommibeleg per Messaging zurück."""

    chan = messaging.setup_queue(zielqueue, durable=True)
    doc = messaging.empty_message('wmslib.rueckmelden/',
                                  guid='mypl.kommiauftragsrueckmeldung-%s' % kommiauftragnr,
                                  audit_trail=audit_trail,
                                  audit_info='an SoftM zurueckgemeldet')
    doc['kommiauftragnr'] = kommiauftragnr
    doc['positionen'] = []
    kommibeleg = husoftm.lieferscheine.Kommibeleg(kommiauftragnr)
    for pos in kommibeleg.positionen:
        menge = int(pos.menge_komissionierbeleg)
        if nullen:
            menge = 0
        doc['positionen'].append({'posnr': pos.auftrags_position,
                                  'kommissionierbeleg_position': pos.kommissionierbeleg_position,
                                  'auftrags_position': pos.auftrags_position,
                                  'menge': menge,
                                  'artnr': pos.artnr})
    messaging.publish(doc, zielqueue)
