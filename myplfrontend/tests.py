#!/usr/bin/env python
# encoding: utf-8
"""
test.py

Created by LArs Ronge & Maximillian Dornseif on 2007-12-05.
Copyright (c) 2007 HUDORA. All rights reserved.
"""

import unittest
from django.test.client import Client
from django.test import TestCase

import myplfrontend.views


class SimpleTests(TestCase):
    """Test basic functionality"""
    
    fixtures = ['fixtures/testusers.json']
    
    def setUp(self):
        """Initial Client for further Tests."""
        self.client = Client()
        self.client.login(username='testclient_staff', password='password') 
    
    def test_index(self):
        """Test that index page works and is password protected."""
        response = self.client.get('/mypl/viewer/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'myplfrontend/index.html')
        unauthorizedClient = Client()
        response = unauthorizedClient.get('/mypl/viewer/')
        self.assertTemplateNotUsed(response, 'myplfrontend/index.html')
    
    def test_info(self):
        """Test that info page works and is password protected."""
        response = self.client.get('/mypl/viewer/info/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'myplfrontend/lager_info.html')
        unauthorizedClient = Client()
        response = unauthorizedClient.get('/mypl/viewer/info/')
        self.assertTemplateNotUsed(response, 'myplfrontend/lager_info.html')
        

class HelperFunctionTests(TestCase):
    def setUp(self):
        pass

    def test_get_locations(self):
        """Simple tests for the __get_locations() fnc.
        
        This is not bullet-proof, since we're only testing if the available and occupied locations
        are different. Here is no guarantee, that the collected locations are _all_ the locations from
        mypl."""
        available = myplfrontend.views.__get_locations(available=True)
        occupied = myplfrontend.views.__get_locations(available=False)
        self.failUnless(available != occupied)

        # I think, both sizes should never be zero, so test this too
        sz_a = len(available)
        self.assertTrue(sz_a != 0)
        sz_o = len(occupied)
        self.assertTrue(sz_o != 0)

        # check if there is no intersection (Schnittmenge) between both lists
        sz = sz_a + sz_o
        all = set(available+occupied)
        self.assertEqual(sz, len(all))
    
    def test_get_softm_articles(self):
        """Simple tests for the _get_softm_articles() fnc."""
        
        # FIXME
        # I have no better idea by now as to call this function and check that the list is not emtpy
        # and that all list entries (the dictionaries) have correct keys.
        # At least this assures that the function will not raise when it is called.
        articles = myplfrontend.views._get_softm_articles()
        self.assertNotEqual(len(articles), 0)
        for a in articles:
            self.assertTrue(a.has_key('artnr'))
            self.assertTrue(a.has_key('name'))
            self.assertTrue(a.has_key('full_quantity'))
            self.assertTrue(a.has_key('available_quantity'))
            self.assertTrue(a.has_key('pick_quantity'))
            self.assertTrue(a.has_key('movement_quantity'))
            self.assertTrue(a.has_key('buchbestand'))
        pass
    

if __name__ == '__main__':
    unittest.main()
