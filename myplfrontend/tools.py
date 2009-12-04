#!/usr/bin/env python
# encoding: utf-8
"""
tools.py

Created by Lars Ronge on 2008-02-26.
Copyright (c) 2008 __MyCompanyName__. All rights reserved.
"""

import unittest
import husoftm.bestaende
import myplfrontend.kernelapi
import itertools
    

def find_softm_differences():
    """Find articles which have different quantities in myPL as their SoftM counterparts."""
    softmbestand = set(husoftm.bestaende.buchbestaende(lager=100).items())
    kernelbestand = set((artdict['artnr'], artdict['full_quantity']) for artdict in 
                        (myplfrontend.kernelapi.get_article(article) for article in myplfrontend.kernelapi.get_article_list()))
    difkernel2softm = kernelbestand.difference(softmbestand)
    difsoftm2kernel = softmbestand.difference(kernelbestand)
    artnrs = set(artnr for (artnr, mng) in itertools.chain(difkernel2softm, difsoftm2kernel))
    dictkernel2softm = dict(difkernel2softm)
    dictsoftm2kernel = dict(difsoftm2kernel)
    return [dict(artnr=artnr, softm_menge=dictsoftm2kernel.get(artnr), kernel_menge=dictkernel2softm.get(artnr))
            for artnr in artnrs]


def format_locname(locname):
    """Formats a location name nicely.

    >>> format_locname("010203")
    '01-02-03'
    >>> format_locname("AUSLAG")
    'AUSLAG'
    >>> format_locname("K20")
    'K20'
    """

    if len(locname) == 6 and str(locname).isdigit():
        return "%s-%s-%s" % (locname[:2], locname[2:4], locname[4:])
    return locname


def compare_locations(s_location, o_location):
    """Compares two Locations regarding the following rules:
    1st - Compare the aisles (two rows make up on aisle)
    2nd - Compare the rows
    
    >>> compare_locations("020501", "030201")
    1
    >>> compare_locations("020501", "030501")
    0
    >>> compare_locations("020301", "030501")
    -1
    >>> compare_locations("K10", "030201")
    -1
    >>> compare_locations("030201", "K11")
    1
    >>> compare_locations("K11", "K11")
    0
    """

    if not s_location.isdigit() and not o_location.isdigit():
        return 0

    if not s_location.isdigit():
        return -1
                               
    if not o_location.isdigit():
        return 1
                                                
    s_row = s_location[:2]
    s_aisle = 1 + (int(s_row) / 2)
    
    o_row = o_location[:2]
    o_aisle = 1 + (int(o_row) / 2)
    
    if int(s_aisle) > int(o_aisle):
        return 1
    elif int(s_aisle) < int(o_aisle):
        return -1
    
    s_column = s_location[2:4]
    o_column = o_location[2:4]
    
    if int(s_column) > int(o_column):
        return 1
    elif int(s_column) < int(o_column):
        return -1
    
    return 0


def sort_plaetze(items, key='location_from'):
    """Sortiert eine Menge von Lagerplätzen nach folgendem Kriterium:
    Reihen werden zu Gängen zusammengefasst, die Plätze der zu besuchenden Gänge werden abwechselnd
    auf- und absteigend sortiert. Siehe http://blogs.23.nu/disLEXiaDE/stories/15539/
    
    Paramter ist ein dictionary, dessen Schlüssel Lagerplätze nach dem Schema Reihe-Riegel-Ebene sind.
    Die Values sind beliebige Objekte.

    Als key wird der Methodenname bzw. der dictitionary Schlüssel vorgegeben, der den Platz repräsentiert.
    
    >>> sort_plaetze([{'location_from': '01-10-01'}, {'location_from': '02-12-01'}, {'location_from': '03-10-01'}, {'location_from': '03-15-01'}, {'location_from': 'EINLAG'}])
    [{'location_from': 'EINLAG'}, {'location_from': '01-10-01'}, {'location_from': '03-15-01'}, {'location_from': '02-12-01'}, {'location_from': '03-10-01'}]
    """
    
    tmp = dict()
    for item in items:
        location = getattr(item, key, None)
        if not location:
            location = item[key]
        location = location.replace("-", "")
        if not location.isdigit():
            location = "000000"

        row = location[:2]
        aisle = 1 + (int(row) / 2)

        tmp.setdefault(aisle, {}).setdefault(location, item)
        # if tmp.has_key(aisle):
        #     tmp[aisle][location] = item
        # else:
        #     tmp[aisle] = {location: item}

    all_items = []
    reverse = False

    for aisle in sorted(tmp.keys()):
        for key in sorted(tmp[aisle].keys(), key=lambda x: x[2:], reverse=reverse):
            all_items.append(tmp[aisle][key])

        # optimierung oder komplexisierng:
        # wenn reihe von letztem platz in gang n < (bzw. >) reihe von erstem platz in gang n+1:
        # kehre reihenfolge nicht um
        reverse = not reverse

    return all_items


