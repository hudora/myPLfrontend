# -*- coding: utf8 -*-

import sys
import random
try:
    import json
except:
    import simplejson as json
import time
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login, logout

# Wir brauchen den alten Kerneladapter noch solange, bis in den 
# neuen Kerneladapter die Moeglichkeit zum Rueckmelden einer 
# Umlagerung eingebaut ist. Sobald das erledigt ist muessen wir 
# den OldKernelAdapter rausnehmen und durch den neuen ersetzen.
from mypl.kernel import Kerneladapter as OldKerneladapter
from myplfrontend.kernelapi import Kerneladapter

from models import Staplerjob, make_job, STAPLERJOB_STATUS
from decorators import login_required
from cs.zwitscher import zwitscher


def index(request):
    return render_to_response('stapler/application.html',{}, context_instance=RequestContext(request))

def is_logged_in(request):
    is_logged_in = request.user.is_authenticated()
    job_count = Staplerjob.objects.filter(status='open', user=request.user).count()
    current_movement = job_count > 0
    return _render_to_json({'login':is_logged_in,
                            'current_movement': current_movement})

@require_POST
def do_login(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            return _render_to_json({'status':'OK'})
    return _render_to_json({'status':'FAIL'})

@require_POST
def do_logout(request):
    logout(request)
    return _render_to_json({'status':'OK'})

@login_required
def has_current_movement(request):
    try:
        return _render_to_json({'movement':True})
    except:
        return _render_to_json({'movement':False})

@require_POST
@login_required
def fetch_movement(request):
    # zuerst gucken wir, ob wir noch einen aktuellen Job in der DB haben
    try:
        job = Staplerjob.objects.get(status='open', user=request.user)
        json = job.serialized_movement

    # nein, haben wir nicht, also holen wir uns einen neuen Job vom Kernel
    # oder erzeugen im Debug-Mode ein Testmovement. Wenn wir einen Fehler 
    # vom Kernel bekommen zeigen wir auf dem iPhone ebenfalls einen Fehler an.
    except Staplerjob.DoesNotExist:
        try:
            #movement = Kerneladapter().get_next_movement(attr='%s via myPL Stapler' % request.user.username)
            movement = _get_dummy_movement()
            zwitscher("Staplerauftrag %s wurde geladen" % movement['oid'], username="stapler")
        except Exception:
            return HttpRespone('{"status":"exception"}', mimetype='application/json')

        # haben wir ein Movement vom Kernel bekommen? Wenn ja legen wir es
        # als Job in der lokalen DB ab und erzeugen die Ausgabe fuer den Client,
        # ansonsten gibt's eine passende Fehlermeldung fuer den Kernel
        if movement:
            job = make_job(request.user, movement)
            json = job.serialized_movement
        else:
            json = '{"status":"not_found"}'

    # und jetzt noch die fertige Msg zum Client liefern, fettich.
    return HttpResponse(json, mimetype='application/json')

@require_POST
@login_required
def commit_or_cancel_movement(request, what):
    oid = request.POST['oid']
    job = get_object_or_404(Staplerjob, movement_id=oid, user=request.user, status='open')
    if what == 'cancel':
        #Kerneladapter().movement_stornieren(oid, request.user.username, 'Storno via myPL Stapler')
        zwitscher("Staplerauftrag %s wurde storniert" % oid, username="stapler")
        job.status = 'canceled'
    else:
        # Der neue (HTTP-basierte) Kerneladapter unterstuetzt noch kein Rueckmelden von Movements:
        ##Kerneladapter().commit_movement(oid)
        #OldKerneladapter().commit_movement(oid)
        zwitscher("Staplerauftrag %s wurde rueckgemeldet" % oid, username="stapler")
        job.status = 'closed'
    job.closed_at = datetime.now()
    job.save()
    return _render_to_json({ 'status': 'OK' })

@require_POST
@login_required
def history(request):
    result = []
    username = request.user.username
    jobs = Staplerjob.objects.exclude(status='open') \
                             .filter(user__username=username) \
                             .order_by('-created_at')[0:10]
    for job in jobs:
        data = job.deserialized
        data['status'] = filter(lambda x: x, \
                                map(lambda (e,d): d if e==job.status else None, \
                                    STAPLERJOB_STATUS))[0] 
        result.append(data)
    return _render_to_json({ 'status': 'OK', 'data': result })

def _render_to_json(data):
    json_data = json.dumps(data)
    return HttpResponse(json_data, mimetype='application/json')

def _get_dummy_movement():
    """ liefert ein Testmovement zurueck, damit der Stapler-Source ohne 
        reale Anbindung an den Kernel getestet werden kann """

    ident = str(random.randint(10, 90))
    return { 'artnr': '!DUMMY! ' + ident,
             'attr': 'test',
             'created_at': datetime.now().isoformat(),
             'from_location': '1103' + ident,
             'to_location': '03' + ident + '01',
             'menge': 11,
             'mui': '340059981002670930',
             'mypl_notify_requesttracker': True,
             'oid': 'mb091919' + ident,
             'reason': 'requesttracker',
             'status': 'open' }
