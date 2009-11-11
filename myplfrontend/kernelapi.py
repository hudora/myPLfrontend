#!/usr/bin/env python
# encoding: utf-8
"""
kernelapi.py - accesses kernelE via Python.

See http://cybernetics.../kernelE/trunk/docs/kernal-API.rst for details.

Created by Maximillian Dornseif on 2009-10-16.
Copyright (c) 2009 HUDORA. All rights reserved.
"""


from operator import itemgetter
import calendar
import couchdb
import cs.zwitscher
import datetime
import httplib2
import simplejson as json
import time


COUCHSERVER = "http://couchdb.local.hudora.biz:5984"
KERNELURL = "http://hurricane.local.hudora.biz:8000"


def get_audit(view, key):
    # Auditinformationen aus CouchDB holen
    audit = []
    COUCHDB_NAME = "mypl_audit"
    server = couchdb.client.Server(COUCHSERVER)
    db = server[COUCHDB_NAME]
    for row in db.view(view, key=key, limit=100, include_docs=True):
        doc = row.doc
        doc['references'] = doc.get('references', '')
        audit.append(fix_timestamps(doc))
    audit.sort(key=itemgetter('created_at'), reverse=True)
    return audit
    

def fix_timestamp(value):
    """Converts a single string timestamp to a datetime object in the local timezone.
    Timestamp is assumed to be UTC.
    """
    if not value:
        return value
    value = value.split('.')[0]
    if len(value) == 17:
        # bug in legacy records: 20091015T00222559
        value = value[:9] + value[11:]
    if not value.endswith('Z'):
        value = value + 'Z'
    # Would be better to use something mature like
    # http://pytz.sourceforge.net/
    value = value.replace('Z', 'UTC')
    if '-' not in value:
        try:
            dtime = datetime.datetime.strptime(value, '%Y%m%dT%H%M%S%Z')
        except ValueError:
            raise
    else:
        dtime = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%Z')
    secs = calendar.timegm(dtime.timetuple())

    return datetime.datetime(*time.localtime(secs)[0:6])


def fix_timestamps(doc):
    """Converts list of strings, which may contain a timestamps string.
    only keys ending with "_at" will be converted to datetime objects in the local timezone.
    Timestamps are assumed to be UTC.
    """
    
    for key, value in doc.items():
        if key.endswith('_at'):
            doc[key] = fix_timestamp(value)
    return doc
    

def utc_to_local(timestamp):
    """Convert UTC to the local timezone"""
    secs = calendar.timegm(timestamp)
    return time.localtime(secs)
    

def e2string(data):
    """Turn an Erlang String into a Python string."""
    # if we got a list of numbers turn it into a string
    if data and data[0] and isinstance(data[0], int):
        return ''.join([chr(x) for x in data])
    if data == []:
        return ''
    return data


def _get_data_from_kernel(path):
    """Return a dict with data from the kernel, gotten from SERVER/path.

    It does a GET request, receives json, and decodes this for you.
    """
    httpconn = httplib2.Http()
    resp, content = httpconn.request(KERNELURL + '/%s' % path, 'GET')
    if resp.status == 200:
        return json.loads(content)
    elif resp.status == 404:
        return None
    else:
        raise RuntimeError("Can't get reply from kernel, Status: %s, Body: %s" % (resp.status, content))


def _post_data_to_kernel(path, data):
    """Send a data dict to the kernel. It encodes this as json for you.
    Return a dict with data from the kernel, gotten from SERVER/path.

    It does a POST request, if there is a reply, it decodes the json for you.
    """
    encoded_data = json.dumps(data)

    httpconn = httplib2.Http()
    resp, content = httpconn.request(KERNELURL + '/%s' % path, 'POST', body=encoded_data)

    if resp.status == 201 or resp.status == 200:
        return json.loads(content)
    elif resp.status in [403, 404]: # FIXME: Maybe we need a more fine grained error handling?
        return None
    else:
        raise RuntimeError("Can't get reply from kernel, Status: %s, Body: %s" % (resp.status, content))


def _send_delete_to_kernel(path, data):
    """Send a DELETE request to the kernel."""
    httpconn = httplib2.Http()
    resp, content = httpconn.request(KERNELURL + '/%s' % path, 'DELETE', data)
    if resp['status'] == 204:
        return content
    elif resp['status'] == 404:
        return None
    else:
        raise RuntimeError("Can't get reply from kernel, Status: %s, Body: %s" % (resp.status, content))