def get_pickinfo_from_pipeline_data(pipeline_data):
    """Get Pickinfo from Pipeline data"""

    fieldnames = ('versandpaletten', 'volume', 'weigth', 'packstuecke', 'picks', 'orderlines_count', 'count')
    db = {}
    for typ1 in ['direktfahrt', 'kep', 'normal']:
        for typ2 in ['yes', 'maybe', 'no']:
            typ = "%s_%s" % (typ2, typ1)
            db[typ] = {}
            for name in fieldnames:
                db[typ][name] = 0

    for order in pipeline_data:
        shouldprocess = order['shouldprocess']
        direktfahrt = order.get('versandpaletten', 0) > 6
        order['direktfahrt'] = direktfahrt
        
        if direktfahrt:
            shippingkey = "%s_direktfahrt" % (shouldprocess)
        elif order.get('kep', False):
            shippingkey = "%s_kep" % (shouldprocess)
        else:
            shippingkey = "%s_normal" % (shouldprocess)
        if shippingkey not in db:
            db[shippingkey] = {}
        if not 'count' in db[shippingkey]:
            db[shippingkey]['count'] = 0
        db[shippingkey]['count'] += 1
        
        for name in fieldnames:
            if 'volume' not in name:
                db[shippingkey][name] += order.get(name, 0)
            else:
                db[shippingkey][name] += order.get(name, 0) / 1000.0

    for shippingkey in db:
        for name in db[shippingkey]:
            db[shippingkey][name] = int(db[shippingkey][name])
    return db


class toolsTests(unittest.TestCase):
    """Some tests for the tools-functionalities"""
    
    def setUp(self):
        pass

    def test_get_pickinfo_from_pipeline_data(self):
        """Tests the method get_pickinfo_from_pipeline_data"""
        pipeline_data = []
        pipeline_data.append({'shouldprocess': 'yes',
                              'versandpaletten': 2,
                              'volume': 1000.0,
                              'weigth': 100.0,
                              'packstuecke': 5,
                              'picks': 5,
                              'orderlines_count': 3,
                            })
        pipeline_data.append({'shouldprocess': 'yes',
                              'versandpaletten': 7,
                              'volume': 5555.0,
                              'weigth': 555.0,
                              'packstuecke': 155,
                              'picks': 165,
                              'orderlines_count': 145,
                            })
        pipeline_data.append({'shouldprocess': 'maybe',
                              'versandpaletten': 1,
                              'volume': 20.0,
                              'weigth': 2.0,
                              'packstuecke': 2,
                              'picks': 3,
                              'orderlines_count': 2,
                            })
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['maybe']['orderlines_count'], 2)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['maybe']['packstuecke'], 2)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['maybe']['picks'], 3)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['maybe']['versandpaletten'], 1)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['maybe']['volume'], 20.0)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['maybe']['weigth'], 2.0)

        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes']['orderlines_count'], 148)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes']['packstuecke'], 160)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes']['picks'], 170)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes']['versandpaletten'], 9)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes']['volume'], 6555.0)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes']['weigth'], 655.0)

        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes_normal']['orderlines_count'], 3)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes_normal']['packstuecke'], 5)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes_normal']['picks'], 5)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes_normal']['versandpaletten'], 2)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes_normal']['volume'], 1.0)
        self.assertEqual(get_pickinfo_from_pipeline_data(pipeline_data)['yes_normal']['weigth'], 100.0)


if __name__ == '__main__':
    unittest.main()
