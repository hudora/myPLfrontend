#!/usr/bin/env python
# encoding: utf-8
"""
belege.py

Created by Maximillian Dornseif on 2007-12-13.
Copyright (c) 2007 HUDORA. All rights reserved.
"""

import os
import datetime
import xml.etree.ElementTree as ET

from cs.zwitscher import zwitscher
from pyjasper.client import JasperGenerator
from mypl.kernel import Kerneladapter
from mypl.utils import format_locname
from huTools.robusttypecasts import int_or_0

import produktpass.models

__revision__ = "$Revision: 7184 $"


class ProvisioningGenerator(JasperGenerator):
    """Jasper-Generator for Provisioning-Documents"""

    def __init__(self):
        super(ProvisioningGenerator, self).__init__()
        self.reportname = os.path.abspath(os.path.join(os.path.dirname(__file__), 'reports', 'Provisioning.jrxml'))
        self.xpath = '/provisionings/provisioning/provisioningposition'
        self.root = ET.Element('provisionings')

    def provisioning2xml(self, provisioning):
        """Generic funictionality to turn a Provisioning object into XML."""
        xmlroot = self.root
        xml_provisioning = ET.SubElement(xmlroot, 'provisioning')

        weight_sum = 0
        volume_sum = 0

        ET.SubElement(xml_provisioning, 'location_to').text = format_locname(provisioning.location_to)
        for fieldname in ['id', 'mypl_id', 'parts', 'created_at', 'created_by',
                          'printed_at', 'printed_by']:
            ET.SubElement(xml_provisioning, fieldname).text = unicode(getattr(provisioning, fieldname))

        for fieldname in ['kommissionierbelegnr', 'liefer_date', 'sachbearbeiter', 'warenempfaenger',
                          'versandart', 'auftragsnr']:
            ET.SubElement(xml_provisioning, fieldname).text \
                = unicode(getattr(provisioning.lieferschein, fieldname))

        for pos in sorted(list(provisioning.provisioningposition_set.all())):
            xml_pos = ET.SubElement(xml_provisioning, 'provisioningposition')
            ET.SubElement(xml_pos, 'location_from').text = format_locname(pos.location_from)
            for fieldname in ['provisioning_type', 'quantity_to_pick', 'lineid', 'mui']:
                ET.SubElement(xml_pos, fieldname).text = unicode(getattr(pos, fieldname))
            xml_product = ET.SubElement(xml_pos, 'product')
            try:
                product = produktpass.models.Product.objects.get(artnr=pos.artnr)

                # FIXME: volume is 0
                try:
                    volume_sum += pos.quantity_to_pick * product.package_volume_liter
                    weight_sum += pos.quantity_to_pick * product.package_weight_kg
                except:
                    zwitscher('%s: Gewicht/Volumen unbekannt' % product.artnr,
                    username='mypl')


                for fieldname in ['artnr', 'name', 'einheit', 'ean', 'package_weight',
                                  'package_volume', 'products_per_ve1', 'products_per_export_package']:
                    ET.SubElement(xml_product, fieldname).text = unicode(getattr(product, fieldname))
                ET.SubElement(xml_pos, 'total_package_weight').text \
                    = unicode(int_or_0(product.package_weight) * int_or_0(pos.quantity_to_pick))
                ET.SubElement(xml_pos, 'total_package_volume').text \
                    = unicode(int_or_0(product.package_volume) * int_or_0(pos.quantity_to_pick))
                if product.products_per_export_package > 0:
                    ET.SubElement(xml_pos, 'export_packages_per_position').text \
                        = unicode(int_or_0(pos.quantity_to_pick) / float(product.products_per_export_package))
                else:
                    ET.SubElement(xml_pos, 'export_packages_per_position').text = ''
            except produktpass.models.Product.DoesNotExist:
                pass

        ET.SubElement(xml_provisioning, 'volume_sum').text = str(volume_sum)
        ET.SubElement(xml_provisioning, 'weight_sum').text = str(weight_sum)

        return xmlroot

    def generate_xml(self, provisioning):
        """Generates the XML File used by Jasperreports"""
        ET.SubElement(self.root, 'generator').text = __revision__
        ET.SubElement(self.root, 'generated_at').text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.provisioning2xml(provisioning)


class RetrievalStickerGenerator(ProvisioningGenerator):
    """Jasper-Generator for retrievalStickers."""

    def __init__(self):
        super(RetrievalStickerGenerator, self).__init__()
        self.reportname = os.path.abspath(os.path.join(os.path.dirname(__file__), 'reports',
                                                       'Retrieval.jrxml'))


