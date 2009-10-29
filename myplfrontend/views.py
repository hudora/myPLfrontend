#!/usr/bin/env python
# encoding: utf-8

"""View functions for myplfrontend."""

import couchdb
import datetime
import django.views.decorators.http
import httplib2
import husoftm.bestaende
import kernelapi
import myplfrontend.tools
import simplejson as json
from cs.zwitscher import zwitscher
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from huTools.robusttypecasts import float_or_0
from hudjango.auth.decorators import require_login
from mypl.kernel import Kerneladapter
from mypl.models import Lieferschein, Event, get_provisionings_by_id
from mypl.tools import get_products_to_ship_today
from operator import itemgetter
from produktpass.models import Product
import cs.masterdata.article


COUCHSERVER = "http://couchdb.local.hudora.biz:5984"
KERNELURL = "http://hurricane.local.hudora.biz:8000"

def _get_data_from_kernel(path):
    """Return data from the kernel, gotten from SERVER/path.
    
    It does a GET request, receives json, and decodes this for you.
    """
    httpconn = httplib2.Http()
    resp, content = httpconn.request(KERNELURL + '/%s' % path, 'GET')
    if resp.status == 200:
        return json.loads(content)
    else:
        raise RuntimeError("can't get reply from kernel")


def _get_locations_by_height():
    """Returns a dict with location information of all locations.

    Keys of that dict are 'bebucht' and 'unbebucht',
    values are again dictionaries containing locations belonging to a given height."""
    kerneladapter = Kerneladapter()
    booked, unbooked = {}, {}
    
    # TODO: move to http
    for location in kerneladapter.location_list():
        info = kerneladapter.location_info(location)
        loc_info = dict(name=info['name'], preference=info['preference'])
        height = info['height']
        if (info['reserved_for'] or info['allocated_by']):
            booked.setdefault(height, []).append(loc_info)
        else:
            unbooked.setdefault(height, []).append(loc_info)

    return (booked, unbooked, )


def index(request):
    """Render static index page."""
    return render_to_response('myplfrontend/index.html', {}, context_instance=RequestContext(request))
    

def _lager_info():
    """This is the logic for the lager_info view.

    A dict is created, containing information about warehouse status."""
    # TODO: move to http
    kerneladapter = Kerneladapter()
    anzahl_artikel = len(kerneladapter.count_products())

    booked_plaetze, unbooked_plaetze = _get_locations_by_height()

    booked_plaetze = sorted([(height, len(loc), ) for height, loc in booked_plaetze.items()])
    unbooked_plaetze = sorted([(height, len(loc), ) for height, loc in unbooked_plaetze.items()])

    nplaetze_booked = sum([x[1] for x in booked_plaetze])
    nplaetze_unbooked = sum([x[1] for x in unbooked_plaetze])
    nplaetze_gesamt = nplaetze_booked + nplaetze_unbooked

    return {'anzahl_bebucht': nplaetze_booked, 'anzahl_unbebucht': nplaetze_unbooked,
                'anzahl_plaetze': nplaetze_gesamt, 'anzahl_artikel': anzahl_artikel,
                'plaetze_bebucht': booked_plaetze, 'plaetze_unbebucht': unbooked_plaetze}
    

def lager_info(request):
    """Render a page with basic information about the Lager."""
    # TODO: move to http and inline code above
    info = _lager_info()
    
    extra_info = kernelapi.get_statistics()

    info.update(extra_info)

    return render_to_response('myplfrontend/lager_info.html', info, context_instance=RequestContext(request))

    
