#!/usr/bin/env python
# encoding: utf-8
"""
mypl/models.py

Created by Lars Ronge on 2007-10-16.
Refactored by Christian Klein on 2008-11-07.
Furter refactored by Maximillian Dornseif in 2008-12
Refactored and Movement to message based communication
    by Christoph Borgolte and Maximillian Dornseif in 2009.
Copyright (c) 2007, 2008, 2009 HUDORA GmbH. All rights reserved.
"""


from cs.zwitscher import zwitscher
from django.db import models
from huTools.calendar.workdays import previous_workday_german as previous_workday
from huTools.robusttypecasts import int_or_0
from mypl.belege import MovementGenerator, ProvisioningGenerator, RetrievalStickerGenerator
from mypl.kernel import Kerneladapter
import cs.messaging as messaging
import cs.messaging.protocol.lieferscheindruck
import datetime
import huTools.printing
import husoftm.connection
import logging
import mypl.utils
import produktpass.models


__revision__ = "$Revision: 7323 $".split()[-1].strip('$')

LOG = logging.getLogger('mypl.models')
LOG.setLevel(logging.DEBUG)

LIEFERSCHEIN_STATUS = (
    ('new', 'neu'),
    ('ready_for_kernel', u'kann an den kernel übergeben werden'),
    ('in_mypl', u'ist bereits an den kernel übergeben worden'),
    ('in_provisioning', 'wird kommissioniert'),
    ('confirmed', u'zurückgemeldet'),
    ('provisioning_ready', 'wurde komplett kommissioniert'), # besser: provisioning_done
    ('in_interface', 'in Schnittstelle zu SoftM'),
    ('done', 'durch SoftM eingelesen'), # von SoftM als Eingelesen markiert
    ('printed', 'gedruckt'), # TODO: remove, ungenutzt
    ('cancelled', 'storniert'),
    ('zeroized', 'genullt'),
)


# Wie viele Werk-Tage vor dem ermittelten Liefertermin muss der Versandtermin liegen. Für Deutschland
# gibt es eine individuelle Berechnung. Das ganze ist eh ein bisschen zu grob.
LAND_VORLAUFTAGE = {'AT': 3, 'FR': 3, 'ES': 4, 'DE': 1, 'NL': 2, 'BE': 2, 'CH': 4}
LAND_VORLAUFTAGE_DEFAULT = 5

# TODO: use huTools.calendar.add_workdays()
def deduct_workdays(start, days):
    """Deduct number of days workdays from start.

    >>> deduct_workdays(datetime.date(2007, 7, 10), 5)
    datetime.date(2007, 7, 3)
    """

    day = start
    for i in range(days):
        day = previous_workday(day)
    return day


