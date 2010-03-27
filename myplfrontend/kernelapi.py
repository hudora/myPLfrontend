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
import couchdb.client
import datetime
import httplib2
import simplejson as json
import time


COUCHSERVER = "http://couchdb.local.hudora.biz:5984"
KERNELURL = "http://hurricane.local.hudora.biz:8000"


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



class Kerneladapter(object):
    """Kerneladapter for KernelE"""
    
    def __init__(self, kernel="http://hurricane.local.hudora.biz:8000",
                       couchdbserver="http://couchdb.local.hudora.biz:5984"):
        self.kernel = kernel
        self.couchdbserver = self.couchdbserver

    def _get(self, path):
        """
        Funktion, um Daten per HTTP GET vom Kernel anzufordern.
        
        Die Daten vom Kernel werden als JSON dekodiert,
        der Rückgabewert ist ein dict
        """
        
        conn = httplib2.Http()
        response, content = conn.request(self.kernel + '/%s' % path, 'GET')
        if response.status == 200:
            return json.loads(content)
        elif response.status == 404:
            return None
        else:
            raise RuntimeError("Can't get reply from kernel, Status: %s, Body: %s" % (response.status, content))
    
    def _post(self, path, **kwargs):
        """
        Funktion, um Daten per HTTP POST an den Kernel zu übertragen.
        
        Die Daten werden als JSON kodiert.
        Der Rückgabewert ist ein dict.
        """
        
        encoded_data = json.dumps(kwargs)

        conn = httplib2.Http()
        response, content = conn.request(self.kernel + '/%s' % path, 'POST', body=encoded_data)

        if response.status in [200, 201]:
            return json.loads(content)
        elif response.status in [403, 404]:
            return None
        else:
            raise RuntimeError("Can't get reply from kernel, Status: %s, Body: %s" % (response.status, content))


    def _delete(self, path, data):
        """
        Send a DELETE request to the kernel.
        """
        
        conn = httplib2.Http()
        response, content = conn.request(self.kernel + '/%s' % path, 'DELETE', data)
        if response.status == 204:
            return content
        elif response.status == 404:
            return None
        else:
            raise RuntimeError("Can't get reply from kernel, Status: %s, Body: %s" % (response.status, content))

    def _couch(self, database, view, **kwargs):
        """Get document from CouchDB"""
        
        if not 'include_docs' in kwargs:
            kwargs['include_docs'] = True
        server = couchdb.client.Server(self.couchdbserver)
        return server[database].view(view, **kwargs)

    def _updatecouch(self, database, doc_id, document):
        """Update document in CouchDB"""
        
        server = couchdb.client.Server(self.couchdbserver)
        try:
            server[database][doc_id] = document
        except couchdb.client.ResourceConflict:
            pass
    
    def get_abc(self):
        """ABC-Klassifizierung"""
        return self._get('abc')

    def get_article_list(self):
        """Gibt eine Liste aller Artikelnummer im Kernel zurück.

        >>> myplfrontend.kernelapi.get_article_list()
        ['01020', '01023', '10008', ..., 'WK84020']
        """
        return self._get('product')

    def get_article(self, artnr):
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
        return self._get('product/%s' % artnr)
    
    def get_kommiauftrag_list(self):
        """
        Liefert eine Liste aller nicht erledigten Kommiaufträge.

        >>> myplfrontend.kernelapi.get_kommiauftrag_list()
        ['3099279',
         '3099292',
         '3099302',
         '3099214',
         '3099215',
         ...]
        """
        return self._get('kommiauftrag')
    
    def get_movements_list(self):
        """Liefert eine Liste aller nicht erledigten Movements.

        >>> myplfrontend.kernelapi.get_movements_list()
        ['mb08546054', 'mr08548916', 'mr08548928']

        """
        return self._get("movement")
    
    def get_picks_list(self):
        """Liefert eine Liste aller nicht erledigten Picks.

        >>> myplfrontend.kernelapi.get_picks_list()
        ['P08548169', 'P08548153']

        """
        return self._get("pick")
    
    def get_kommischein_list(self):
        """Liefert eine Liste aller nicht erledigten Kommischeine.

        >>> myplfrontend.kernelapi.get_kommischein_list()
        ['r08549072']

        """
        return self._get('kommischein')

    def get_units_list(self):
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
        return self._get('unit')
    
    def get_location_list(self):
        """Returns the full list of locations in the warehouse.

        >>> myplfrontend.kernelapi.get_location_list()
        ['011301', '011302', '011303', '011401', '011402', '011403', '011501', '011502', '011503', ...]

        """
        return self._get('location')

    def requesttracker(self):
        """Zeigt Informationen über den RequestTracker an.

        Der Requestracker koordiniert, welche Palettne herunter gelagert werden sollen.
        """
        return self._get("requesttracker")
    
    def get_statistics(self):
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
        return self._get("statistics")
    
    def get_location(self, location):
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
        
        return self._get('location/%s' % location)
    
    ### P O S T
    
    def get_movementlist(self):
        """Get movement (or retrieval)"""
        movement = self._post('/movement')
        return movement
    
    def commit_movement(self, movementid):
        """Movement zurückmelden"""
        return self._post('/movement/%s' % movementid)
    
    def set_kommiauftrag_priority(self, kommiauftragnr, begruendung, priority):
        """Changes the priority of a Kommiauftrag."""
        return self._post("kommiauftrag/%s/priority" % kommiauftragnr,
                         priority=priority, explanation=begruendung)
    
    def set_unit_height(self, mui, height):
        """Set the height of a pallet and return the pallet data."""
        return self._post("unit/%s" % mui, height=height)
    
    def find_provisioning_candidates(self, menge, artnr):
        """Hiermit kann ein Komissioniervorschlag für eine bestimmte Menge eines Artikels erstellt werden.

        Falls keine passenden Mengen gefunden werden können - z.B. will erst noch eine Umlagerung durchgeführt
        werden muss - wird der Statuscode None zurückgegeben. Sollte das Lager weniger Bestand als gefordert
        haben, wird ein RuntimeError (Statuscode 403) zurückgegeben.

        >>> myplfrontend.kernelapi.find_provisioning_candidates(1, 10147)
        {"retrievals":[],"picks":[{"menge":1,"mui":"340059981002563591"}]}

        """
        return self._post("product/%s" % artnr, menge=menge)
    
    ### D E L E T E ###
    def kommiauftrag_nullen(self, kommiauftragnr, username, begruendung):
        """'Nullen' eines Kommisionierauftrags"""
        data = u'Kommiauftrag durch %s genullt. Begruendung: %s' % (username, begruendung)
        content = self._delete('kommiauftrag/%s' % kommiauftragnr, data)
        return content

    def movement_stornieren(self, movementid, username, begruendung):
        """Cancel a movement."""
        data = u'Movement durch %s genullt. Begruendung: %s' % (username, begruendung)
        return self._delete('movement/%s' % movementid, data)

    ### C O U C H
    
    def get_article_audit(self, artnr):
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
        rows = self._couch('mypl_audit', 'selection/articleaudit', descending=True, key=artnr, limit=1000)
        return [fix_timestamps(dict(entry.doc)) for entry in rows]
    
    def get_audit(self, view, key):
        """Hole Audit-Informationen aus CouchDB"""
        audit = []
        rows = self._couch("mypl_audit", view, key=key, limit=100)
        for row in rows:
            row.doc.setdefault('references', '')
            audit.append(fix_timestamps(row.doc))
        return sorted(audit, key=itemgetter('created_at'), reverse=True)

    ### A R C H I V E D
    def get_unit(self, mui):
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
        unit = self._get('unit/%s' % mui)
        if unit:
            unit['archived'] = False
        else:
            units = self._couch('mypl_archive', 'selection/units', key=mui, limit=1)
            if units.total_rows == 0:
                unit = {}
            else:
                unit = fix_timestamps(dict(units.rows[0].doc))
                unit['archived'] = True
        return unit
    
    def get_kommischein(self, kommischeinnr):
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
                              'P08556421'],
         'provpipeline_id': '3099579',
         'status': 'new',
         'type': 'picklist',
         'volume': 262.19200000000001,
         'weight': 24020}
        """
        
        kommischein = self._get('kommischein/%s' % kommischeinnr)
        if not kommischein is None:
            kommischein['archived'] = False
        else:
            kommischeine = self._couch('mypl_archive', 'selection/kommischeine', key=kommischeinnr, limit=1)
            if kommischeine.total_rows == 0:
                return {}
            
            kommischein = kommischeine.rows[0].doc
            kommischein = fix_timestamps(dict(kommischein))
            kommischein['id'] = kommischeinnr
            kommischein['archived'] = True
        return kommischein

    def get_movement(self, movementid):
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
        movement = self._get('movement/%s' % movementid)
        if not movement is None:
            movement['archived'] = False
        else:
            movements = self._couch('mypl_archive', 'selection/movements', key=movementid, limit=1)
            if movements.total_rows == 0:
                return {}
            
            movement = movements.rows[0].doc
            
            # fix fields in legacy records
            changed = False
            if 'artnr' not in movement:
                changed, movement['artnr'] = True, movement.get('product', '')
            if 'interne_umlagerung' not in movement:
                if 'mypl_notify_requestracker' in movement.get('prop', {}):
                    changed, = True
                    movement['interne_umlagerung'] = movement.get('prop', {
                                                                  }).get('mypl_notify_requestracker', False)
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
                self._updatecouch('mypl_archive', movement.id, movement)

            movement['archived'] = True
            movement = fix_timestamps(dict(movement))
        return movement

    def get_pick(self, pickid):
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

        pick = self._get("pick/%s" % pickid)
        if not pick is None:
            pick['archived'] = False
        else:
            picks = self._couch('mypl_archive', 'selection/picks', key=pickid, limit=1)
            if picks.total_rows == 0:
                return {}
            pick = picks.rows[0].doc
            
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
                changed = True
                pick['kernel_provisioninglist_id'] = pick.get('attributes', {
                                                              }).get('kernel_provisioninglist_id', '')
            if 'provpipeline_id' not in pick:
                changed, pick['provpipeline_id'] = True, pick.get('prop', {}).get('provpipeline_id', '')
            #'attributes': {'committed_at': '20081210T00071056.295023',
            #'kernel_provisioninglist_id': 'p06405646',
            #'kernel_published_at': '20081210T00061028.000000'},
            if changed:
                self._updatecouch('mypl_archive', pick.id, pick)
            
            pick['archived'] = True
            pick = fix_timestamps(dict(pick))
        
        return pick

    def get_kommiauftrag(self, kommiauftragnr):
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
        
        kommiauftrag = self._get('kommiauftrag/%s' % kommiauftragnr)
        if not kommiauftrag is None:
            kommiauftrag['archived'] = False
        else:
            kommiauftraege = self._couch('mypl_archive', 'selection/kommiauftraege', key=kommiauftragnr, limit=1)
            if kommiauftraege.total_rows == 0:
                return {}
            
            kommiauftrag = kommiauftraege.rows[0].doc
            
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
                self._updatecouch('mypl_archive', kommiauftragnr, kommiauftrag)

            kommiauftrag['archived'] = True
            kommiauftrag = fix_timestamps(dict(kommiauftrag))

        kommiauftrag['orderlines_count'] = len(kommiauftrag['orderlines'])
        return kommiauftrag

