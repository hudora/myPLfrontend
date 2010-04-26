#!/usr/bin/env python
# encoding: utf-8
"""
views.py - views for myPL

Copyright (c) 2007-2010 HUDORA GmbH. All rights reserved.
"""

import random
import datetime

from django.template import RequestContext
from django.contrib.auth.decorators import user_passes_test, permission_required, login_required
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import render_to_response, get_object_or_404
from django.utils import simplejson as json

from mypl.models import Provisioning, Movement, Staplerjob
from mypl.kernel import Kerneladapter, KernelError
from mypl import eventlogger

from cs.zwitscher import zwitscher


def zurueckmelden(request):
    """Zurückmelden der verschiedenen Belegarten."""

    anzeige = {}

    if request.method == "POST":
        belegnr = request.POST.get('belegnr', '').strip().lower()
        
        if belegnr.startswith('mr'):
            # Manipulationsversuch: jemand versucht Teile eines Retrivals einzeln zurückzumelden
            zwitscher('%s versucht "%s" manipulativ zurueckzumelden' % (request.META['REMOTE_ADDR'], belegnr),
                      username='mypl')
            raise ValueError('Versuch "%s" zu manipulieren' % belegnr)
        
        if belegnr.startswith('m'):
            # It's a movement, commit directly to kernelE
            Kerneladapter().commit_movement(belegnr)
            eventlogger.log(belegnr, confirmed_at=datetime.datetime.now())
        
        elif belegnr.startswith('r') or belegnr.startswith('p'):
            # It's a picklist or a retrievallist, commit as demanded to SoftM
            timestamp = datetime.datetime.now()
            provisioning = Provisioning.objects.get(mypl_id=belegnr)
            provisioning.confirmed_at = timestamp
            provisioning.save()
            provisioning.confirm_as_demanded()
            eventlogger.log(belegnr, confirmed_at=timestamp)

        else:
            anzeige = {'class': u"warning",
                       'headline': u"Belegnummer fehlt oder ist ungültig.",
                       'paragraph': u"Bitte geben Sie eine gültige Belegnummer ein."}

        if not anzeige.get('class') == u"warning":
            anzeige = {'class': u"acknowledgement",
                       'headline': u"Alles klar.",
                       'paragraph': u'Beleg #%s wurde zurückgemeldet!' % (belegnr)}
    
    return render_to_response('mypl/beleg_zurueckmelden.html',
                              {'anzeige': anzeige},
                              context_instance=RequestContext(request))


def _get_picklist(request):
    """Get a picklist

    This function gets a picklist and prints it on either the requested printer
    or the default printer.

    It returns the number of processed picklists or
    0 if the kernel adapter did not return any picklist.

    """

    # type_and_worker is a string like "pick klein"
    # remove the provisioning type from type_and_worker
    provisioning_user = " ".join(request.POST.get('type_and_worker', '').split(" ")[1:]).upper()
    
    kernel = Kerneladapter()
    # Return 0 if kernelE reported timeout
    # which is very likely due to no picklist being available at the moment
    try:
        picklists = kernel.get_picklists()
    except KernelError, error:
        if not "timeout" in error.report:
            zwitscher('KernelError: %s' % error.report, username='mypl')
            return 0
        raise

    for picklist in picklists:
        provisioning = Provisioning()
        provisioning.create_from_kernel(picklist)

        picklist_id = picklist[0]

        provisioning.printed_by = provisioning_user
        provisioning.save()

        if request.POST.get('printer'):
            provisioning.output_on_printer(printer=request.POST.get('printer'))
        else:
            provisioning.output_on_printer()

        eventlogger.log(picklist_id, action_type="pick", handled_by=provisioning_user,
                        positions=provisioning.provisioningposition_set.count())

    return len(picklists)


def _get_movementlist(request):
    """
    Get a movementlist

    This function gets a movementlist and prints it on either the requested printer
    or the default printer.

    It returns the number of processed movementlists or
    0 if the kernel adapter did not return any movementlist.
    """

    # type_and_worker is a string like "R Christian Klein"
    # remove the provisioning type from type_and_worker
    provisioning_user = " ".join(request.POST.get('type_and_worker', '').split(" ")[1:]).upper()

    kernel = Kerneladapter()
    try:
        movementlist = kernel.get_movementlist()
    except KernelError, error:
        if not "timeout" in error.report:
            zwitscher('KernelError: %s' % error.report, username='mypl')
            return 0
        raise

    for movement_id in movementlist:
        # Gather movement Information from kernel
        movement = Movement(movement_id)

        if request.POST.get('printer'):
            movement.output_on_printer(printer=request.POST.get('printer'))
        else:
            movement.output_on_printer()

        eventlogger.log(movement_id, action_type="movement", positions=1, handled_by=provisioning_user)

    return len(movementlist)


def _get_retrievallist(request):
    """
    Get a retrievallist

    This function gets a retrievallist and prints it on either the requested printer
    or the default printer.

    It returns 1 (or the number of processed retrievallists) or
    0 if the kernel adapter did not return any retrievallist.
    """

    # type_and_worker is a string like "R Christian Klein"
    # remove the provisioning type from type_and_worker
    provisioning_user = ' '.join(request.POST.get('type_and_worker', '').split(' ')[1:]).upper()

    kernel = Kerneladapter()
    try:
        retrievallists = kernel.get_retrievallists()
    except KernelError, error:
        if not "timeout" in error.report:
            zwitscher('KernelError: %s' % error.report, username='mypl')
            return 0
        raise

    for retrievallist in retrievallists:
        provisioning = Provisioning()
        provisioning.create_from_kernel(retrievallist)

        provisioning.printed_by = provisioning_user
        provisioning.save()

        if request.POST.get('printer'):
            provisioning.output_on_printer(printer=request.POST.get('printer'))
        else:
            provisioning.output_on_printer()
        # also output retrievalstickers
        provisioning.output_stickers_on_printer()
        eventlogger.log(retrievallist[0], action_type="retrieval", positions=1, handled_by=provisioning_user)

    return len(retrievallists)