class Lieferschein(models.Model):
    """Repräsentiert einen Kommiauftrag, KEINEN Lieferschein."""

    # fields, taken from SoftM
    # TODO: remove - move to infotext_kunde
    anfangstext = models.TextField(blank=True)
    auftragsnr = models.CharField(max_length=8, db_index=True)
    auftragsnr_kunde = models.CharField(max_length=128, blank=True, null=True)
    # TODO: remove - move to infotext_kunde
    endetext = models.TextField(blank=True)
    kommissionierbelegnr = models.CharField(max_length=8, db_index=True)
    lager = models.IntegerField()
    # TODO: rename to anlieferdatum
    liefer_date = models.DateField(blank=True)
    # TODO: remove
    sachbearbeiter = models.IntegerField(blank=True, default=0) # TODO: remove field
    # TODO: remove
    satznummer = models.IntegerField(blank=True)
    # TODO remove
    versandart = models.CharField(max_length=3, blank=True)
    warenempfaenger = models.CharField(max_length=5)

    # Lieferadresse
    name1 = models.CharField(max_length=40)
    name2 = models.CharField(max_length=40, blank=True)
    name3 = models.CharField(max_length=40, blank=True)
    strasse = models.CharField(max_length=40, blank=True)
    plz = models.CharField(max_length=15, blank=True, db_column='postleitzahl')
    ort = models.CharField(max_length=40, blank=True)
    land = models.CharField(max_length=3, blank=True, db_column='laenderkennzeichen')
    telefon = models.CharField(max_length=20, blank=True)
    # TODO: remove
    fax = models.CharField(max_length=20, blank=True)
    
    # not SoftM-conform fields
    total_weight = models.IntegerField(default=0,
                   help_text='Returns the gewicht of all Items in this Lieferung in g.')
    total_volume = models.FloatField(default=0,
                   help_text='Returns the volume of all Items in this Lieferung in m^3.')
    paletten = models.FloatField(default=0,
                     help_text='Returns the number of pallets of all Items in this Lieferung.')
    export_kartons = models.FloatField(default=0,
              help_text='the estimated number of packages which will be shipped. A float.')
    kep = models.BooleanField(default=False,
              help_text='Entscheidet, ob die Sendung als Paket verschickt werden kann.')
    anbruch = models.BooleanField(default=False,
              help_text='False if no items need a export_package to be opened')
    versandtermin = models.DateTimeField(blank=True, null=True, help_text='suggested date of shipping.')

    # internal fields
    status = models.CharField(max_length=20, choices=LIEFERSCHEIN_STATUS)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='letzte √Ñnderung', null=True)

    class Meta:
        verbose_name_plural = "Lieferscheine"

    def __unicode__(self):
        return u"Provisioning-Note-No.: %s Order-No.: %s ID: %s Status: %s" % (self.kommissionierbelegnr,
               self.auftragsnr, self.id, self.status)

    def commit(self):
        """Meldet einen Kommiauftrag an SoftM (ISR00) zurück."""
        if self.status == 'provisioning_ready' and self.is_provisioning_complete():
            self._commit_to_interface()
            self.status = 'in_interface'
            self.save()

    def zeroize(self):
        """Nullt einen KOmissionierbeleg in SoftM (ISR00).
        
        Nullen führt dazu, dass die entsprechende Ware erneut zugeteilt wird."""
        
        # Wir gehen hier Dreistufig vor:
        # 1: wir vversuchen ihn im Kernel zu nullen
        # 2., wenn das geklappt hat, versuchen wir in in Django auf null zu setzen
        # 3. wenn das geklappt hat, versuchen wir ihn im SoftM zu nullen
        
        if self.status in ['new', 'in_mypl']:
            zwitscher('%s: Versuche Beleg mit Null zurückzumelden (%s, %s)'
                      % (self.kommissionierbelegnr, self.name1, self.ort), username='mypl')
            if self.status == 'in_mypl':
                Kerneladapter().delete_pipeline(self.kommissionierbelegnr)
            self._commit_to_interface('zeroize')
            self.status = 'zeroized'
            self.save()
    
    def _commit_to_interface(self, commit_type='normal', audit_trail=''):
        """Commits the Delivery Note to SoftM by writing records for all positions into ISR00"""
        
        # Rückmeldung in SoftM anstossen
'erp.cs-wms.warenzugang'        
        # Lieferscheindruck anstossen
        zielqueue = 'lieferscheindruck'
        chan = messaging.setup_queue(zielqueue, durable=True)
        doc = messaging.empty_message('mypl.models/%s' % __revision__,
                                       guid='mypl.kommiauftragsrueckmeldung-%s' % self.kommissionierbelegnr,
                                       audit_trail=audit_trail,
                                       audit_info=u'Lieferscheindruck nach Rückmeldung angefordert')
        doc['kommiauftragnr'] = self.kommissionierbelegnr
        doc['printer'] = "DruckerLempel"
        doc['generation'] = 1
        messaging.publish(doc, zielqueue)
        
    
    def get_versandtermin(self):
        """Calculate the shipping date for this delivery_note."""

        versandtermin = deduct_workdays(self.liefer_date, LAND_VORLAUFTAGE.get(self.land,
                                                          LAND_VORLAUFTAGE_DEFAULT))
        return versandtermin

    def is_provisioning_complete(self):
        """Checks, if all existing Provisionings are confirmed"""
        for provisioning in self.provisioning_set.all():
            if provisioning.status != 'confirmed':
                return False
        
        # Emergency Check/BUGFIX:
        # pruefen ob ist und sollmenge uebereinstimmen
        for pos in self.lieferscheinposition_set.all():
            if pos.menge != pos.menge_komissionierbeleg:
                return False
        return True

    def get_quantities(self):
        """  Returns the cumulated quantities for each article of Lieferschein.
        Something like:
        [(4, '10195'), (204, '66702')]"""
        positionen = self.lieferscheinposition_set.all()
        return mypl.utils.deduper([(pos.menge_komissionierbeleg, pos.artnr) for pos in positionen])


