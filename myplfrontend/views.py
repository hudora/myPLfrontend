#!/usr/bin/env python
# encoding: utf-8

"""View functions for myplfrontend."""

from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from huTools.robusttypecasts import float_or_0
from hudjango.auth.decorators import require_login
from myplfrontend.forms import palletheightForm

import cs.masterdata.article
import cs.zwitscher
import django.views.decorators.http
import husoftm.bestaende
import itertools
import myplfrontend.kernelapi
import myplfrontend.tools


def _get_locations_by_height():
    """Returns a dict with location information of all locations.

    Keys of that dict are 'bebucht' and 'unbebucht',
    values are again dictionaries containing locations belonging to a given height."""
    booked, unbooked = {}, {}

    # i suspect having a server-side (erlang) 'location_detail_list' would provide a great speedup here
    for location in myplfrontend.kernelapi.get_location_list():
        info = myplfrontend.kernelapi.get_location(location)
        if int(info['preference']) < 1:
            continue
        loc_info = dict(name=info['name'], preference=info['preference'])
        height = info['height']
        if info['reserved_for'] or info['allocated_by']:
            booked.setdefault(height, []).append(loc_info)
        else:
            unbooked.setdefault(height, []).append(loc_info)
    return booked, unbooked


def lager_info(request):
    """Render a page with basic information about the Lager."""
    
    kerneladapter = myplfrontent.kernelapi.Kerneladapter()
    anzahl_artikel = len(kerneladapter.get_article_list())
    
    booked, unbooked = _get_locations_by_height()
    booked = sorted((height, len(loc)) for height, loc in booked.items())
    unbooked = sorted((height, len(loc)) for height, loc in unbooked.items())
    
    num_booked = sum(platz[1] for platz in booked)
    num_unbooked = sum(platz[1] for x in unbooked)
        
    ctx = {
            'anzahl_bebucht': num_booked,
            'anzahl_unbebucht': num_unbooked,
            'anzahl_plaetze': num_booked + num_unbooked,
            'anzahl_artikel': anzahl_artikel,
            'plaetze_bebucht': booked,
            'plaetze_unbebucht': unbooked
    }
    
    extra_info = kerneladapter.get_statistics()
    extra_info['oldest_movement'] = myplfrontend.kernelapi.fix_timestamp(extra_info['oldest_movement'])
    extra_info['oldest_pick'] = myplfrontend.kernelapi.fix_timestamp(extra_info['oldest_pick'])
    ctx.update(extra_info)
    return render_to_response('myplfrontend/lager_info.html', ctx, context_instance=RequestContext(request))


def info_panel(request):
    """Renders a page, that shows an info panel for the employees in the store."""
    pipeline = [myplfrontend.kernelapi.get_kommiauftrag(kommi) for kommi in myplfrontend.kernelapi.get_kommiauftrag_list()]
    for kommi in pipeline:
        kommi['orderlines_count'] = len(kommi.get('orderlines', []))

    db = myplfrontend.tools.get_pickinfo_from_pipeline_data(pipeline)

    # FIXME: Der Code hier beruht noch teilweise auf den Daten, die aus der zugeh. Django DB kamen, zB. postions['done'] wurde vorher
    # aus dieser DB berechnet. Wie können wir die erledigten Positionen aus dem Kernel / couchdb / ... erhalten?
    
    positions = {}
    positions['done'] = 0
    positions['inwork'] = 0
    if 'yes' in db: # FIXME aus dem get_pickinfo_from_pipeline_data() code verstehe ich nicht, wo hier ein key 'yes' herkommen soll?
        positions['todo'] = int(db['yes']['orderlines_count'])
    else:
        positions['todo'] = 0
    positions['total'] = positions['done'] + positions['inwork'] + positions['todo']
    if positions['total']:
        positions['percent_done'] = (100.0/positions['total']) * positions['done']
    else:
        positions['percent_done'] = 0
    return render_to_response('myplfrontend/info_panel.html',
                              {'pipeline': pipeline, 'db': db, 'positions': positions},
                              context_instance=RequestContext(request))
    

