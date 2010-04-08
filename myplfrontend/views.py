#!/usr/bin/env python
# encoding: utf-8

"""View functions for myplfrontend."""

from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.cache import cache_page

from huTools.robusttypecasts import float_or_0
from hudjango.auth.decorators import require_login
from myplfrontend.forms import PalletHeightForm

import cs.masterdata.article
import cs.printing
import cs.zwitscher
import django.views.decorators.http
import husoftm.bestaende
import itertools
# import mypl.models
import myplfrontend.belege
import myplfrontend.kernelapi
from myplfrontend.kernelapi import Kerneladapter
import myplfrontend.tools


def _get_locations_by_height():
    """
    Erzeuge ein Tupel mit den bebuchten und unbebuchten Plätzen.
    
    Die Elemente des Tupels sind Dictionaries, deren Schlüssel die Platzhöhe
    und deren Keys Listen mit Informationen über die Plätze sind.
    
    Beispiel:
    ({1000: [{'name': '182503', 'preference': 6}],
      2000: [{'name': '032003', 'preference': 6},
             {'name': '042503', 'preference': 6},
             {'name': '043603', 'preference': 6}]
      },
      {1050: [{'name': '011503', 'preference': 1},
              {'name': '053603', 'preference': 6}]
    })
    
    Plätze mit einer Präferenz < 1 werden nicht berücksichtigt.
    """
    
    kerneladapter = Kerneladapter()
    booked, unbooked = {}, {}
    for location in kerneladapter.get_location_list():
        info = kerneladapter.get_location(location)
        if int(info['preference']) < 1:
            continue
        if info['reserved_for'] or info['allocated_by']:
            tmp = booked
        else:
            tmp = unbooked
        tmp.setdefault(info['height'], []).append({'name': info['name'], 'preference': info['preference']})
    return booked, unbooked


