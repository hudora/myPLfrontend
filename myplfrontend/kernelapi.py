#!/usr/bin/env python
# encoding: utf-8
"""
kernelapi.py

Created by Maximillian Dornseif on 2009-10-16.
Copyright (c) 2009 HUDORA. All rights reserved.
"""


from operator import itemgetter
import calendar
import couchdb
import datetime
import httplib2
import simplejson as json
import time


COUCHSERVER = "http://couchdb.local.hudora.biz:5984"


def get_article_audit(artnr):
    server = couchdb.client.Server(COUCHSERVER)
    tmp_audit = server['mypl_audit'].view('selection/articleaudit',
                                          descending=True, key=artnr, limit=1000, include_docs=True)
    audit = []
    for entry in tmp_audit:
        audit.append(fix_timestamps(dict(entry.doc)))
    return audit
    

def get_movements_list():
    """Liefert eine Liste aller nicht erledigten Movements."""
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/movement', 'GET')
    if resp.status == 200:
        return json.loads(content)
    else:
        raise RuntimeError("can't get reply from kernel")
    

def get_movement(movementid):
    """Liefert Informationen zu einem einzelnen - möglicherweise auch erledigten - Movement."""
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/movement/%s' % movementid, 'GET')
    if resp.status == 200:
        movement = json.loads(content)
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
    return dict(movement)
    

def get_picks_list():
    """Liefert eine Liste aller nicht erledigten Picks."""
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/pick', 'GET')
    if resp.status == 200:
        return json.loads(content)
    else:
        raise RuntimeError("can't get reply from kernel")
    

def get_pick(pickid):
    """Liefert Informationen zu einem einzelnen - möglicherweise auch erledigten - Pick."""
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/pick/%s' % pickid, 'GET')
    if resp.status == 200:
        pick = json.loads(content)
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
    """Liefert eine Liste aller nicht erledigten Kommiaufträge."""
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/kommiauftrag', 'GET')
    if resp.status == 200:
        return json.loads(content)
    else:
        raise RuntimeError("can't get reply from kernel")
    

def get_kommiauftrag(kommiauftragnr):
    """Liefert Informationen zu einem einzelnen - möglicherweise auch erledigten - Kommiauftrag."""
    kommiauftrag = {}
    
    # kommiauftrag aus dem Kernel holen
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/kommiauftrag/%s' % kommiauftragnr, 'GET')
    if resp.status == 200:
        kommiauftrag = json.loads(content)
        kommiauftrag['archived'] = False
    else:
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
                server['mypl_archive'][kommiauftrag.id] = kommiauftrag
            except couchdb.client.ResourceConflict:
                pass # try next time

    kommiauftrag['orderlines_count'] = len(kommiauftrag['orderlines'])
    
    kommiauftrag = fix_timestamps(kommiauftrag)
    return dict(kommiauftrag)
    

def get_units_list():
    """Liefert eine Liste aller im Lager befindlichen Units."""
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/unit', 'GET')
    if resp.status == 200:
        return json.loads(content)
    else:
        raise RuntimeError("can't get reply from kernel")
    

def get_unit(mui):
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/unit/%s' % mui, 'GET')
    if resp.status == 200:
        unit = json.loads(content)
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
    

def get_article_list():
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/product', 'GET')
    if resp.status == 200:
        return json.loads(content)
    else:
        raise RuntimeError("can't get reply from kernel")
    

def get_article(artnr):
    httpconn = httplib2.Http()
    resp, content = httpconn.request('http://hurricane.local.hudora.biz:8000/product/%s' % artnr, 'GET')
    if resp.status == 200:
        return json.loads(content)
    else:
        raise RuntimeError("can't get reply from kernel")
    

def fix_timestamps(doc):
    """Converts string timestamps to datetime objectssss in the local timezone.
    Timestamps are assumed to be UTC."""
    
    for key, value in doc.items():
        if key.endswith('_at'):
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
            doc[key] = datetime.datetime(*time.localtime(secs)[0:6])
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
    else:
        raise RuntimeError("can't get reply from kernel")


def get_location(location):
    """Return data for location from kernel."""
    return _get_data_from_kernel("location/%s" % location)


def get_statistics():
    """Return statistics about the kernel."""
    return _get_data_from_kernel("statistics")