def artikel_heute(request):
    """Renders a view of all articles and quantities that have to be shipped today"""

    # summarize product quantities
    products = {}
    for komminr in myplfrontend.kernelapi.get_kommiauftrag_list():
        kommi = myplfrontend.kernelapi.get_kommiauftrag(komminr)
        if kommi['shouldprocess'] == 'yes':
            for orderline in kommi['orderlines']:
                artnr = orderline['artnr']
                products[artnr] = products.get(artnr, 0) + orderline['menge']

    artikel_heutel = []
    for artnr, quantity in products.items():
        product = cs.masterdata.article.eap(artnr)
        if product:
            total_weight = quantity * float_or_0(product["package_weight"]) / 1000. # kg
            total_volume = quantity * float_or_0(product["package_volume_liter"])
            total_palettes = quantity / float_or_0(product["palettenfaktor"], default=1.0)
            artikel_heutel.append({'quantity': quantity, 'artnr': artnr, 'name': product["name"],
                                   'palettenfaktor': product["palettenfaktor"], 'total_weight': total_weight,
                                   'total_volume': total_volume, 'paletten': total_palettes})
        else:
            cs.zwitscher.zwitscher('%s: Nicht in CouchDB. OMG! #error' % artnr, username='mypl')
    return render_to_response('myplfrontend/artikel_heute.html', {'artikel_heute': artikel_heutel},
                              context_instance=RequestContext(request))
    

def abc(request):
    """Render ABC Classification."""
    klasses = {}
    for name, klass in myplfrontend.kernelapi.get_abc().items():
        tmp = []
        for (quantity, artnr) in klass:
            product_detail = myplfrontend.kernelapi.get_article(artnr)
            full_quantity = product_detail["full_quantity"]
            nves_count = len(product_detail["muis"])
            tmp.append((quantity, full_quantity, artnr, nves_count))
        klasses[name] = tmp
    return render_to_response('myplfrontend/abc.html', {'klasses': klasses},
                              context_instance=RequestContext(request))


def penner(request):
    """Render Products with no recent activity."""
    abc_articles = set(artnr for (m, artnr) in itertools.chain(*myplfrontend.kernelapi.get_abc().values()))
    lagerbestand = set(myplfrontend.kernelapi.get_article_list())
    artnrs = lagerbestand - abc_articles
    
    pennerliste = []
    for artnr in artnrs:
        product_detail = myplfrontend.kernelapi.get_article(artnr)
        full_quantity = product_detail["full_quantity"]
        nves_count = len(product_detail["muis"])
        pennerliste.append((nves_count, full_quantity, artnr))
    pennerliste.sort(reverse=True)
    return render_to_response('myplfrontend/penner.html', {'pennerliste': pennerliste},
                              context_instance=RequestContext(request))
    

def lagerplaetze(request):
    """Render a list of all Lagerplätze."""
    # TODO: rewrite using http://hurricane.local.hudora.biz:8000/location
    booked_plaetze, unbooked_plaetze = _get_locations_by_height()
    booked_plaetze = sorted(booked_plaetze.items(), reverse=True)
    unbooked_plaetze = sorted(unbooked_plaetze.items(), reverse=True)
    return render_to_response('myplfrontend/lagerplaetze.html',
                              {'booked': booked_plaetze, 'unbooked': unbooked_plaetze},
                              context_instance=RequestContext(request))
    

def lagerplatz_detail(request, location):
    """Render details for a location."""

    platzinfo = myplfrontend.kernelapi.get_location(location)

    units = []
    for mui in platzinfo['allocated_by']:
        units.append(myplfrontend.kernelapi.get_unit(mui))
    
    # TODO: alle movements und korrekturbuchungen auf diesem Platz zeigen
    
    return render_to_response('myplfrontend/platz_detail.html',
                              {'title': 'Lagerplatz %s' % location, 'platzinfo': platzinfo, 'units': units},
                              context_instance=RequestContext(request))


def show_articles(request, want_softm):
    """Render a list of all articles."""
    if request.method == 'POST' and 'article' in request.POST:
        url = './' + request.POST['article']
        return HttpResponseRedirect(url)
    
    articles = []
    for artnr in myplfrontend.kernelapi.get_article_list():
        article = myplfrontend.kernelapi.get_article(artnr)
        article['name'] = cs.masterdata.article.name(article['artnr'])
        if want_softm:
            article['buchbestand'] = husoftm.bestaende.buchbestand(lager=100, artnr=article['artnr'])
        articles.append(article)
    
    # TODO: Artikel finden, von dneen SoftM denkt, sie wären im myPL, von denen das myPL aber nichts weiss
    
    title = 'Artikel am Lager'
    if want_softm:
        title += ' mit SoftM Buchbeständen'
    return render_to_response('myplfrontend/articles.html', {'title': title,
                                                           'articles': articles,
                                                           'want_softm': want_softm},
                              context_instance=RequestContext(request))
    

def article_detail(request, artnr):
    """Render details regarding an article."""
    
    data = myplfrontend.kernelapi.get_article(artnr)
    myunits = []
    for mynve in data['muis']:
        myunits.append(myplfrontend.kernelapi.get_unit(mynve))
    
    title = 'Artikelinformationen: %s (%s)' % (cs.masterdata.article.name(artnr), artnr)
    bestand100 = None
    try:
        bestand100 = husoftm.bestaende.bestand(artnr=artnr, lager=100)
    except:
        pass
    
    return render_to_response('myplfrontend/article_details.html',
                 {'title': title,
                  'full_quantity': data['full_quantity'],
                  'available_quantity': data['available_quantity'],
                  'pick_quantity': data['pick_quantity'],
                  'bestand100': bestand100,
                  'movement_quantity': data['movement_quantity'],
                  'artnr': artnr, 'myunits': myunits}, context_instance=RequestContext(request))
    

