#!/usr/bin/env python
# encoding: utf-8
"""
tools.py

Created by Lars Ronge on 2008-03-18.
Copyright (c) 2008 HUDORA Gmbh. All rights reserved.
"""

import sys, os
from mypl.models import Movement
from mypl.kernel import Kerneladapter


def get_provisiongdata_for_kb(kommissionierbelegnr):
    """Returns the Provisioning-Data from kernelE for a KB-No. The returned data could be used to create
    Provisioning-Objects in Django."""
    ret = []
    k = Kerneladapter()
    pipeline_info = k.provpipeline_info(kommissionierbelegnr)
    for provlist in pipeline_info[0]['provisioninglists']:
        data = []
        prov_info = k.provisioninglist_info(provlist)
        data.append(provlist)
        data.append(kommissionierbelegnr)
        data.append(prov_info['destination'])
        data.append(prov_info['parts'])
        data.append(prov_info['attributes'])
        data.append([])
        for pickid in prov_info['provisioning_ids']:
            if pickid[0] == 'P':
                pick_info = k.pick_info(pickid)
                data[5].append([pickid, pick_info['from_unit'], pick_info['from_location'], 
                                pick_info['quantity'], pick_info['product']])
            else: 
                pick_info = k.movement_info(pickid)
                data[5].append([pickid, pick_info['mui'], pick_info['from_location'], 
                                pick_info['quantity'], pick_info['product']])
        ret.append(data)
        
    return ret


def get_products_to_ship_today():
    """
    Create a dictionary with article numbers as keys and quantities as values
    of products that have to be shipped today
    (taken from pending orders in provpipeline)
    """

    products = {}
    kernel = Kerneladapter()
    for kommi in kernel.provpipeline_list_new():
        if kommi['shouldprocess'] == 'yes':
            for orderline in kommi['orderlines']:
                artnr = orderline['product']
                products[artnr] = products.get(artnr, 0) + orderline['quantity']
    return products


def get_products_in_provpipeline_list_new():
    """Returns a list of all products pending in provpipeline
    """
    k = Kerneladapter()
    pipeline = k.provpipeline_list_new()
    products = {}
    for kb in pipeline:
        for orderline in kb['orderlines']:
            products[orderline['product']] = products.get(orderline['product'], 0) + 1

    return products


def get_ls_positions(date_to=None):
    """Returns the number of delivery-note-positions in kernele, that is new in the processing pipeline.
       When a date is given as parameter, all positions to deliver before and on that date are returned.
    """
    k = Kerneladapter()
    pipeline = k.provpipeline_list_new()
    ls_positions = 0
    for kb in pipeline:
        if not date_to or kb['versandtermin'] <= date_to:
            ls_positions += len(kb['orderlines'])
    return ls_positions
    

def get_kbs_for_articles_in_pipeline(artnr):
    """Returns the KB-Numbers and the quantities (as a tupel) of the KBs in the Provisioning-Pipeline 
       that contain the given article-number
    """
    k = Kerneladapter()
    pipeline = k.provpipeline_list_new()
    kbs = []
    for kb in pipeline:
        for orderline in kb['orderlines']:
            if orderline['product'] == artnr:
                kbs.append((kb['id'], orderline['quantity']))
    return kbs

# TODO: remove I'm not sute what this gains
def print_movements(movementlist, printer="DruckerAllmanFach2"):
    """Print out the requested movements"""
    if movementlist:
        for movement_id in movementlist:
            movement = Movement(movement_id)
            movement.output_on_printer(printer=printer)
            print "%s: %s -> %s" % (movement_id, movement.location_from, movement.location_to)
        return True
    else:
        return False