def kommischein_info(request, kommischeinid):
    """kommischein ist auch bekannt als picklist, retrievallist oder provisioninglist."""
    # TODO: move to http, mixme, md
    kerneladapter = Kerneladapter()
    kommischein = {}
    try:
        unit = kerneladapter.unit_info(mui)
    except:
        server = couchdb.client.Server(COUCHSERVER)
        db = server["mypl_archive"]
        raw_reply = db.view('selection/kommischeine', key=mui, limit=1)
        for doc in [db[x.id] for x in raw_reply if x.key.startswith(mui)]:
            kommischein = doc
    # (mypl_produktion@airvent)346> mypl_prov_query:provisioninglist_info("p08147727").
    # {ok,[{id,"p08147727"},
    #      {type,picklist},
    #      {provpipeline_id,"3096132"},
    #      {destination,"AUSLAG"},
    #      {parts,1},
    #      {attributes,[{volume,41.598375000000004},
    #                   {anbruch,true},
    #                   {weight,13540},
    #                   {paletten,0.04791666666666666},
    #                   {export_packages,1.0}]},
    #      {status,new},
    #      {created_at,{{2009,10,9},{5,4,29}}},
    #      {provisioning_ids,["P08147696","P08147704","P08147715"]}]}
    # 
   

def info_panel(request):
    """Renders a page, that shows an info panel for the employees in the store"""
    kerneladapter = Kerneladapter()
    # TODO: switch to http
    pipeline = kerneladapter.provpipeline_list_new()
    db = myplfrontend.tools.get_pickinfo_from_pipeline_data(pipeline)
    
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM mypl_lieferschein ls, mypl_lieferscheinposition lsp "
                  + "WHERE ls.id=lsp.lieferschein_kopf_id AND ls.status='in_interface' "
                  + "AND DATE(ls.updated_at)=CURRENT_DATE;")
    row_done = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM mypl_lieferschein ls, mypl_lieferscheinposition lsp "
                  + "WHERE ls.id=lsp.lieferschein_kopf_id AND (ls.status='provisioning_ready' OR "
                  + "ls.status='in_provisioning') AND DATE(ls.updated_at)=CURRENT_DATE;")
    row_inwork = cursor.fetchone()
    cursor.close()
    
    positions = {}
    positions['done'] = int(row_done[0])
    positions['inwork'] = int(row_inwork[0])
    if 'yes' in db:
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
    # TODO: convert to HTTP-API and move get_products_to_ship_today() inline
    artikel_heutel = []
    for artnr, quantity in get_products_to_ship_today().items():
        try:
            product = Product.objects.get(artnr=artnr)
            total_weight = quantity * float_or_0(product.package_weight_kg)
            total_volume = quantity * float_or_0(product.package_volume)
            total_palettes = quantity / float_or_0(product.palettenfaktor, default=1.0)
            artikel_heutel.append({'quantity': quantity, 'artnr': artnr, 'name': product.name,
                                   'palettenfaktor': product.palettenfaktor, 'total_weight': total_weight,
                                   'total_volume': total_volume, 'paletten': total_palettes})
        except Product.DoesNotExist:
            zwitscher('%s: Kein Artikelpass. OMG! #error' % artnr, username='mypl')
    return render_to_response('myplfrontend/artikel_heute.html', {'artikel_heute': artikel_heutel},
                              context_instance=RequestContext(request))
    

def abc(request):
    """Render ABC Classification."""

    # TODO: move to http://hurricane.local.hudora.biz:8000/abc
    kerneladapter = Kerneladapter()
    klasses = {}
    for name, klass in zip(('a', 'b', 'c'), kerneladapter.get_abc()):
        tmp = []
        for (quantity, artnr) in klass:
            mengen, nves = kerneladapter.count_product(artnr)
            tmp.append((quantity, mengen[0], artnr, len(nves)))
        klasses[name] = tmp
    return render_to_response('myplfrontend/abc.html', {'klasses': klasses},
                              context_instance=RequestContext(request))