def article_audit(request, artnr):
    """Render the Audit-Log (Artikelkonto) of a certain article."""
    audit = myplfrontend.kernelapi.get_article_audit(artnr)
    return render_to_response('myplfrontend/article_audit.html',
                              {'title': 'Artikelkonto %s' % artnr,
                               'artnr': artnr, 'audit': audit},
                              context_instance=RequestContext(request))
    

def bewegungen(request):
    """Liste aller offenen Picks und Movements"""
    movements = []
    for movementid in sorted(myplfrontend.kernelapi.get_movements_list()):
        movements.append(myplfrontend.kernelapi.get_movement(movementid))
    picks = []
    for pickid in sorted(myplfrontend.kernelapi.get_picks_list()):
        picks.append(myplfrontend.kernelapi.get_pick(pickid))
    return render_to_response('myplfrontend/movement_list.html',
                              {'movements': movements, 'picks': picks},
                              context_instance=RequestContext(request))
    

def movement_show(request, mid):
    """Informationen zu einer Bewegung"""
    
    movement = myplfrontend.kernelapi.get_movement(mid)
    if not movement:
        raise Http404
    title = 'Movement %s' % mid
    if movement.get('archived'):
        title += ' (archiviert)'
    return render_to_response('myplfrontend/movement_info.html',
                              {'movement': movement, 'title': title},
                              context_instance=RequestContext(request))
    

def pick_show(request, pickid):
    """Informationen zu einem Pick"""
    
    pick = myplfrontend.kernelapi.get_pick(pickid)
    if not pick:
        raise Http404
    title = 'Pick %s' % pickid
    if pick.get('archived'):
        title += ' (archiviert)'
    return render_to_response('myplfrontend/pick_info.html',
                              {'title': title, 'pick': pick},
                              context_instance=RequestContext(request))
    

def unit_list(request):
    """Render a list of all MUIs/NVEs/SSCCs"""
    
    muis = myplfrontend.kernelapi.get_units_list()
    return render_to_response('myplfrontend/unit_list.html',
                              {'title': 'Units im Lager', 'muis': sorted(muis)},
                              context_instance=RequestContext(request))
    

def unit_show(request, mui):
    """Render Details for an Unit."""
    
    unit = myplfrontend.kernelapi.get_unit(mui)
    
    form = None
    if request.method == "POST":
        form = palletheightForm(request.POST)
        if unit.get('archived'):
            #message
            pass
    
        elif form.is_valid():
            myplfrontend.kernelapi.set_unit_height(mui, form.cleaned_data['height'])
    
    elif not unit.get('archived'):
        form = palletheightForm({'height': unit.get('height', 1950)})
    
    title = 'Unit %s' % mui
    if unit.get('archived'):
        title += ' (archiviert)'
    audit = myplfrontend.kernelapi.get_audit('selection/unitaudit', mui)
    return render_to_response('myplfrontend/unit_detail.html',
                              {'title': title,
                               'unit': unit, 'audit': audit,
                               'paletform': form},
                              context_instance=RequestContext(request))
    

def kommiauftrag_list(request):
    """Render a view of entries beeing currently processed in the provpipeline."""
    kommiauftraege_new, kommiauftraege_processing, pipelincutoff = [], [], False
    kommiauftraege = [] # falls es nix zu kommisionieren gibt
    for kommiauftragnr in myplfrontend.kernelapi.get_kommiauftrag_list():
        kommiauftrag = myplfrontend.kernelapi.get_kommiauftrag(kommiauftragnr)
        if kommiauftrag['status'] == 'processing':
            kommiauftraege_processing.append(myplfrontend.kernelapi.get_kommiauftrag(kommiauftragnr))
        else:
            kommiauftraege_new.append(myplfrontend.kernelapi.get_kommiauftrag(kommiauftragnr))
        
        kommiauftraege = kommiauftraege_processing + kommiauftraege_new
        if len(kommiauftraege) > 200:
            pipelincutoff = True
            kommiauftraege = kommiauftraege[:200]
    
    return render_to_response('myplfrontend/kommiauftraege.html',
                              {'title': 'Komissionierungen, die nicht erledigt sind.',
                               'kommiauftraege': kommiauftraege, 'pipelincutoff': pipelincutoff}, #, 'db': db},
                              context_instance=RequestContext(request))
    