## API

def get_abc():
    """Get abc classification of warehouse contents based on picks in the last 45 days.
    
    Keep in mind that products not picked in the last 45 days will not appear here.

    Return value is a dictionary w/ keys 'a', 'b', 'c'.
    The value for every of those keys is a list of pairs (artnrs, quantity).

    >>> myplfrontend.kernelapi.get_abc()
    {'a': [[532, '76666'],
       [478, '76686'],
       [454, '76650'],
       [218, '76676'],
        ...]
     'b': [[78, '14705'],
       [70, '10302'],
       [68, '14555'],
       [67, '12031/01'],
       ...]
     'c': [[29, '12113'],
       [29, '10148'],
       [29, '10106/01'],
       [28, '76010'],
       ...
       ]}
    """
    return _get_data_from_kernel('abc')


def get_article_list():
    """Gibt eine Liste aller Artikelnummer im Kernel zurück.

    >>> myplfrontend.kernelapi.get_article_list()
    ['01020', '01023', '10008', ..., 'WK84020']
    
    """
    return _get_data_from_kernel('product')
    

def get_article(artnr):
    """Liefert informationen zu einem Artikel im Kernel.

    >>> myplfrontend.kernelapi.get_article('01020'))
    {'artnr': '01020',
     'muis': ['340059981001348267', '340059981001351939', '340059981001350925',
              '340059981002392177', '340059981002392184', '340059981001359928'],
     'full_quantity': 104,
     'pick_quantity': 0,
     'available_quantity': 104,
     'movement_quantity': 0}
    
    """
    return _get_data_from_kernel('product/%s' % artnr)
    

def get_article_audit(artnr):
    """Get audit information for an article.

    >>> myplfrontend.kernelapi.get_article_audit(artnr)
    [{'_id': '01020-a1252308278.201882',
      '_rev': '2-e50b5cbf73d4440a26b84e105ea86972',
      'created_at': datetime.datetime(2009, 9, 7, 9, 24, 38),
      'description': 'Pick auf 340059981001094393',
      'mui': '340059981001094393',
      'product': '01020',
      'quantity': -2,
      'ref': '',
      'transaction': 'P08055535',
      'type': 'articleaudit'},
     {'_id': '01020-a1246254005.684696',
      '_rev': '2-998a3cccfdb6016a6928b3489adbca5d',
      ...},
      ...]
    
    """
    server = couchdb.client.Server(COUCHSERVER)
    tmp_audit = server['mypl_audit'].view('selection/articleaudit',
                                          descending=True, key=artnr, limit=1000, include_docs=True)
    audit = []
    for entry in tmp_audit:
        audit.append(fix_timestamps(dict(entry.doc)))
    return audit
    

def get_movements_list():
    """Liefert eine Liste aller nicht erledigten Movements.

    >>> myplfrontend.kernelapi.get_movements_list()
    ['mb08546054', 'mr08548916', 'mr08548928']
    
    """
    return _get_data_from_kernel("movement")
    

def get_movement(movementid):
    """Liefert Informationen zu einem einzelnen - möglicherweise auch erledigten - Movement.

    >>> myplfrontend.kernelapi.get_movement(movementid)
    {'archived': False,
     'artnr': '84039',
     'created_at': datetime.datetime(2009, 11, 9, 7, 20, 58),
     'from_location': 'EINLAG',
     'menge': 72,
     'mui': '340059981002585579',
     'oid': 'mb08546054',
     'status': 'open',
     'to_location': '163002'}
    
    """
    movement = _get_data_from_kernel('movement/%s' % movementid)
    if movement:
        movement['archived'] = False
    else:
        # Movement aus dem Archiv holen
        server = couchdb.client.Server(COUCHSERVER)
        movement = server['mypl_archive'].view('selection/movements', key=movementid, limit=1, include_docs=True)
        if not movement:
            return None
        movement = list(movement)[0].doc # without conversion to list integer indexes don't work
        # fix fields in legacy records
        changed = False
        if 'artnr' not in movement:
            changed, movement['artnr'] = True, movement.get('product', '')
        if 'interne_umlagerung' not in movement:
            if 'mypl_notify_requestracker' in movement.get('prop', {}):
                changed, movement['interne_umlagerung'] = True, movement.get('prop', {}).get('mypl_notify_requestracker', False)
            else:
                changed, movement['interne_umlagerung'] = True, False
        if 'to_location' not in movement:
            changed, movement['to_location'] = True, movement.get('prop', {}).get('to_location', '')
        if 'from_location' not in movement:
            changed, movement['from_location'] = True, movement.get('prop', {}).get('from_location', '')
        if 'status' not in movement:
            changed, movement['status'] = True, 'archived'
        #'attributes': {'committed_at': '20081210T00071056.295023', 
        #'kernel_provisioninglist_id': 'p06405646', 
        #'kernel_published_at': '20081210T00061028.000000'}, 
        if changed:
            try:
                server['mypl_archive'][movement.id] = movement
            except couchdb.client.ResourceConflict:
                pass # try next time
        
        movement['archived'] = True
    movement = fix_timestamps(movement)
    return dict(movement) #this is to convert a couchdb objet into a real dict
    