def penner(request):
    """Render Products with no recent activity."""
    # TODO: move to http://hurricane.local.hudora.biz:8000/abc
    kerneladapter = Kerneladapter()
    
    abc_articles = []
    for klass in kerneladapter.get_abc():
        # collecting artnrs
        abc_articles.extend([tmp[1] for tmp in klass])
    
    lagerbestand = kerneladapter.count_products()
    artnrs = set([x[0] for x in lagerbestand])
    artnrs -= set(abc_articles)
    
    pennerliste = []
    for artnr in sorted(artnrs):
        mengen, nves = kerneladapter.count_product(artnr)
        pennerliste.append((len(nves), mengen[0], artnr))
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

    platzinfo = kernelapi.get_location(location)

    units = []
    for mui in platzinfo['allocated_by']:
        units.append(kernelapi.get_unit(mui))
    
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
    for artnr in kernelapi.get_article_list():
        tmp = kernelapi.get_article(artnr)
        tmp['name'] = cs.masterdata.article.name(tmp['artnr'])
        if want_softm:
            tmp['buchbestand'] = husoftm.bestaende.buchbestand(lager=100, artnr=tmp['artnr'])
        articles.append(tmp)
    
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
    
    data = kernelapi.get_article(artnr)
    myunits = []
    for mynve in data['muis']:
        myunits.append(kernelapi.get_unit(mynve))
    
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
    audit = kernelapi.get_article_audit(artnr)
    return render_to_response('myplfrontend/article_audit.html',
                              {'title': 'Artikelkonto %s' % artnr,
                               'artnr': artnr, 'audit': audit},
                              context_instance=RequestContext(request))
    

def bewegungen(request):
    """Liste aller offenen Picks und Movements"""
    movements = []
    for movementid in sorted(kernelapi.get_movements_list()):
        movements.append(kernelapi.get_movement(movementid))
    picks = []
    for pickid in sorted(kernelapi.get_picks_list()):
        picks.append(kernelapi.get_pick(pickid))
    return render_to_response('myplfrontend/movement_list.html',
                              {'movements': movements, 'picks': picks},
                              context_instance=RequestContext(request))
    

def movement_show(request, mid):
    """Informationen zu einer Bewegung"""
    
    movement = kernelapi.get_movement(mid)
    title = 'Movement %s' % mid
    if movement.get('archived'):
        title += ' (archiviert)'
    return render_to_response('myplfrontend/movement_info.html',
                              {'movement': movement, 'title': title},
                              context_instance=RequestContext(request))
    

def pick_show(request, pickid):
    """Informationen zu einem Pick"""
    
    pick = kernelapi.get_pick(pickid)
    title = 'Pick %s' % pickid
    if pick.get('archived'):
        title += ' (archiviert)'
    return render_to_response('myplfrontend/pick_info.html',
                              {'title': title, 'pick': pick},
                              context_instance=RequestContext(request))
    

def unit_list(request):
    """Render a list of all MUIs/NVEs/SSCCs"""
    
    muis = kernelapi.get_units_list()
    return render_to_response('myplfrontend/unit_list.html',
                              {'title': 'Units im Lager', 'muis': sorted(muis)},
                              context_instance=RequestContext(request))
    

def unit_show(request, mui):
    """Render Details for an Unit."""
    
    unit = kernelapi.get_unit(mui)
    
    title = 'Unit %s' % mui
    if unit.get('archived'):
        title += ' (archiviert)'
    audit = myplfrontend.kernelapi.get_audit('selection/unitaudit', mui)
    return render_to_response('myplfrontend/unit_detail.html',
                              {'title': title,
                               'unit': unit, 'audit': audit},
                              context_instance=RequestContext(request))
    

def kommiauftrag_list(request):
    """Render a view of entries beeing currently processed in the provpipeline."""
    kommiauftraege_new, kommiauftraege_processing, pipelincutoff = [], [], False
    for kommiauftragnr in kernelapi.get_kommiauftrag_list():
        kommiauftrag = kernelapi.get_kommiauftrag(kommiauftragnr)
        if kommiauftrag['status'] == 'processing':
            kommiauftraege_processing.append(kernelapi.get_kommiauftrag(kommiauftragnr))
        else:
            kommiauftraege_new.append(kernelapi.get_kommiauftrag(kommiauftragnr))
        
        kommiauftraege = kommiauftraege_processing + kommiauftraege_new
        if len(kommiauftraege) > 200:
            pipelincutoff = True
            kommiauftraege = kommiauftraege[:200]
    
    return render_to_response('myplfrontend/kommiauftraege.html',
                              {'title': 'Komissionierungen, die nicht erledigt sind.',
                               'kommiauftraege': kommiauftraege, 'pipelincutoff': pipelincutoff}, #, 'db': db},
                              context_instance=RequestContext(request))
    

