#!/usr/bin/env python
# encoding: utf-8
"""
mypl.py

Created by Christoph Borgolte and Christian Klein on 2010-04-13.
Copyright (c) 2010 HUDORA GmbH. All rights reserved.
"""


from django.shortcuts import render_to_response
from django.template import RequestContext
from myplfrontend.kernelapi import Kerneladapter
from cs.messaging import simple_message
from hudjango import PrinterChooser


# MOVE TO UTIL ODER WO AUCH IMMER...
def commit_to_softm(kommischein, commit_type='normal'):
    """Rückmeldung in SoftM anstossen"""
    
    kerneladapter = Kerneladapter()
    zielqueue = 'erp.cs-wms.rueckmeldung#%s' % commit_type
    doc = {'guid': 'mypl.kommiauftragsrueckmeldung-%s' % kommischein['id'],
           'audit_info': 'an SoftM zurueckgemeldet',
           'kommiauftragnr': kommischein['id'],
           'positionen': [],
          }
    
    for posnr, provisioning_id in enumerate(kommischein['provisionings']):
        provisioning = kerneladapter.get_pick(provisioning_id)
        doc['positionen'].append({
                'posnr': posnr,
                'menge': provisioning['menge'],
                'artnr': provisioning['artnr']})
    simple_message(doc, zielqueue, 'mypl')


def zurueckmelden(request):
    """Zurückmelden der verschiedenen Belegarten."""

    if request.method == "POST":
        
        kerneladapter = Kerneladapter()
        
        belegnr = request.POST.get('belegnr', '').strip().lower()
        
        if belegnr.startswith('mr'):
            # Manipulationsversuch: jemand versucht Teile eines Retrivals einzeln zurückzumelden
            zwitscher('%s versucht "%s" manipulativ zurueckzumelden' % (request.META['REMOTE_ADDR'], belegnr),
                      username='mypl')
            raise ValueError('Versuch "%s" zu manipulieren' % belegnr)
        
        if belegnr.startswith('m'):
            # It's a movement, commit directly to kernelE
            response = kerneladapter.commit_movement(belegnr)
        
        elif belegnr.startswith('r') or belegnr.startswith('p'):
            # It's a picklist or a retrievallist, commit as demanded to SoftM
            # kernelE commit:
            response = kerneladapter.commit_provisioning(belegnr)
            
            # SoftM commit:
            kommischein = kerneladapter.get_kommischein(belegnr)
            # TODO: Test auf None...
            commit_to_softm(kommischein)
            
        else:
            response = u"ungültige oder unbekannte Belegnummer"
        
        # Benutzer informieren
        # request.user.message_set.create(msg=response)
        
    return render_to_response('mypl/beleg_zurueckmelden.html',
                              context_instance=RequestContext(request))


def holen(request):
    """
    Generate a movement/provisioning.

    This function comes in two flavours, handling both beleg_holen.html and beleg_holen_manuell.html
    Pay attention to the key/value pairs in the request: a value for the key "type_and_worker" means
    that the template for getting a provisioning was requested with a barcode card.
    Else, "pick" or "retrieval" was requested manually.
    """

    kerneladapter = Kerneladapter()
    printer = PrinterChooser(request, ("DruckerAllman", "DruckerLerdorf", "DruckerDraper"))

    if request.method == "POST":
        provisioningtype = request.POST.get('provisioningtype', '')
        if request.POST.get('type_and_worker'):
            provisioningtype = request.POST.get('type_and_worker').split(' ')[0]
        provisioningtype = provisioningtype.lower()

        if provisioningtype == 'pick':
            # get picklist
            pass
            # response = kerneladapter.get_whatever()
            
        elif provisioningtype == 'retrieval':
            # Statistically, in 70% of all cases we want to handle movements first
            # (and then retrievals, if there are no movements)
            response = kerneladapter.get_next_job(probability=0.7) # todo: kwargs...
    
    #if response:
    # inform_user()
    #else:
    # inform_user("gibt nix")
        
    # XXX: DRUCKEN!!!
    
    if 'manuell' in request.path:
        template = 'mypl/beleg_holen_manuell.html'
    else:
        template = 'mypl/beleg_holen.html'
    
    ctx = {}
    return render_to_response(template, printer.update_context(ctx),
                              context_instance=RequestContext(request))