class LieferscheinPosition(models.Model):
    """Represents a position of a delivery note"""

    lieferschein_kopf = models.ForeignKey(Lieferschein)
    artnr = models.CharField(max_length=20)
    auftrags_position = models.IntegerField()
    auftragsnr = models.CharField(max_length=8)
    kommissionierbelegnr = models.IntegerField(blank=True, db_index=True)
    kommissionierbeleg_position = models.IntegerField()
    lager = models.IntegerField()
    liefertermin = models.DateTimeField(blank=True)
    menge = models.IntegerField()     # Confirmed quantity (provisioned)
    menge_fakturierung = models.IntegerField()
    menge_komissionierbeleg = models.IntegerField()     # Requested quantity (by SoftM)
    menge_offen = models.IntegerField()
    rechnungsempfaenger = models.CharField(max_length=5)
    setartikel = models.IntegerField()
    weight_per_item = models.FloatField(default=0)
    volume_per_item = models.FloatField(default=0)

    class Meta:
        """Configuration for the Django OR-Mapper."""
        ordering = ['kommissionierbeleg_position']

    def get_values_from_product(self):
        """Gets needed values from Product-Pass (article-weight and -volume)"""

        try:
            product = produktpass.models.Product.objects.get(artnr=self.artnr)
            self.weight_per_item = product.package_weight
            if self.weight_per_item == None:
                self.weight_per_item = 0
            self.volume_per_item = product.package_volume
            if self.volume_per_item == None:
                self.volume_per_item = 0
        except ObjectDoesNotExist:
            self.weight_per_item = 0
            self.volume_per_item = 0
            LOG.error('Productpass for Product %s does not exist' % self.artnr)
        # TODO: weigth and volume extraction doesn't work
        print "Article: %s, Weight: %s, Volume: %s" % (self.artnr, self.weight_per_item, self.volume_per_item)

    def weight_to_pick(self):
        """The total weight of menge_kommissionierbeleg * weight_per_item"""
        return self.menge_komissionierbeleg * int_or_0(self.weight_per_item)


PROVISIONING_STATUS = (
    ('new', 'neu'),
    ('printed', 'Beleg gedruckt'),
    ('confirmed', 'zur√ºckgemeldet'),
    ('ready', 'fertig'))


