#!/usr/bin/env python
# encoding: utf-8
"""
test.py

Created by Lars Ronge & Maximillian Dornseif on 2007-12-05.
Copyright (c) 2007 HUDORA. All rights reserved.
"""

import unittest
from django.test.client import Client
from django.test import TestCase


class SimpleTests(TestCase):
    """Test basic functionality"""
    
    fixtures = ['fixtures/testusers.json']
    
    def setUp(self):
        """Initial Client for further Tests."""
        self.client = Client()
        self.client.login(username='testclient_staff', password='password')
    
    def test_index(self):
        """Test that index page works"""
        response = self.client.get('/myplfrontend/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'myplfrontend/index.html')
    
    def test_info(self):
        """Test that info page works"""
        response = self.client.get('/myplfrontend/info/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'myplfrontend/lager_info.html')


if __name__ == '__main__':
    unittest.main()