def get_picks_list():
    """Liefert eine Liste aller nicht erledigten Picks.

    >>> myplfrontend.kernelapi.get_picks_list()
    ['P08548169', 'P08548153']
    
    """
    return _get_data_from_kernel("pick")
    

def get_pick(pickid):
    """Liefert Informationen zu einem einzelnen - möglicherweise auch erledigten - Pick.
    
    from kernelE:
    >>> myplfrontend.kernelapi.get_pick(pickid)
    {'archived': False,
     'artnr': '57104',
     'created_at': datetime.datetime(2009, 11, 9, 10, 39, 16),
     'from_location': '172601',
     'from_unit': '340059981002438684',
     'kernel_kommiauftrag_id': '3099300',
     'kernel_kommischein_id': 'p08548182',
     'kernel_provisioninglist_id': 'p08548182',
     'kernel_published_at': datetime.datetime(2009, 11, 9, 11, 37, 3),
     'menge': 10,
     'oid': 'P08548169',
     'status': 'open'}
    
    from archive:
    >>> myplfrontend.kernelapi.get_pick(pickid)
    {'_id': 'P00149533',
     '_rev': '3-9c54fef0ab271bab56beecb87d37092b',
     'archived': True,
     'archived_at': datetime.datetime(2007, 12, 11, 0, 53, 58),
     'artnr': '14613/01',
     'created_at': datetime.datetime(2007, 12, 7, 7, 5, 25),
     'from_unit': '340059981000022823',
     'kernel_provisioninglist_id': '',
     'menge': 2,
     'mui': '340059981000022823',
     'oid': 'P00149533',
     'product': '14613/01',
     'prop': {'d': True, 'e': True, 'f': True, 'i': True, 'n': True, 'u': True},
     'provpipeline_id': '',
     'quantity': 2,
     'status': 'archived',
     'transaction': 'commit_pick',
     'type': 'pick'}
    

    """
    pick = _get_data_from_kernel("pick/%s" % pickid)
    if pick:
        pick['archived'] = False
    else:
        # Pick aus dem Archiv holen
        server = couchdb.client.Server(COUCHSERVER)
        pick = server['mypl_archive'].view('selection/picks', key=pickid, limit=1, include_docs=True)
        if not pick:
            return None
        pick = list(pick)[0].doc # without conversion to list integer indexes don't work
        # fix fields in legacy records
        changed = False
        if 'artnr' not in pick:
            changed, pick['artnr'] = True, pick.get('product', '')
        if 'menge' not in pick:
            changed, pick['menge'] = True, pick.get('quantity', '')
        if 'from_unit' not in pick:
            changed, pick['from_unit'] = True, pick.get('mui', '')
        if 'status' not in pick:
            changed, pick['status'] = True, 'archived'
        if 'kernel_provisioninglist_id' not in pick:
            changed, pick['kernel_provisioninglist_id'] = True, pick.get('attributes', {}).get('kernel_provisioninglist_id', '')
        if 'provpipeline_id' not in pick:
            changed, pick['provpipeline_id'] = True, pick.get('prop', {}).get('provpipeline_id', '')
        #'attributes': {'committed_at': '20081210T00071056.295023', 
        #'kernel_provisioninglist_id': 'p06405646', 
        #'kernel_published_at': '20081210T00061028.000000'}, 
        if changed:
            try:
                server['mypl_archive'][pick.id] = pick
            except couchdb.client.ResourceConflict:
                pass # try next time
        
        pick['archived'] = True
    
    pick = fix_timestamps(pick)
    return dict(pick)
    