@require_login
@permission_required('mypl.can_change_priority')
def kommiauftrag_set_priority(request, kommiauftragnr):
    priority = int(request.POST.get('priority').strip('p'))
    content = myplfrontend.kernelapi.set_kommiauftrag_priority(
            kommiauftragnr,
            explanation='Prioritaet auf %d durch %s geaendert' % (priority, request.user.username),
            priority=priority)
    return HttpResponse(content, mimetype='application/json')


@django.views.decorators.http.require_POST
@permission_required('mypl.can_zeroise_provisioning')
def kommiauftrag_nullen(request, kommiauftragnr):
    begruendung = request.POST.get('begruendung').strip()
    content = myplfrontend.kernelapi.kommiauftrag_nullen(kommiauftragnr, request.user.username, begruendung)
    if content:
        request.user.message_set.objects.create('%s erfolgreich genullt' % kommiauftragnr)
        return HttpResponseRedirect('../')
    else:
        return HttpResponse("Fehler beim Nullen von %r" % kommiauftragnr, mimetype='text/plain', status=500)


@django.views.decorators.http.require_POST
@permission_required('mypl.can_cancel_movement')
def bewegung_stornieren(request, movementid):
    """Cancel a movement."""

    content = myplfrontend.kernelapi.movement_stornieren(movementid)

    if content:
        cs.zwitscher.zwitscher('%s erfolgreich storniert (%s)' % (movementid, request.user.username))
        request.user.message_set.objects.create('%s erfolgreich storniert' % movementid)
        return HttpResponseRedirect('../')
    else:
        return HttpResponse("Fehler beim stornieren", mimetype='text/plain', status=500)


@require_login
def kommiauftrag_show(request, kommiauftragnr):
    """Render a page with further information for a single Kommiauftrag."""
    kommiauftrag = myplfrontend.kernelapi.get_kommiauftrag(kommiauftragnr)
    # Prüfen, ob genug Ware für den Artikel verfügbar ist.
    orderlines = []
    if not kommiauftrag.get('archived') and 'orderlines' in kommiauftrag:
        for orderline in kommiauftrag['orderlines']:
            orderline['picksuggestion'] = myplfrontend.kernelapi.find_provisioning_candidates(
                                                             orderline['menge'], orderline['artnr'])
            available = bool(orderline['picksuggestion'])
            orderline['available'] = available
            if not available:
                orderline['fehler'] = u'Kann zur Zeit nicht efüllt werden'
            orderlines.append(orderline)
    kommischeine = []
    for kommischein_id in kommiauftrag.get('provisioninglists', []):
        kommischein = myplfrontend.kernelapi.get_kommischein(kommischein_id)
        provisionings = []
        for provisioning_id in kommischein.get('provisioning_ids', []):
            if kommischein.get('type') == 'picklist':
                provisioning = myplfrontend.kernelapi.get_pick(provisioning_id)
                if not provisioning:
                    provisioning = {}
                provisioning.update({'id': provisioning_id})
                provisionings.append(provisioning)
        kommischein['provisionings'] = provisionings
        kommischeine.append(kommischein)
        # [[["id","p08437559"],["type","picklist"],["provpipeline_id","3097046"],["destination","AUSLAG"],
        # ["parts",1],["attributes",[["volume",658.2239999999999],["anbruch",false],["weight",14268],
        # ["paletten",0.10238095238095238],["export_packages",2.0]]],["status","new"],["created_at",
        # "20091016T00113536.000000"],["provisioning_ids",["P08437537","P08437544"]]]]
        # [{'anbruch': True,
        # 'created_at': '2009-10-19T08:26:00.000000Z',
        # 'status': 'new',
        # 'type': 'picklist',
    
    # TODO: change to unitaudit
    audit = myplfrontend.kernelapi.get_audit('fields/by_komminr', kommiauftragnr)
    title = 'Kommissionierauftrag %s' % kommiauftragnr
    if kommiauftrag.get('archived'):
        title += ' (archiviert)'

    return render_to_response('myplfrontend/kommiauftrag.html',
                              {'title': title,
                               'kommiauftrag': kommiauftrag,
                               'orderlines': orderlines,
                               'kommischeine': kommischeine,
                               'auditlines': audit},
                              context_instance=RequestContext(request))


def requesttracker(request):
    """Display a table containing requesttracker data from kernelE."""
    tracking_infos = myplfrontend.kernelapi.requesttracker()
    return render_to_response('myplfrontend/requesttracker.html', dict(tracking_infos=tracking_infos),
                              context_instance=RequestContext(request))


def softmdifferences(request):
    """Show the differences between SoftM and myPL stock."""
    differences = myplfrontend.tools.find_softm_differences()
    return render_to_response('myplfrontend/softmdifferences.html', {'differences': differences},
                              context_instance=RequestContext(request))
