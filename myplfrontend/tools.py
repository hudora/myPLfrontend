#!/usr/bin/env python
# encoding: utf-8
"""
tools.py

Created by Lars Ronge on 2008-02-26.
Copyright (c) 2008 __MyCompanyName__. All rights reserved.
"""

import unittest


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
