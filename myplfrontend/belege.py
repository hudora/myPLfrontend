#!/usr/bin/env python
# encoding: utf-8
"""
belege.py - Create myPL related pdf documents 

Created by Maximillian Dornseif on 2007-12-13.
Copyright (c) 2007, 2009 HUDORA. All rights reserved.
"""

from myplfrontend.tools import format_locname, sort_plaetze
from pyjasper.client import JasperGenerator

import cs.masterdata.article
import cs.zwitscher
import datetime
import myplfrontend.kernelapi
import os
import xml.etree.ElementTree as ET


def _add_subelemententry(root, field, obj_dict):
    """Adds a new field to the given root element."""
    value = obj_dict.get(field)
    if not value:
        print 'debug: %s fehlt!' % field
        value = ""
    if 'location' in field.lower():
        value = format_locname(value)
    ET.SubElement(root, field).text = unicode(value)


class _ProvisioningGenerator(JasperGenerator):
    """Jasper-Generator for Provisioning-Documents (Kommischeine)."""

    def __init__(self):
        super(_ProvisioningGenerator, self).__init__()
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'reports', 'Provisioning.jrxml'))
        self.reportname = path
        self.xpath = '/provisionings/provisioning/provisioningposition'
        self.root = ET.Element('provisionings')

    def provisioning2xml(self, provisioning_id):
        """Generic functionality to create a XML file from kernelE's kommischein information."""

        provisioning_dict = myplfrontend.kernelapi.get_kommischein(provisioning_id)
        
        xmlroot = self.root
        xml_provisioning = ET.SubElement(xmlroot, 'provisioning')

        # neccessary data from kommischein
        for fieldname in ['provpipeline_id', 'id']:
            _add_subelemententry(xml_provisioning, fieldname, provisioning_dict)

        # FIXME This is special treatment for archived provisionings. Is there a need to process the archived?
        for fieldname in ['parts']:
            attr_dict = provisioning_dict.get('attributes', provisioning_dict)
            _add_subelemententry(xml_provisioning, fieldname, attr_dict)

        # data from kommiauftrag
        fields = ['liefertermin', 'kundennr', 'auftragsnummer']
        kommiauftrag = myplfrontend.kernelapi.get_kommiauftrag(provisioning_dict["provpipeline_id"])
        attr_dict = kommiauftrag.get('attributes', kommiauftrag)
        for fieldname in fields:
            _add_subelemententry(xml_provisioning, fieldname, attr_dict)

        # data from the kommischeins provisionings_ids
        weight_sum = 0
        volume_sum = 0

        # collect provisionings in a list of dictionaries -> for sorting
        provisionings = []
        # XXX: provisionings called provisioning_ids in kernel and provisionings in archive
        # FIXME: do we need archived provisionings?
        for provisioningid in provisioning_dict.get("provisioning_ids",
                                                    provisioning_dict.get("provisionings", [])):
            if provisioningid.startswith('P'):
                provisioning = myplfrontend.kernelapi.get_pick(provisioningid)
            else:
                provisioning = myplfrontend.kernelapi.get_movement(provisioningid)
            provisionings.append(provisioning)

        # process provisionings sorted by from_location
        for provisioning in sort_plaetze(provisionings, key='from_location'):
            xml_pos = ET.SubElement(xml_provisioning, 'provisioningposition')

            # FIXME was ist provisioning_type? -> pick/retrieval? wo wird das angedruckt?
            # FIXME: sowas wie from_location gibts bei archivierten daten nicht
            for fieldname in ['from_location', 'provisioning_type', 'menge']:
                _add_subelemententry(xml_pos, fieldname, provisioning)
            
            # article data
            artnr = provisioning['artnr']
            pickmenge = provisioning['menge']
            product = dict(cs.masterdata.article.eap(artnr)) # dict aus couchdb document machen
            product['artnr'] = artnr # ist sonst nur _id
            xml_product = ET.SubElement(xml_pos, 'product')

            volume = product.get('package_volume_liter')
            if volume:
                volume_sum += pickmenge * volume
            else:
                cs.zwitscher.zwitscher('%s: Volumen unbekannt' % artnr, username='mypl')

            weight = product.get('package_weight', 0)/1000.
            if weight:
                weight_sum += pickmenge * weight
            else:
                cs.zwitscher.zwitscher('%s: Gewicht unbekannt' % artnr, username='mypl')

            for fieldname in ['artnr', 'name', 'package_weight']:
                _add_subelemententry(xml_product, fieldname, product)
            products_per_export_package = product.get('products_per_export_package')
            if products_per_export_package:
                ET.SubElement(xml_pos, 'export_packages_per_position').text = unicode(
                        pickmenge / float(products_per_export_package))
            else:
                ET.SubElement(xml_pos, 'export_packages_per_position').text = ''

        ET.SubElement(xml_provisioning, 'volume_sum').text = str(volume_sum)
        ET.SubElement(xml_provisioning, 'weight_sum').text = str(weight_sum)
        return xmlroot

    def generate_xml(self, provisioning_id):
        """Generates the XML File used by Jasperreports"""
        ET.SubElement(self.root, 'generator').text = 'myPL'
        ET.SubElement(self.root, 'generated_at').text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.provisioning2xml(provisioning_id)


class _RetrievalStickerGenerator(_ProvisioningGenerator):
    """Jasper-Generator for retrievalStickers."""

    def __init__(self):
        super(_RetrievalStickerGenerator, self).__init__()
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'reports', 'Retrieval.jrxml'))
        self.reportname = path


class _MovementGenerator(JasperGenerator):
    """Jasper-Generator for Movement-Documents"""

    def __init__(self):
        super(_MovementGenerator, self).__init__()
        self.reportname = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                       'reports', 'Movement.jrxml'))
        self.xpath = '/movements/movement'
        self.root = ET.Element('movements')

    def generate_xml(self, movement_id):
        """Generates the XML File used by Jasperreports"""

        ET.SubElement(self.root, 'generator').text = 'myP'
        ET.SubElement(self.root, 'generated_at').text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        xml_movement = ET.SubElement(self.root, 'movement')
        movement = myplfrontend.kernelapi.get_movement(movement_id)
        for fieldname in ["from_location", "to_location", "oid", "created_at"]:
            _add_subelemententry(xml_movement, fieldname, movement)

        artnr = movement["artnr"]
        product = dict(cs.masterdata.article.eap(artnr)) # dict aus couchdb document machen
        product['artnr'] = artnr # ist sonst nur _id
        xml_product = ET.SubElement(xml_movement, 'product')
        for fieldname in ['artnr', 'name']:
            _add_subelemententry(xml_product, fieldname, product)

        unit = myplfrontend.kernelapi.get_unit(movement['mui'])
        xml_unit = ET.SubElement(xml_movement, 'unit')
        for fieldname in ['height', 'created_at', 'mui', 'menge']:
            _add_subelemententry(xml_unit, fieldname, unit)
        return self.root


def get_provisioning_pdf(provisioning_id):
    """Public interface to get a kommischein pdf."""
    return _ProvisioningGenerator().generate(provisioning_id)


def get_retrievalsticker_pdf(retrieval_id):
    """Public interface to get a retrievalsticker pdf."""
    return _RetrievalStickerGenerator().generate(retrieval_id)


def get_movement_pdf(movement_id):
    """Public interface to get a movement pdf."""
    return _MovementGenerator().generate(movement_id)