class MovementGenerator(JasperGenerator):
    """Jasper-Generator for Movement-Documents"""

    def __init__(self):
        super(MovementGenerator, self).__init__()
        self.reportname = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                       'reports', 'Movement.jrxml'))
        self.xpath = '/movements/movement'
        self.root = ET.Element('movements')

    def generate_xml(self, movement):
        """Generates the XML File used by Jasperreports"""

        ET.SubElement(self.root, 'generator').text = __revision__
        ET.SubElement(self.root, 'generated_at').text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        xmlroot = self.root
        xml_movement = ET.SubElement(xmlroot, 'movement')

        ET.SubElement(xml_movement, "location_from").text = format_locname(movement.location_from)
        ET.SubElement(xml_movement, "location_to").text = format_locname(movement.location_to)
        ET.SubElement(xml_movement, "movement_id").text = format_locname(movement.id)
        ET.SubElement(xml_movement, "created_at").text \
            = unicode(movement.created_at.strftime('%Y-%m-%d %H:%M:%S'))

        product = produktpass.models.Product.objects.get(artnr=movement.artnr)
        xml_product = ET.SubElement(xml_movement, 'product')
        for fieldname in ['artnr', 'name', 'einheit', 'ean', 'products_per_export_package',
                          'pallet_height']:
            ET.SubElement(xml_product, fieldname).text = unicode(getattr(product, fieldname))

        xml_unit = ET.SubElement(xml_movement, 'unit')
        ET.SubElement(xml_unit, "mui").text = unicode(movement.mui)
        ET.SubElement(xml_unit, 'height').text = unicode(movement.unit_height)
        ET.SubElement(xml_unit, 'quantity').text = unicode(movement.quantity)
        ET.SubElement(xml_unit, 'created_at').text = movement.unit_created_at.strftime('%Y-%m-%d %H:%M:%S')
        return xmlroot


class StocktakingListGenerator(JasperGenerator):
    """Jasper-Generator for Stocktaking (Inventur/Zählliste)."""

    def __init__(self):
        super(StocktakingListGenerator, self).__init__()
        self.reportname = os.path.abspath(os.path.join(os.path.dirname(__file__),
            'reports', 'Stocktakinglist.jrxml'))
        self.xpath = '/warehouse/location'
        self.root = ET.Element('warehouse')

    def generate_xml(self, locations):
        """Generates the XML File used by Jasperreports"""

        ET.SubElement(self.root, 'generator').text = __revision__
        ET.SubElement(self.root, 'generated_at').text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        xmlroot = self.root
        kernel = Kerneladapter()

        for locname in locations:
            xml_location = ET.SubElement(xmlroot, 'location')
            location = kernel.location_info(locname)
            ET.SubElement(xml_location, "location").text = unicode(locname)
            ET.SubElement(xml_location, "height").text = unicode(location['height'])
            ET.SubElement(xml_location, "attributes").text = unicode(location['attributes'])
            ET.SubElement(xml_location, "floorlevel").text = unicode(location['floorlevel'])
            ET.SubElement(xml_location, "preference").text = unicode(location['preference'])
            ET.SubElement(xml_location, "info").text = unicode(location['info'])
            ET.SubElement(xml_location, "reserved_for").text = unicode(location['reserved_for'])

            for mui in location['allocated_by']:
                unit = kernel.unit_info(mui)
                xml_unit = ET.SubElement(xml_location, "unit")
                ET.SubElement(xml_unit, "mui").text = unicode(unit['mui'])
                ET.SubElement(xml_unit, "quantity").text = unicode(unit['quantity'])
                ET.SubElement(xml_unit, "artnr").text = unicode(unit['product'])
                ET.SubElement(xml_unit, "height").text = unicode(unit['height'])
                ET.SubElement(xml_unit, "pick_quantity").text = unicode(unit['pick_quantity'])
                ET.SubElement(xml_unit, 'created_at').text = unit['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                ET.SubElement(xml_unit, "movements").text = unicode(unit['movements'])
                ET.SubElement(xml_unit, "picks").text = unicode(unit['picks'])
                ET.SubElement(xml_unit, "attributes").text = unicode(unit['attributes'])
                try:
                    product = produktpass.models.Product.objects.get(artnr=unit['product'])
                    ET.SubElement(xml_unit, "product_name").text = unicode(product.name)
                except produktpass.models.Product.DoesNotExist:
                    ET.SubElement(xml_unit, "product_name").text = '???'

        return xmlroot