def get_kommiauftrag_list():
    """Liefert eine Liste aller nicht erledigten Kommiaufträge.

    >>> myplfrontend.kernelapi.get_kommiauftrag_list()
    ['3099279',
     '3099292',
     '3099302',
     '3099214',
     '3099215',
     ...]

    """
    return _get_data_from_kernel('kommiauftrag')
    

def get_kommiauftrag(kommiauftragnr):
    """Liefert Informationen zu einem einzelnen - möglicherweise auch erledigten - Kommiauftrag.

    from kernelE:
    >>> myplfrontend.kernelapi.get_kommiauftrag(kommiauftragnr)
    {'anbruch': False,
     'art': 'A',
     'auftragsnr': '1093439',
     'auftragsnummer': '1093439',
     'fixtermin': False,
     'gewicht': 2000,
     'info_kunde': '',
     'kep': True,
     'kernel_customer': [49, 50, 51, 57, 54],
     'kernel_enqueued_at': datetime.datetime(2009, 11, 9, 0, 58, 27),
     'kommiauftragsnr': '3099279',
     'kundenname': 'BVG E. N-Hollenberg Baustoff- vertriebsges. mbH & Co. KG',
     'kundennr': '12396',
     'land': 'DE',
     'liefertermin': '2009-11-10',
     'liefertermin_ab': '2009-11-10',
     'orderlines': [{'artnr': '65171',
                     'auftragsposition': 1,
                     'gewicht': 0,
                     'menge': 1,
                     'posnr': 1}],
     'orderlines_count': 1,
     'paletten': 0.01,
     'plz': '49152',
     'priority': 2,
     'provisioninglists': [],
     'shouldprocess': 'yes',
     'status': 'new',
     'tries': 0,
     'versandpaletten': 0.01,
     'versandtermin': '2009-11-09',
     'versandtermin_ab': '2009-11-09',
     'volumen': 10.331}

    from archive
    >>> myplfrontend.kernelapi.get_kommiauftrag(kommiauftragnr)
    {'_id': '930613',
     '_rev': '3-ec028554a5b088a6962df5527fb8a618',
     'archived': True,
     'archived_at': datetime.datetime(2009, 1, 18, 21, 15, 49),
     'archived_by': 'cleanup',
     'attributes': {'auftragsnummer': '648204',
                    'commited_at': '20090118T00201549.741895',
                    'kernel_customer': '50402',
                    'kernel_enqueued_at': '20071206T00205116.000000',
                    'liefertermin': '2007-11-27',
                    'volume': 0.0,
                    'weigth': 0},
     'id': '930613',
     'oid': '930613',
     'orderlines': [[10, '14613/01', {'auftragsposition': 1, 'gewicht': 0}],
                    [4, '14695', {'auftragsposition': 2, 'gewicht': 0}],
                    [10, '14801', {'auftragsposition': 3, 'gewicht': 0}]],
     'orderlines_count': 3,
     'priority': 5,
     'provisioninglists': ['p00149579', 'r00149567'],
     'status': 'provisioned',
     'tries': 0,
     'type': 'provpipeline'}

    """
    # kommiauftrag aus dem Kernel holen
    kommiauftrag = _get_data_from_kernel('kommiauftrag/%s' % kommiauftragnr)
    if not kommiauftrag:
        # kommiauftrag aus dem Archiv holen
        server = couchdb.client.Server(COUCHSERVER)
        db = server['mypl_archive']
        # TODO: time out and retry with stale=ok & include_docs ?
        # see http://wiki.apache.org/couchdb/HTTP_view_API
        raw_reply = db.view('selection/kommiauftraege', key=kommiauftragnr, limit=1)
        for doc in [db[x.id] for x in raw_reply if x.key.startswith(kommiauftragnr)]:
            kommiauftrag = doc
        new_orderlines = []
        for orderline in kommiauftrag.get('orderlines', []):
            if isinstance(orderline, list):
                menge, artnr, attributes = orderline
                new_orderline = {'menge': menge, 'artnr': artnr}
                new_orderline.update(attributes)
            new_orderlines.append(orderline)
        kommiauftrag['orderlines'] = new_orderlines
        kommiauftrag['archived'] = True
        
        # fix legacy records
        changed = False
        if 'provisioninglists' in kommiauftrag:
            provisioninglists = []
            for kommischein_id in kommiauftrag.get('provisioninglists', []):
                provisioninglists.append(e2string(kommischein_id))
            if kommiauftrag['provisioninglists'] != provisioninglists:
                changed = True
            kommiauftrag['provisioninglists'] = provisioninglists
        if changed:
            try:
                server['mypl_archive'][kommiauftragnr] = kommiauftrag
            except couchdb.client.ResourceConflict:
                pass # try next time

    kommiauftrag['orderlines_count'] = len(kommiauftrag['orderlines'])
    
    kommiauftrag = fix_timestamps(kommiauftrag)
    return dict(kommiauftrag)