@require_login
def kommiauftrag_set_priority(request, kommiauftragnr):
    priority = int(request.POST.get('priority').strip('p'))
    data = json.dumps({'explanation': 'Prioritaet auf %d durch %s geaendert' % (priority, 
                                                                                request.user.username),
                       'priority': priority})
    h = httplib2.Http()
    resp, content = h.request('http://hurricane.local.hudora.biz:8000/kommiauftrag/%s/priority' % kommiauftragnr,
                              'POST', data)
    return HttpResponse(content, mimetype='application/json')
    

@require_login
@django.views.decorators.http.require_POST
def kommiauftrag_nullen(request, kommiauftragnr):
    begruendung = request.POST.get('begruendung').strip()
    data = u'Kommiauftrag durch %s genullt. Begruendung: %s' % (request.user.username, begruendung)
    h = httplib2.Http()
    resp, content = h.request('http://hurricane.local.hudora.biz:8000/kommiauftrag/%s' % kommiauftragnr,
                              'DELETE', data)
    if resp['status'] == '204':
       request.user.message_set.create(message='Auftrag wurde genullt')
       zwitscher(u'Kommiauftrag %s durch %s genullt. Begruendung: %s' % (kommiauftragnr,
                                                                         request.user.username,
                                                                         begruendung), username='mypl')
       return HttpResponseRedirect('../')
    return HttpResponse("Fehler beim Nullen %r | %r" % (resp, content),
                        mimetype='text/plain', status=500)
    

@require_login
def kommiauftrag_show(request, kommiauftragnr):
    """Render a page with further information for a single Kommiauftrag"""
    
    kommiauftrag = kernelapi.get_kommiauftrag(kommiauftragnr)
    # TODO: move to HTTP, md
    kerneladapter = Kerneladapter()
    
    # Prüfen, ob genug Ware für den Artikel verfügbar ist.
    orderlines = []
    if 'orderlines' in kommiauftrag and not kommiauftrag.get('archived'):
        for orderline in kommiauftrag['orderlines']:
            orderline['picksuggestion'] = kerneladapter.find_provisioning_candidates(orderline['menge'],
                                                                                     orderline['artnr'])
            orderline['fehler'] = ''
            if orderline['picksuggestion'] and orderline['picksuggestion'][0] != 'error':
                orderline['available'] = True
            else:
                orderline['available'] = False
                if orderline['picksuggestion'] and orderline['picksuggestion'][1] == 'not_enough':
                    orderline['fehler'] = 'Nicht genug Ware am Lager'
            orderlines.append(orderline)
    
    kommischeine = []
    h = httplib2.Http()
    for kommischein_id in kommiauftrag.get('provisioninglists', []):
        resp, content = h.request('http://hurricane.local.hudora.biz:8000/kommischein/%s' % kommischein_id,
                                  'GET')
        kommischein = {}
        if resp.status == 200:
            kommischein = json.loads(content)
        else:
            # kommiauftrag aus dem Archiv holen
            server = couchdb.client.Server(COUCHSERVER)
            db = server['mypl_archive']
            # TODO: time out and retry with stale=ok
            # see http://wiki.apache.org/couchdb/HTTP_view_API
            for row in db.view('selection/kommischeine', key=kommischein_id, limit=1, include_docs=True):
                kommischein = kernelapi.fix_timestamps(row.doc)
        kommischein.update({'id': kommischein_id})
        provisionings = []
        for provisioning_id in kommischein.get('provisioning_ids', []):
            if kommischein.get('type', ) == 'picklist':
                resp, content = h.request('http://hurricane.local.hudora.biz:8000/pick/%s' % provisioning_id,
                                          'GET')
                provisioning = {}
                if resp.status == 200:
                    provisioning = json.loads(content)
                
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
    title =  'Kommissionierauftrag %s' % kommiauftragnr
    if kommiauftrag.get('archived'):
        title += ' (archiviert)'
    return render_to_response('myplfrontend/kommiauftrag.html', 
                              {'title': title,
                               'kommiauftrag': kommiauftrag,
                               'orderlines': orderlines, 'kommischeine': kommischeine,
                               'auditlines': audit},
                              context_instance=RequestContext(request))