class Provisioning(models.Model): # kommischein
    """Represents a piece of paper instructing a warehouse worker to get some goods."""

    lieferschein = models.ForeignKey(Lieferschein)
    mypl_id = models.CharField(max_length=40, db_index=True, unique=True)
    parts = models.IntegerField(blank=True, null=True)
    location_to = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.IntegerField(blank=True, null=True, verbose_name='Erstellt durch')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='letzte Änderung', null=True)
    printed_at = models.DateTimeField(blank=True, null=True)
    printed_by = models.CharField(max_length=64, blank=True, default='')
    picked_at = models.DateTimeField(blank=True, null=True)
    picked_by = models.IntegerField(blank=True, null=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    confirmed_by = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=PROVISIONING_STATUS, default='new')

    class Meta:
        permissions = (("can_view_provpipeline", "Can view Provisioning Pipeline"),
                       ("can_initiate_provisioning", "Can initiate Provisioning"),
                       ("can_cancel_movement", "Can cancel a Movement"),
                       ("can_push_provisioning", "Can push Provisioning"),
                       ("can_change_priority", "Can change Provisioning priority"),
                       ("can_zeroise_provisioning", "Can zeroise a Provisioning"),)

    def __unicode__(self):
        return u"ID: %s Status: %s Location To: %s" % (self.id, self.status, self.location_to)
    
    def __repr__(self):
        """Prints the provisioning note for debug purposes. Shows elemental components"""
        ret = []
        ret.append("ID: %s\nStatus: %s\nLocation To: %s\n" % (self.id, self.status, self.location_to))
        ret.append("ID / Article / Quantity_Demanded / Quantity_Picked / Location From / Provisioning-Type")
        for pos in self.provisioningposition_set.all():
            ret.append("%s %s %s %s %s %s" % (pos.id, pos.artnr, pos.quantity_to_pick, pos.quantity_picked,
                                         pos.location_from, pos.provisioning_type))
        return '\n'.join(ret)
    
    def confirm_as_demanded(self):
        """Confirms the Picklist as demanded by SoftM and commits the quantities
           to the delivery note (Lieferschein.menge)"""
        for position in self.provisioningposition_set.all():
            position.quantity_picked = position.quantity_to_pick
            position.save()
        self.confirm_picklist()
    
    def confirm_picklist(self):
        """Confirms the Picklist and commits the quantities to the delivery note (Lieferschein.menge)"""
        if self.status == 'printed':
        
            # cumulate quantities for each article in picklist
            cumulated_quantity = {}
            missing_pos_ids = []
            for pickpos in self.provisioningposition_set.all():
                cumulated_quantity.setdefault(str(pickpos.artnr), 0)
                cumulated_quantity[str(pickpos.artnr)] += pickpos.quantity_picked
            
                if pickpos.quantity_picked == 0:
                    missing_pos_ids.append(pickpos.lineid)
            
            # distribute items to positions in delivery-note and substitute quantities in cumulated picklist
            for ls_pos in self.lieferschein.lieferscheinposition_set.all():
                to_pick = ls_pos.menge_komissionierbeleg - ls_pos.menge
                if (str(ls_pos.artnr) in cumulated_quantity
                    and to_pick <= cumulated_quantity[str(ls_pos.artnr)]):
                    cumulated_quantity[str(ls_pos.artnr)] -= to_pick
                    if (cumulated_quantity[str(ls_pos.artnr)] == 0):
                        del(cumulated_quantity[str(ls_pos.artnr)])
                    ls_pos.menge += to_pick
                elif str(ls_pos.artnr) in cumulated_quantity:
                    ls_pos.menge += cumulated_quantity[str(ls_pos.artnr)]
                    del(cumulated_quantity[str(ls_pos.artnr)])
                ls_pos.save()
            
            # leider liefert der Kernel hier gelegentlich falsche Werte zurück
            prov_status = self._confirm_picklist_to_kernel()

            self.confirmed_at = datetime.datetime.now()
            self.status = 'confirmed'
            self.save()

            # Confirming Provisioning to kernelE and commit delivery note to SoftM (ISR00)
            if prov_status == "provisioned":
                self.lieferschein.status = 'provisioning_ready'
                self.lieferschein.save()
                self.lieferschein.commit()

    def _confirm_picklist_to_kernel(self, missing_pos_ids=None):
        """Confirms the picklist to kernelE"""
        kerneladapter = Kerneladapter()
        if self.get_provisioning_type == 'retrieval':
            ret = kerneladapter.commit_retrieval(self.mypl_id)
        else:
            ret = kerneladapter.commit_picklist(self.mypl_id)
        return ret

    def get_provisioning_type(self):
        """Returns the Provisiong-Type (pick or retrieval)."""
        if str(self.mypl_id).lower().startswith('r'):
            return 'retrieval'
        else:
            return 'pick'

    def create_from_kernel(self, data):
        """Creates a new Provisioning and uses the given data from kernelE
        The given data should look like this:

        ["p00175456", "932444", "AUSLAG", 2, {}, [
                        ["P123254", "340005454452145", "020301", 4, "11007"]
                        ["P123256", "340005454452136", "060401", 2, "11006"]
        ]]
        """
        if not self.id:
            if not len(data) == 6:
                raise RuntimeError("Parameter data has wrong length")

            delivery_note = Lieferschein.objects.get(kommissionierbelegnr=data[1])
            self.mypl_id = data[0]
            self.location_to = data[2]
            self.parts = data[3]
            self.lieferschein = delivery_note
            self.save()

            provisioning_type = self.get_provisioning_type()

            for pos in data[5]:
                new_prov_pos = ProvisioningPosition()
                new_prov_pos.provisioning_type = provisioning_type
                new_prov_pos.lineid = pos[0]
                new_prov_pos.mui = pos[1]
                new_prov_pos.location_from = pos[2]
                new_prov_pos.quantity_to_pick = pos[3]
                new_prov_pos.artnr = pos[4]
                self.provisioningposition_set.add(new_prov_pos)

            self.lieferschein.status = 'in_provisioning'
            self.lieferschein.save()
            self.save()

    def output_on_printer(self, printer="DruckerAllman"):
        """Outputs a Kommischein on a printer."""
        
        pjasper = ProvisioningGenerator()
        pdf = pjasper.generate(self)
        huTools.printing.print_data(pdf, printer=printer)
        if self.status == 'new':
            self.status = 'printed'
            self.save()
    
    def output_stickers_on_printer(self, printer="DruckerSedgewick"):
        """Outputs some Retrievalstickers on a printer."""
        pjasper = RetrievalStickerGenerator()
        pdf = pjasper.generate(self)
        huTools.printing.print_data(pdf, printer=printer)
    
    def debug_print(self):
        return repr(self)
    
    def get_quantities(self):
        """  Returns the cumulated quantities for each article of Provisioning.
        Something like:
        [(4, '10195'), (204, '66702')]"""
        positionen = self.provisioningposition_set.all()
        return mypl.utils.deduper([(pos.quantity_picked, pos.artnr) for pos in positionen])