def set_kommiauftrag_priority(kommiauftragnr, explanation, priority):
    """Changes the priority of a Kommiauftrag."""
    return _post_data_to_kernel("kommiauftrag/%s/priority" % kommiauftragnr,
                                data=dict(priority=priority, explanation=explanation))


def get_kommischein_list():
    """Liefert eine Liste aller nicht erledigten Kommischeine.

    >>> myplfrontend.kernelapi.get_kommischein_list()
    ['r08549072']
    
    """
    return _get_data_from_kernel('kommischein')


def get_kommischein(kommischeinnr):
    """Liefert Details zu einem Kommischein.

    Die Informationen werden entweder aus dem Kernel, oder aus dem Archiv im CouchDB genommen.

    from archive:
    >>> myplfrontend.kernelapi.get_kommischein('p00149579')
    {'_id': 'p00149579-R1232271323.735974p00149579',
     '_rev': '2-7e378c9a311abc784e356c42eee71da7',
     'archived_at': datetime.datetime(2009, 1, 18, 10, 35, 23),
     'archived_by': 'cleanup',
     'attributes': {'auftragsnummer': '648204',
                    'commited_at': '20090118T00093523.735268',
                    'kernel_customer': '50402',
                    'kernel_enqueued_at': '20071206T00205116.000000',
                    'liefertermin': '2007-11-27',
                    'parts': 2},
     'created_at': datetime.datetime(2008, 1, 1, 1, 0),
     'destination': 'AUSLAG',
     'id': 'p00149579',
     'oid': 'p00149579',
     'provisionings': ['P00149533', 'P00149546', 'P00149551'],
     'provpipeline_id': '930613',
     'status': 'provisioned',
     'type': 'picklist'}

    from kernelE:
    >>> myplfrontend.kernelapi.get_kommischein(kommischeinnr)
    {'anbruch': True,
     'created_at': '2009-11-10T09:26:09.000000Z',
     'destination': 'AUSLAG',
     'export_packages': 2.5,
     'id': 'p08556432',
     'paletten': 0.2583333333333333,
     'parts': 1,
     'provisioning_ids': ['P08556318',
                          'P08556325',
                          'P08556339',
                          'P08556341',
                          'P08556356',
                          'P08556360',
                          'P08556373',
                          'P08556387',
                          'P08556394',
                          'P08556409',
                          'P08556413',
                          'P08556421'],
     'provpipeline_id': '3099579',
     'status': 'new',
     'type': 'picklist',
     'volume': 262.19200000000001,
     'weight': 24020}
    

    """
    kommischein = _get_data_from_kernel('kommischein/%s' % kommischeinnr)
    if not kommischein:
        kommischein = {}
        # kommiauftrag aus dem Archiv holen
        server = couchdb.client.Server(COUCHSERVER)
        db = server['mypl_archive']
        # TODO: time out and retry with stale=ok
        # see http://wiki.apache.org/couchdb/HTTP_view_API
        for row in db.view('selection/kommischeine', key=kommischeinnr, limit=1, include_docs=True):
            kommischein = dict(fix_timestamps(row.doc))
    kommischein.update({'id': kommischeinnr})
    return kommischein
    