def holen(request):
    """
    Generate a movement/provisioning.

    This function comes in two flavours, handling both beleg_holen.html and beleg_holen_manuell.html
    Pay attention to the key/value pairs in the request: a value for the key "type_and_worker" means
    that the template for getting a provisioning was requested with a barcode card. Else, "pick" or
    "retrieval" was requested manually.
    """
    anzeige = {}
    printers = request.session.get('printer', {})

    # TODO Make use of PrinterChooser here
    if not "DruckerDraper" in printers:
        # Default values for printers
        printers = {"DruckerAllman": "selected", "DruckerLerdorf": "unselected",
                    "DruckerDraper": "unselected"}
        request.session['printer'] = printers

    if request.method == "POST":

        if request.POST.get('printer'):
            for key in request.session['printer']:
                request.session['printer'][key] = 'unselected'
            request.session['printer'][request.POST.get('printer')] = 'selected'

        provisioningtype = request.POST.get('provisioningtype', '')
        if request.POST.get('type_and_worker'):
            provisioningtype = request.POST.get('type_and_worker').split(' ')[0]
        provisioningtype = provisioningtype.lower()

        if provisioningtype == 'pick':
            if _get_picklist(request) == 0:
                anzeige = {'class': u"warning",
                           'headline': u"Keine Daten verfügbar",
                           'paragraph': u"Bitte versuchen Sie es später noch einmal."}
            else:
                anzeige = {'class': u"acknowledgement",
                           'headline': u"Alles klar.",
                           'paragraph': u"Kommissionierbeleg wird gedruckt."}

        elif provisioningtype == 'retrieval':
            # Statistically, in 70% of all cases we want to handle movements first
            # (and then retrievals, if there are no movements)
            # We want it the other way round in the other cases
            if random.random() < 0.70:
                first, second = _get_movementlist, _get_retrievallist
            else:
                first, second = _get_retrievallist, _get_movementlist

            # if first() returns 0, the argument is determined by second()
            # otherwise, second() will not be called
            if not(first(request) or second(request)):
                anzeige = {'class': u"warning",
                           'headline': u"Keine Daten verfügbar",
                           'paragraph': u"Bitte versuchen Sie es später noch einmal."}
            else:
                anzeige = {'class': u"acknowledgement",
                           'headline': u"Alles klar.",
                           'paragraph': u"Beleg wird gedruckt."}

    if 'manuell' in request.path:
        template = 'mypl/beleg_holen_manuell.html'
    else:
        template = 'mypl/beleg_holen.html'
    return render_to_response(template, {'anzeige': anzeige, 'printers': printers},
                              context_instance=RequestContext(request))


@permission_required('mypl.can_initiate_provisioning')
def movement_init(request):
    """Manually init a movement."""

    anzeige = {}

    if request.method == "POST":
        nve = request.POST.get('nve')
        if nve:
            try:
                movement_id = Kerneladapter().init_movement_to_good_location(nve)
                movement = Movement(movement_id)
                zwitscher('%s versucht eine Umlagerung von %s zu initialisieren' % (request.user, nve), username='mypl')
                movement.output_on_printer(printer="DruckerAllmanFach2")
                anzeige = {'class': u"acknowledgement",
                           'headline': u"Movement erfolgt.",
                           'paragraph': u'NVE #%s wird umgelagert. Umlagerungsnummer: %s' % (nve, movement_id)}
            except:
                anzeige = {'class': u"warning",
                           'headline': u'Fehler bei Umlagerung.',
                           'paragraph': u'NVE #%s konnte nicht umgelagert werden.' % (nve)}
        else:
            anzeige = {'class': u"warning",
                       'headline': u'NVE fehlt.',
                       'paragraph': u'Bitte geben Sie eine gültige NVE ein.'}

    return render_to_response('mypl/movement_init.html', {'anzeige': anzeige}, context_instance=RequestContext(request))


@user_passes_test(lambda u: u.is_superuser)
def movement_rollback(request):
    """Movement abbrechen."""

    anzeige = {}

    if request.method == "POST":
        vorgangsnr = request.POST.get('vorgangsnr')

        if vorgangsnr:
            try:
                Kerneladapter().rollback_movement(vorgangsnr)
                anzeige = {'class': u"acknowledgement",
                           'headline': u"Umlagerungs storniert.",
                           'paragraph': u"Vorgang #%s wird storniert." % (vorgangsnr)}
            except:
                anzeige = {'class': u"warning",
                           'headline': u'Fehler bei Umlagerungsstornierung.',
                           'paragraph': u'Vorgang #%s konnte nicht storniert werden.' % (vorgangsnr)}
        else:
            anzeige = {'class': u"warning",
                       'headline': u'Vorgangsnummer fehlt.',
                       'paragraph': u'Bitte geben Sie eine gültige Vorgangsnummer ein.'}
    return render_to_response('mypl/movement_rollback.html',
                              {'anzeige': anzeige},
                              context_instance=RequestContext(request))