@cache_page(60 * 5)
def lager_info(request):
    """View für die Lager-Informations-Ansicht"""
    
    kerneladapter = Kerneladapter()
    anzahl_artikel = len(kerneladapter.get_article_list())
    booked, unbooked = _get_locations_by_height()
    booked = sorted((height, len(loc)) for height, loc in booked.items())
    unbooked = sorted((height, len(loc)) for height, loc in unbooked.items())
    
    num_booked = sum(platz[1] for platz in booked)
    num_unbooked = sum(platz[1] for x in unbooked)
    
    ctx = {'anzahl_bebucht': num_booked,
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


@cache_page(60 * 5)
def info_panel(request):
    """Renders a page, that shows an info panel for the employees in the store."""
    
    kerneladapter = Kerneladapter()
    pipeline = (kerneladapter.get_kommiauftrag(kommi) for kommi in kerneladapter.get_kommiauftrag_list())
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


@cache_page(60 * 5)
def artikel_heute(request):
    """View für Übersichtsseite mit den heute zu verschickenden Artikeln"""
    
    kerneladapter = Kerneladapter()
    
    # summarize product quantities
    products = {}
    for komminr in myplfrontend.kernelapi.get_kommiauftrag_list():
        kommi = kerneladapter.get_kommiauftrag(komminr)
        if kommi['shouldprocess'] == 'yes':
            for orderline in kommi['orderlines']:
                artnr = orderline['artnr']
                products[artnr] = products.get(artnr, 0) + orderline['menge']
    
    artikel_heutel = []
    for artnr, quantity in products.items():
        product = cs.masterdata.article.eap(artnr)
        if product:
            total_weight = quantity * float_or_0(product["package_weight"]) / 1000.0
            total_volume = quantity * float_or_0(product["package_volume_liter"])
            total_palettes = quantity / float_or_0(product["palettenfaktor"], default=1.0)
            artikel_heutel.append({'quantity': quantity,
                                   'artnr': artnr,
                                   'name': product['name'],
                                   'palettenfaktor': product['palettenfaktor'],
                                   'total_weight': total_weight,
                                   'total_volume': total_volume,
                                   'paletten': total_palettes})
        else:
            cs.zwitscher.zwitscher('%s: eAP nicht in CouchDB. OMG! #error' % artnr, username='mypl')
    return render_to_response('myplfrontend/artikel_heute.html', {'artikel_heute': artikel_heutel},
                              context_instance=RequestContext(request))

@cache_page(60 * 5)
def abc(request):
    """View für ABC-Klassifizierung"""
    
    kerneladapter = Kerneladapter()
    klasses = {}
    for name, klass in kerneladapter.get_abc().items():
        tmp = []
        for quantity, artnr in klass:
            product_detail = kerneladapter.get_article(artnr)
            full_quantity = product_detail["full_quantity"]
            nve_count = len(product_detail["muis"])
            tmp.append((quantity, full_quantity, artnr, nve_count))
        klasses[name] = tmp
    return render_to_response('myplfrontend/abc.html', {'klasses': klasses},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
def penner(request):
    """View für Penner-Übersicht (Artikel ohne Aktivität in der letzten Zeit)"""
    
    kerneladapter = Kerneladapter()
    abc_articles = set(artnr for (m, artnr) in itertools.chain(*kerneladapter.get_abc().values()))
    lagerbestand = set(kerneladapter.get_article_list())
    
    pennerliste = []
    for artnr in (lagerbestand - abc_articles):
        product_detail = kerneladapter.get_article(artnr)
        full_quantity = product_detail['full_quantity']
        nve_count = len(product_detail['muis'])
        pennerliste.append((nve_count, full_quantity, artnr))
    return render_to_response('myplfrontend/penner.html',
                              {'pennerliste': sorted(pennerliste, reverse=True)},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
def lagerplaetze(request):
    """View für Übersicht aller Lagerplätze"""
    
    booked_plaetze, unbooked_plaetze = _get_locations_by_height()
    booked_plaetze = sorted(booked_plaetze.items(), reverse=True)
    unbooked_plaetze = sorted(unbooked_plaetze.items(), reverse=True)
    return render_to_response('myplfrontend/lagerplaetze.html',
                              {'booked': booked_plaetze, 'unbooked': unbooked_plaetze},
                              context_instance=RequestContext(request))


@cache_page(60 * 2)
def lagerplatz_detail(request, location):
    """View für Detailansicht eines Lagerplatzes"""
    
    kerneladapter = Kerneladapter()
    platzinfo = kerneladapter.get_location(location)
    units = [kerneladapter.get_unit(mui)) for mui in platzinfo['allocated_by']]
    
    # TODO: alle movements und korrekturbuchungen auf diesem Platz zeigen
    # Und zwar wie?!?
    
    return render_to_response('myplfrontend/platz_detail.html',
                              {'title': 'Lagerplatz %s' % location, 'platzinfo': platzinfo, 'units': units},
                              context_instance=RequestContext(request))


def show_articles(request, want_softm):
    """Render a list of all articles."""
    if request.method == 'POST':
        url = './' + request.POST.get('article', '')
        return HttpResponseRedirect(url)
    
    articles = []
    for artnr in myplfrontend.kernelapi.get_article_list():
        article = myplfrontend.kernelapi.get_article(artnr)
        article['name'] = cs.masterdata.article.name(article['artnr'])
        if want_softm:
            article['buchbestand'] = husoftm.bestaende.buchbestand(lager=100, artnr=article['artnr'])
        articles.append(article)
    
    # TODO: Artikel finden, von denen SoftM denkt, sie wären im myPL, von denen das myPL aber nichts weiss
    # Wie?
    
    title = 'Artikel am Lager'
    if want_softm:
        title += ' mit SoftM Buchbeständen'
    return render_to_response('myplfrontend/articles.html',
                              {'title': title, 'articles': articles, 'want_softm': want_softm},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
def article_detail(request, artnr):
    """View für Detailansicht eines Artikels"""
    
    kerneladapter = Kerneladapter()
    article_info = kerneladapter.get_article(artnr)
    return render_to_response('myplfrontend/article_details.html',
                              {'title': 'Artikelinformationen: %s (%s)' % (cs.masterdata.article.name(artnr), artnr),
                               'article_info': article_info,
                               'bestand100': husoftm.bestaende.bestand(artnr=artnr, lager=100),
                               'units': [kerneladapter.get_unit(nve) for nve in article_info['muis']},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
def article_audit(request, artnr):
    """View für die Ansicht eines Artikelkontos eines Artikels (Audit-Log)"""
    kerneladapter = Kerneladapter()
    audit = kerneladapter.get_article_audit(artnr)
    return render_to_response('myplfrontend/article_audit.html',
                              {'title': 'Artikelkonto %s' % artnr, 'artnr': artnr, 'audit': audit},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
def bewegungen(request):
    """Liste aller offenen Picks und Movements"""
    
    kerneladapter = Kerneladapter()
    movements = [kerneladapter.get_movement(movement_id) for movement_id in sorted(kerneladapter.get_movements_list())]
    picks = [kerneladapter,get_pick(pick_id) for pick_id in sorted(kerneladapter.get_picks_list())]
    return render_to_response('myplfrontend/movement_list.html', {'movements': movements, 'picks': picks},
                              context_instance=RequestContext(request))


def movement_show(request, mid):
    """Informationen zu einer Bewegung"""
    
    kerneladapter = Kerneladapter()
    movement = kerneladapter.get_movement(mid)
    if not movement:
        raise Http404("Kein Movement mit ID %s gefunden" % mid)
    
    title = 'Movement %s' % mid
    if movement.get('archived'):
        title += ' (archiviert)'
    return render_to_response('myplfrontend/movement_info.html',
                              {'movement': movement, 'title': title},
                              context_instance=RequestContext(request))


def pick_show(request, pickid):
    """Informationen zu einem Pick"""
    
    kerneladapter = Kerneladapter()
    pick = kerneladapter.get_pick(pickid)
    if not pick:
        raise Http404("Kein Pick mit ID %s gefunden" % pickid)
    title = 'Pick %s' % pickid
    if pick.get('archived'):
        title += ' (archiviert)'
    return render_to_response('myplfrontend/pick_info.html',
                              {'title': title, 'pick': pick},
                              context_instance=RequestContext(request))


@cache_page(60 * 2)
def unit_list(request):
    """Render a list of all MUIs/NVEs/SSCCs"""
    
    kerneladapter = Kerneladapter()
    muis = kerneladapter.get_units_list()
    return render_to_response('myplfrontend/unit_list.html',
                              {'title': 'Units im Lager', 'muis': sorted(muis)},
                              context_instance=RequestContext(request))


def unit_show(request, mui):
    """View für Detailansicht einer MUI"""
    
    kerneladapter = Kerneladapter()
    unit = kerneladapter.get_unit(mui)
    
    if request.method == "POST":
        form = PalletHeightForm(request.POST)
        if unit.get('archived'):
            pass
        elif form.is_valid():
            kerneladapter.set_unit_height(mui, form.cleaned_data['height'])
    else:
        form = PalletHeightForm({'height': unit.get('height', 1950)})
    
    title = 'Unit %s' % mui
    if unit.get('archived'):
        title += ' (archiviert)'
    audit = kerneladapter.get_unit_audit(mui)
    return render_to_response('myplfrontend/unit_detail.html',
                              {'title': title,
                               'unit': unit, 'audit': audit,
                               'form': form},
                              context_instance=RequestContext(request))


def kommiauftrag_list(request):
    """View für Liste der Aufträge in der Provpipeline"""
    
    kerneladapter = Kerneladapter()
    kommiauftraege_new, kommiauftraege_processing = [], []
    kommiauftraege = [] # falls es nix zu kommisionieren gibt
    
    for kommiauftragnr in kerneladapter.get_kommiauftrag_list():
        kommiauftrag = kerneladapter.get_kommiauftrag(kommiauftragnr)
        
        if kommiauftrag['status'] == 'processing':
            kommiauftraege_processing.append(kerneladapter.get_kommiauftrag(kommiauftragnr))
        else:
            kommiauftraege_new.append(kerneladapter.get_kommiauftrag(kommiauftragnr))
        
        kommiauftraege = kommiauftraege_processing + kommiauftraege_new
        if len(kommiauftraege) > 200:
            cutoff = True
            kommiauftraege = kommiauftraege[:200]
        else:
            cutoff = False
    
    return render_to_response('myplfrontend/kommiauftraege.html',
                              {'title': 'Komissionierungen, die nicht erledigt sind.',
                               'kommiauftraege': kommiauftraege, 'cutoff': cutoff},
                              context_instance=RequestContext(request))


@require_login
@permission_required('mypl.can_change_priority')
def kommiauftrag_set_priority(request, kommiauftragnr):
    priority = int(request.POST.get('priority', '').strip('p'))
    kerneladapter = Kerneladapter()
    content = kerneladapter.set_kommiauftrag_priority(kommiauftragnr,
            explanation='Prioritaet auf %d durch %s geaendert' % (priority, request.user.username),
            priority=priority)
    return HttpResponse(content, mimetype='application/json')


@django.views.decorators.http.require_POST
@permission_required('mypl.can_zeroise_provisioning')
def kommiauftrag_nullen(request, kommiauftragnr):
    begruendung = request.POST.get('begruendung', '').strip()
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

    if myplfrontend.kernelapi.movement_stornieren(movementid):
        cs.zwitscher.zwitscher('%s erfolgreich storniert (%s)' % (movementid, request.user.username), username="mypl")
        request.user.message_set.objects.create('%s erfolgreich storniert' % movementid)
        return HttpResponseRedirect('../')
    else:
        return HttpResponse("Fehler beim stornieren", mimetype='text/plain', status=500) # XXX: Besser: Fehler anzeigen


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
    
    # TODO: change to unitaudit - GANZ GROSSER KOMMENTAR! DA WEISS JEDER IMMER SOFORT WAS GEMEINT IST!
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


##########
### Views, die schreibend auf das System zugreifen
##########

@require_login
@django.views.decorators.http.require_POST
def create_movement(request):
    """Erzeugt eine Umlagerung - soweit der Kernel meint, es würde eine anstehen"""

    # TODO: make use of PrinterChooser here
    movement = myplfrontend.kernelapi.create_automatic_movement({'user': request.user.username,
              'reason': 'manuell durch %s aus Requesttracker angefordert' % request.user.username})
    if not movement:
        request.user.message_set.create(message="Es stehen keine Umlagerungen an.")
    else:
        # movement ist ein Dict
        movement_id = movement['oid']
        # Umlagerbeleg drucken
        pdf = myplfrontend.belege.get_movement_pdf(movement_id)
        cs.printing.print_data(pdf, printer="DruckerAllman")
        request.user.message_set.create(message='Beleg %(oid)s wurde gedruckt' % movement)
    return HttpResponseRedirect('../')