def get_units_list():
    """Liefert eine Liste aller im Lager befindlichen Units.

    >>> myplfrontend.kernelapi.get_kommiauftrag_list()
    ['3099279',
     '3099292',
     '3099302',
     '3099214',
     '3099215',
     '3099288',
     '3099219',
     ...]
    
    """
    return _get_data_from_kernel('unit')
    

def get_unit(mui):
    """Return detailed information about a unit.
    
    Information is taken from couchdb archive, if nothing found in kernel

    >>> import myplfrontend.kernelapi
    >>> myplfrontend.kernelapi.get_unit(340059981002564246)
    {'artnr': '71418',
     'created_at': '2009-10-23T05:40:38.221078Z',
     'height': 1650,
     'id': '340059981002564246',
     'komminr': '3097516',
     'location': '132203',
     'menge': 8,
     'movements': [],
     'mui': '340059981002564246',
     'pick_quantity': 0,
     'picks': [],
     'source': 'umlagerung'}
    """
    unit = _get_data_from_kernel('unit/%s' % mui)
    if unit:
        unit['archived'] = False
    else:
        # Unit aus dem Archiv holen
        server = couchdb.client.Server(COUCHSERVER)
        units = server['mypl_archive'].view('selection/units', key=mui, limit=1, include_docs=True)
        if units:
            unit = list(units)[0].doc # without conversion to list integer indexes don't work
            unit['archived'] = True
        else:
            return {}
    return fix_timestamps(dict(unit))
    

def set_unit_height(mui, height):
    """Set the height of a pallet and return the pallet data."""
    return _post_data_to_kernel("unit/%s" % mui, {'height': height})


def get_location_list():
    """Returns the full list of locations in the warehouse.
    
    >>> myplfrontend.kernelapi.get_location_list()
    ['011301', '011302', '011303', '011401', '011402', '011403', '011501', '011502', '011503', ...]

    """
    return _get_data_from_kernel('location')


def get_location(location):
    """Return detailed data for location from kernel.

    >>> myplfrontend.kernelapi.get_location(location)
    {'allocated_by': ['340059981002483097'],
     'floorlevel': 'true',
     'height': 2100,
     'info': '',
     'name': '011301',
     'preference': 5,
     'reserved_for': []}
        
    """
    return _get_data_from_kernel('location/%s' % location)


def get_statistics():
    """Return statistics about the kernel.

    >>> myplfrontend.kernelapi.get_statistics()
    {'empty_pickable_locations': 46,
     'multi_floorunits': 144,
     'oldest_movement': '2009-11-09T06:20:58.173399Z',
     'oldest_pick': '',
     'open_movements': 4,
     'open_picks': 0,
     'products': 757,
     'provlists_prepared': 0,
     'provpipeline_articles': 2,
     'provpipeline_new': 43,
     'provpipeline_processing': 1,
     'requesstracker_entries': 0,
     'units': 2365}

    """
    return _get_data_from_kernel("statistics")


def kommiauftrag_nullen(kommiauftragnr, username, begruendung):
    """'Nullen' eines Kommisionierauftrags."""
    data = u'Kommiauftrag durch %s genullt. Begruendung: %s' % (username, begruendung)
    content = _send_delete_to_kernel('kommiauftrag/%s' % kommiauftragnr, data)
    return content


def movement_stornieren(oid):
    """Cancel a movement."""
    return _send_delete_to_kernel('movement/%s' % oid)


def find_provisioning_candidates(menge, artnr):
    """Hiermit kann ein Komissioniervorschlag für eine bestimmte Menge eines Artikels erstellt werden.

    Falls keine passenden Mengen gefunden werden können - z.B. will erst noch eine Umlagerung durchgeführt
    werden muss - wird der Statuscode None zurückgegeben. Sollte das Lager weniger Bestand als gefordert haben,
    wird ein RuntimeError (Statuscode 403) zurückgegeben.

    >>> myplfrontend.kernelapi.find_provisioning_candidates(1, 10147)
    {"retrievals":[],"picks":[{"menge":1,"mui":"340059981002563591"}]}

    """
    return _post_data_to_kernel("product/%s" % artnr, data=dict(menge=menge))


def requesttracker():
    """Zeigt Informationen über den RequestTracker an.

    Der Requestracker koordiniert, welche Palettne herunter gelagert werden sollen.
   
    """
    return _get_data_from_kernel("requesttracker")