class ProvisioningPosition(models.Model):
    """Represents a line in a Provisioning."""

    provisioning = models.ForeignKey(Provisioning)
    provisioning_type = models.CharField(max_length=15,
                       choices=(('retrieval', 'retrieval'), ('pick', 'pick')))
    artnr = models.CharField(max_length=20)
    quantity_to_pick = models.IntegerField(blank=True, null=True)
    quantity_picked = models.IntegerField(blank=True, null=True)
    location_from = models.CharField(max_length=20, blank=True, null=True)
    lineid = models.CharField(max_length=40, blank=True, null=True)
    mui = models.CharField(max_length=40, blank=True, null=True)

    def __cmp__(self, other):
        """Compares two ProvisioningPositions - wegoptimierung"""
        return mypl.utils.compare_locations(self.location_from, other.location_from)


class Event(models.Model):
    """Represents a log entry for a job assigned (either a pick, retrieval, or movement)"""

    action_type = models.CharField(max_length=15,
                  choices=(('retrieval', 'retrieval'), ('pick', 'pick'), ('movement', 'movement')))
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    handled_by = models.CharField(max_length=64, blank=True, default='')
    positions = models.IntegerField(blank=True, null=True)
    action_id = models.CharField(max_length=40, blank=True, null=True)

    class Meta:
        get_latest_by = "created_at"


class Staplerjob(models.Model):
    """Represents a stored Movement for Staplr."""
    stapler_id = models.CharField(max_length=2)
    movement_id = models.CharField(max_length=10)
    serialized_movement = models.TextField()

    def __unicode__(self):
        return u'id: %s, stapler id: %s, movement id: %s' % (self.id, self.stapler_id, self.movement_id)


MYPL_FUNCTION_CHOICES = (('zurueckmelden', u'Beleg zurückmelden'),
                         ('picklist_holen', u'Picklist holen'),
                         ('movement_holen', u'Movement holen'),
                         ('retrieval_holen', u'Retrieval holen'),
                         ('stapler_holen', u'Movement holen via Staplr'))


class MyPLConfig(models.Model):
    """Configuration class for MyPL functions."""

    feature = models.CharField(max_length=32, unique=True, db_index=True, choices=MYPL_FUNCTION_CHOICES)
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = u"MyPL Configuration"
        verbose_name_plural = u"MyPL Configurations"


def get_provisionings_by_id(kommi_id):
    """Returns the picklist and the retrievallist for an ID.

    returns (lieferschein, picklist, retrievallist) whereas one of the two might be None.
    So far we assume that an entry in the provisioning pipeline already exists.

    """

    lieferscheine = Lieferschein.objects.filter(kommissionierbelegnr=kommi_id)
    if lieferscheine.count() > 1:
        zwitscher('%s: Kommibeleg doppelt im System! #bug' % kommi_id, username='mypl')

    lieferschein = lieferscheine[0]
    provisionings = lieferschein.provisioning_set.all()
    #if len(provisionings) not in [1, 2]:
    #    raise RuntimeError("Something Nasty is happening %s %r" % (lieferschein, provisionings))
    picklist, retrievallist = None, None
    for prov in provisionings:
        if prov.get_provisioning_type() == 'pick' and not picklist:
            picklist = prov
        elif prov.get_provisioning_type() == 'retrieval' and not retrievallist:
            retrievallist = prov
        else:
            raise RuntimeError("Something very nasty is happening %r" % prov)
    return (lieferschein, picklist, retrievallist)
