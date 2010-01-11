#!/usr/bin/env python
# encoding: utf-8
"""
mypl_kerneladapter.py

Created by Maximillian Dornseif on 2007-10-12.
Copyright (c) 2007 HUDORA GmbH. All rights reserved.
"""

# TODO:
# Relation zwischen Unit und Pick?

import socket, simplejson, datetime, time, types, sys

try:
    import sqladapter
except ImportError:
    USE_SQL_BACKEND = False
else:
    USE_SQL_BACKEND = True

DEBUG = True


class KernelError(RuntimeError):
    """Generic kernel error, inherits from RuntimeError for legacy reasons."""
    def __init__(self, kernelreport):
        self.report = kernelreport

    def __repr__(self):
        return repr(self.report)

    def __str__(self):
        return str(self.report)



def e2string(data):
    """Turn an Erlang String into a Python string."""
    # if we got a list of numbers turn it into a string
    if data and data[0] and type(data[0]) == types.IntType:
        return ''.join([chr(x) for x in data])
    if data == []:
        return ''
    return data


def e2datetime(data):
    """Convert a Erlang Timestamp into a Python datetime object."""
    mydate, mytime = data[:2]
    year, month, day = mydate
    hour, minute, second = mytime
    if len(data) == 2:
        # date and time was given
        return datetime.datetime(year, month, day, hour, minute, second)
    if len(data) == 3:
        # date, time and microseconds are given
        microsecond = data[2]
        return datetime.datetime(year, month, day, hour, minute, second, microsecond)

def e2date(data):
    """Convert a Erlang Timestamp into a Python datetime object."""
    year, month, day = data
    return datetime.date(year, month, day)

def attributelist2dict(attlist, fixattnames=[]):
    """Converts an Erlang Proplist to a Python Dict.
    
    See http://www.erlang.org/doc/man/proplists.html for proplists.
    Using JSON we have issues converting Erlang strings to Python strings.
    This function tries to convert all keys to strings and all values where
    the key is present in fixattnames.
    """
    ret = {}
    for data in attlist:
        if len(data) == 1:
            name = data[0]
            value = True
        else:
            name, value = data
            
        if name in fixattnames:
            ret[e2string(name)] = e2string(value)
        else:
            ret[e2string(name)] = value
    return ret

def attributelist2dict_str(attlist):
    """Like attributelist2dict but tries to convert _all_ values to strings."""
    
    ret = {}
    for data in attlist:
        if len(data) == 1:
            name = data[0]
            value = True
        else:
            name, value = data

        if type(value) == types.ListType:
            ret[e2string(name)] = e2string(value)
        else:
            ret[e2string(name)] = value
    return ret


def print_timing(func):
    """Decorator to print execution time of functions if options.debug is True."""
    
    def _wrapper(*args, **kwargs):
        """Closure providing the actual functionality of print_timing()"""
        
        if DEBUG:
            print "calling %r: " % (func),
        start = time.time()
        try:
            ret = func(*args, **kwargs)
        except:
            print '\n', repr((args, kwargs)), '\n'
            raise
        finally:
            if DEBUG:
                delta = time.time() - start
                print "\t%2.5fs" % (delta)
        
        return ret
    _wrapper.__doc__ = func.__doc__
    _wrapper.__dict__ = func.__dict__
    return _wrapper

def nice_exception(func):
    """Decorator to print call parameters should an exception occur."""
    
    def _wrapper(*args, **kwargs):
        """Closure providing the actual functionality of nice_exception()"""
        
        ret = RuntimeError
        try:
            ret = func(*args, **kwargs)
        except:
            sys.stderr.write('\n%r = %r\n' % ((args, kwargs), ret))
            raise
        return ret
    _wrapper.__doc__ = func.__doc__
    _wrapper.__dict__ = func.__dict__
    return _wrapper


class Kerneladapter:
    """Interacting thit kernelE Erlang Node."""
    def __init__(self):
        self.host = 'kernel.local.hudora.biz'
        self.port = 1919
        self.connected = False
        self.debug = False
        self.sock = False
    
    def __del__(self):
        if self.connected:
            self.sock.close()
    
    def _init_connection(self):
        """connects to server"""
        if not  self.connected:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            header = self.sock.makefile().readline().strip()
            if not header.startswith("200 "):
                raise RuntimeError, "Error reading header: %r" % header
    
    def _read(self):
        """Read Date from the Server stripping of newlines.s"""
        data = self.sock.makefile().readline().strip()
        if self.debug:
            print "<<<", data
        return data
    
    def _read_json(self, code):
        """Read data from the server and decode it as JSON entry."""
        data = self._read()
        codestr = "%d " % code
        if not data.startswith(codestr):
            raise KernelError("unexpected reply: %r" % data)
        data = data[len(codestr):]
        return simplejson.loads(data)
    
    def _read_code(self, code):
        """Read data from the server and check the return code."""
        data = self._read()
        codestr = "%d " % code
        if not data.startswith(codestr):
            raise RuntimeError, "unexpected reply: %r" % data
        return data[4:]
    
    def _send(self, line):
        """Dend data to the server."""
        self._init_connection()
        if self.debug:
            print ">>>", line
        self.sock.send(line + '\n')
    
    @nice_exception
    def count_product(self, product):
        """Gibt die Mengen und NVEs zu einem Produkt an.
        
        >>> import kernelE
        >>> k = kernelE.Kerneladapter_mock()
        >>> k.count_product("14612/01")
        ([85, 85, 0, 0], ['4d183fee-7fb4-11dc-97fa-0017f2c8caff', '4e20d496-7fb4-11dc-97fa-0017f2c8caff'])
        """
        
        product = product.replace(',','').replace('\n','').replace('\r','')
        self._send("count_product %s" % (product,))
        mengen, muis = self._read_json(220)
        return (mengen, [e2string(x) for x in muis])
    
    @nice_exception
    def count_products(self):
        """Gibt die Mengen für alle Produkte im Lager zurück.
        
        >>> import kernelE
        >>> k = kernelE.Kerneladapter_mock()
        >>> k.count_products()
        [('10011', 8, 8, 0, 0), ('10104', 131, 131, 0, 0), '...']
        """
        
        self._send("count_products")
        ret = self._read_json(220)
        return [(e2string(product), fmenge, amenge, rmenge, pmenge) for (product, fmenge, amenge,
                                                                         rmenge, pmenge) in ret]
        
    
    @nice_exception
    def get_articleaudit(self, product):
        """Liefert das Auditlog fuer einen artikel zurueck."""
        product = product.replace(',','').replace('\n','').replace('\r','')
        self._send("get_articleaudit %s" % (product,))
        ret = self._read_json(220)
        out = []
        for data in ret:
            ddict = attributelist2dict_str(data)
            ddict['created_at'] = e2datetime(ddict['created_at'])
            out.append(ddict)
        return out

    @nice_exception
    def get_unitaudit(self, mui):
        """Liefert das Auditlog fuer eine Unit/NVE."""
        mui = mui.replace(',','').replace('\n','').replace('\r','')
        self._send("get_unitaudit %s" % (mui,))
        ret = self._read_json(220)
        out = []
        for data in ret:
            ddict = attributelist2dict_str(data)
            ddict['created_at'] = e2datetime(ddict['created_at'])
            out.append(ddict)
        return out
        
    
    @nice_exception
    def get_articlecorrection(self, artnr):
        """Liefert Korrekruren fuer eine Artnr."""
        artnr = artnr.replace(',','').replace('\n','').replace('\r','')
        self._send("get_articlecorrection %s" % (artnr,))
        ret = self._read_json(220)
        return ret
        
    
    @nice_exception
    def location_list(self):
        """Returns a list of all location names.
        
        >>> import kernelE
        >>> location_list()
        ['011601', '011701', '011801', '012001', '...']
        """
        
        self._send("location_list")
        return [e2string(x) for x in self._read_json(220)]
    
    @nice_exception
    def location_info(self, name):
        """Gibt Informationen zu einem Lagerplatz aus.
        
        >>> import kernelE
        >>> k = kernelE.Kerneladapter_mock()
        >>> k.location_info("104103")
        {u'info': 'BRUECKE', u'reserved_for': [], u'name': '104103', u'height': 3000, u'preference': 3, u'floorlevel': False, u'attributes': [], u'allocated_by': ['4d820122-7fb4-11dc-97fa-0017f2c8caff']}
        """
        
        self._send("location_info %s" % name)
        status, data = self._read_json(220)

        if status == u'error':
            raise KernelError("%s: %s" % (name, data))

        data = attributelist2dict(data, ['name'])
        data['allocated_by'] = [e2string(x) for x in data['allocated_by']]
        data['reserved_for'] = [e2string(x) for x in data['reserved_for']]
        data['info'] = e2string(data['info'])
        return data
    
    @nice_exception
    def unit_list(self):
        """Returns a list of all MUIs"""
        self._send("unit_list")
        return [e2string(x) for x in self._read_json(220)]

    @nice_exception
    def unit_info(self, name):
        """
        >>> import kernelE
        >>> k = kernelE.Kerneladapter_mock()
        >>> k.unit_info("4dac128c-7fb4-11dc-97fa-0017f2c8caff")
        {u'product': '10120', u'created_at': datetime.datetime(2007, 10, 21, 9, 2, 8, 823722), u'height': 1950, u'pick_quantity': 0, u'location': '100903', u'picks': [], u'attributes': [], u'movements': [], u'mui': '4dac128c-7fb4-11dc-97fa-0017f2c8caff', u'quantity': 24},
        """
        
        self._send("unit_info %s" % name)
        ok, data = self._read_json(220)
        data = attributelist2dict(data, ['mui', 'product', 'location'])
        data['movements'] = [e2string(x) for x in data['movements']]
        data['picks'] = [e2string(x) for x in data['picks']]
        data['created_at'] = e2datetime(data['created_at'])
        
        # TODO: This still needs to be implemented
        # if kernelE did not return a result, query the database
        #if USE_SQL_BACKEND and not data:
        #   resultset = Unit.selectBy(mui=name)
        #   data = map(Movement.to_dict, resultset)
        
        return data
    
    @nice_exception
    def update_unit_height(self, name, height):
        self._send("update_unit %s" % (simplejson.dumps(('height', name, height))))
        return self._read_json(220)
    
    @nice_exception
    def movement_info(self, name):
        """Liefert Informationen zu einem Movement.
        
        >>> import kernelE
        >>> k = kernelE.Kerneladapter_mock()
        >>> k.movement_info('m1195651098.535517')
        {u'to_location': '212402', u'from_location': '012801', u'created_at': datetime.datetime(2007, 11, 21, 13, 18, 18, 538711), u'attributes': [], u'mui': '012801|30.0|10106|340059981000000463', u'id': 'm1195651098.535517'}
        """
        self._send("movement_info %s" % name)
        json = self._read_json(220)
        if json[0] == 'error':
            raise KernelError(repr(json))
        ok, data = json
        data = attributelist2dict_str(data)
        data['created_at'] = e2datetime(data['created_at'])
        data['attributes'] = attributelist2dict_str(data.get('attributes', []))
        
        # TODO: This still needs to be implemented
        # if kernelE did not return a result, query the database
        #if USE_SQL_BACKEND and not data:
        #   resultset = Movement.selectBy(id=name)
        #   data = map(Movement.to_dict, resultset)
        
        return data
        
    
    @nice_exception
    def movement_list(self):
        """Liefert eine Liste aller (offenen) Movements.
        
        >>> import kernelE
        >>> k = kernelE.Kerneladapter_mock()
        >>> k.movement_list()
        ["m1193-85203-450126-mypl_test@lichtblick",
         "m1193-85203-453117-mypl_test@lichtblick",
         "m1193-85203-455263-mypl_test@lichtblick",
         "m1193-85203-456898-mypl_test@lichtblick",
         "m1193-85203-459094-mypl_test@lichtblick"]
        """
        self._send("movement_list")
        return [e2string(x) for x in self._read_json(220)]
    
    
    @nice_exception
    def pick_info(self, name):
        """Liefert Informationen zu einem Pick.
        
        >>> import kernelE
        >>> k = kernelE.Kerneladapter_mock()
        >>> k.pick_info('p1195651098.535517')
        {u'to_location': '212402', u'from_location': '012801', u'created_at': datetime.datetime(2007, 11, 21, 13, 18, 18, 538711), u'attributes': [], u'mui': '012801|30.0|10106|340059981000000463', u'id': 'm1195651098.535517'}
        """
        self._send("pick_info %s" % name)
        ok, data = self._read_json(220)
        data = attributelist2dict_str(data)
        data['created_at'] = e2datetime(data['created_at'])
        data['attributes'] = attributelist2dict_str(data.get('attributes', []))
        
        # TODOL: This still needs to be implemented
        # if kernelE did not return a result, query the database
        #if USE_SQL_BACKEND and not data:
        #   resultset = Pick.selectBy(id=name)
        #   data = map(Movement.to_dict, resultset)
        
        return data
        
    
    @nice_exception
    def pick_list(self):
        """Liefert eine Liste aller (offenen) Picks.
        
        >>> import kernelE
        >>> k = kernelE.Kerneladapter_mock()
        >>> k.pick_list()
        ["p1193-85203-460109-mypl_test@lichtblick", "p1193-85203-461143-mypl_test@lichtblick"]
        """
        
        self._send("pick_list")
        return [e2string(x) for x in self._read_json(220)]
            
    
    @nice_exception
    def dump_requests(self):
        """Liefert den Inhalt des Requestrackers."""
        self._send("dump_requests")
        return self._read_json(220)
        
    
    @nice_exception
    def init_location(self, name, height=1950, floorlevel=False, preference=5, info='', attributes=[]):
        """Init a location by creating it or by updating it."""
        name = name.replace(',','').replace('\n','').replace('\r','')
        info = info.replace(',',' ').replace('\n','').replace('\r','')
        if not info:
            # the tokenizer used in kernelE can't handle 'foo,,bar', only 'foo, ,bar'
            info = ' '
        # attributes are not implemented so far
        self._send("init_location %s,%d,%r,%d,%s,[]" % (name, height, floorlevel, preference, info))
        return self._read_code(220)
        
    @nice_exception
    def init_movement(self, mui, destinationname):
        """Initialisiert ein movement"""
        self._send("init_movement %s,%s" % (mui, destinationname))
        ret = self._read_json(220)
        if len(ret) == 2:
            ok, ret = ret
            return e2string(ret)
        else:
            raise RuntimeError, "Fehler im kernel: %r" % ret
    
    @nice_exception
    def init_movement_to_good_location(self, mui, attributes={}):
        """Initialisiert ein movement an einen geeigneten Ort"""
        # TODO: implement transfer of attributes (on a separate call?)
        self._send("init_movement_to_good_location %s" % mui)
        ret = self._read_json(220)
        if len(ret) == 2:
            ok, ret = ret
            return e2string(ret)
        else:
            raise RuntimeError, "Fehler im kernel: %r" % ret
    
    @nice_exception
    def make_nve(self):
        """Generate a NVE/SSCC."""
        self._send("make_nve")
        ret = self._read_json(220)
        return e2string(ret)
        
    
    @nice_exception
    def get_abc(self):
        """Get ABC Klassification."""
        self._send("get_abc")
        ret = self._read_json(220)
        out = []
        for klass in ret:
            out.append([(x[0], e2string(x[1])) for x in klass])
        return out
        
    
    @nice_exception
    def store_at_location(self, name, quantity, artnr, mui=None, height=1950, attributes={}):
        """Store Procucts at a certain Location."""
        if mui == None:
            mui = "%s" % (self.make_nve())
        name = name.replace(',','').replace('\n','').replace('\r','')
        artnr = artnr.replace(',','').replace('\n','').replace('\r','')
        mui = mui.replace(',','').replace('\n','').replace('\r','')
        # TODO: send attributes to the kernel
        self._send("store_at_location %s,%s,%d,%s,%d" % (name, mui, quantity, artnr, height))
        ret = self._read_json(220)
        print ret
        ok, mui = ret
        return e2string(mui)
    
    def store_at_location_multi(self, uid, name, elements, attributes):
        """Store many Procucts at a certain Location. Returns a list of MUIs.
                 
        Elements is a list of (arnr, quantity, heigth). If you try to use the same uid several
        times a KernelDuplicateId Exception is raised.
        """
                                                 
        elements = [(int(x[0]), x[1], int(x[2])) for x in elements]
        self._send("store_at_location_multi %s" % (simplejson.dumps([uid, name, elements, attributes.items()])))
        ret = self._read_json(220)
        if ret[0] == 'ok':
            return [e2string(mui) for mui in ret[1]]
        if ret == 'duplicate_id':
            raise  KernelDuplicateId, "duplicate Id during storing: %s %r" % (uid, elements)
        raise  KernelError, "error during storing of %r: %r" % (elements, ret)

    @nice_exception
    def retrieve(self, mui):
        """Retrieve a Unit from the Warehouse making in vanish."""
        mui = mui.replace(',','').replace('\n','').replace('\r','')
        self._send("retrieve %s" % (mui,))
        ok, ret = self._read_json(220)
        ret[1] = e2string(ret[1])
        return ret
        
    
    @nice_exception
    def find_provisioning_candidates(self, quantity, artnr):
        """Find Units from which a provisioning could be done."""
        artnr = artnr.replace(',','').replace('\n','').replace('\r','')
        self._send("find_provisioning_candidates %d,%s" % (quantity, artnr))
        ret = self._read_json(220)
        if ret[0] == 'ok':
            ok, retrievals, picks = ret
            retrievals = [e2string(x) for x in retrievals]
            picks = [(x[0], e2string(x[1])) for x in picks]
            ret = (ok, retrievals, picks)
        return ret
        
    
    @nice_exception
    def find_provisioning_candidates_multi(self, poslist):
        """Find Units from which a provisioning for several products could be done."""
        self._send("find_provisioning_candidates_multi %s" % (simplejson.dumps(poslist)))
        ret = self._read_json(220)
        if ret[0] == 'ok':
            ok, retrievals, picks = ret
            retrievals = [e2string(x) for x in retrievals]
            picks = [(x[0], e2string(x[1])) for x in picks]
            ret = (ok, retrievals, picks)
        return ret
        
    
    @nice_exception
    def correction(self, uid, mui, old_quantity, product, change_quantity, attributes={}):
        """See http://static.23.nu/md/Files/myPL/doc/mypl_db.html#correction-6"""
        self._send("correction %s" % (simplejson.dumps((uid, mui, old_quantity, product, change_quantity,
                                      attributes.items()))))
        ret = self._read_json(220)
        return ret
        
    
    @nice_exception
    def commit_movement(self, movementid):
        """Commit a single Movement."""
        self._send("commit_movement %s" % (movementid))
        return self._read_json(220)
        
    
    @nice_exception
    def rollback_movement(self, movementid):
        """Rollback a single Movement."""
        self._send("rollback_movement %s" % (movementid))
        return self._read_json(220)
        
    
    @nice_exception
    def commit_retrieval(self, movementid):
        """Commit a single Retrieval."""
        self._send("commit_retrieval %s" % (movementid))
        ret = self._read_json(220)
        return ret
        
    
    @nice_exception
    def rollback_retrieval(self, movementid):
        """Rollback a single Retrieval."""
        self._send("rollback_retrieval %s" % (movementid))
        return self._read_json(220)
        
    
    @nice_exception
    def init_pick(self, quantity, mui):
        """Start a single Pick."""
        self._send("init_pick %s %s" % (quantity, mui))
        return self._read_json(220)
        
    
    @nice_exception
    def commit_pick(self, pickid):
        """Commit a single Pick."""
        self._send("commit_pick %s" % (pickid))
        ret = self._read_json(220)
        return ret
        
    
    @nice_exception
    def rollback_pick(self, pickid):
        """Rollback a single pick."""
        self._send("rollback_pick %s" % (pickid))
        return self._read_json(220)
        
    
    @nice_exception
    def insert_pipeline(self, cid, orderlines, priority, customer, weigth, volume, attributes):
        """adds an order to the provisioningpipeline
        
        `CId' is a unique Id used by the client to refer to this Picking order, e.g. the "Lieferscheinnummer"
        or something similar. `Orderlines' is a list of Articles to
        provision. The List elements are tuples `{Quanity, Product, Attributes}' where Attributes contains
        arbitrary data for use at tha client side.
        The higher the `priority' the more likely it is, that the Order is processed early. If you want the
        scheduler to also consider day to deliver you have to encode that into priority. E.g.
        E.g. `NewPriority = Priority + 10 * max([(now() + 5 - order.day_to_deliver), 0])'.
        'Customer' is to aggregate shippments to the same customer. 'Weigth' and 'Volume' are the calculated
        total Weigth and Volume of the shippment and are used to make scheduling descisions.
        
        
        insert_pipeline(Id, [(20, 10106, {"auftragsposition": 1, "gewicht": 34567}),
                 (70, 14650, {"auftragsposition": 2, "gewicht": 35667}),
                 (30, 76500, {"auftragsposition": 3, "gewicht": 12367})],
                 28, "34566", 345000, 581.34,
                 {"auftragsnumer": "123432", "liefertermin": "2007-12-23"}).
        """
        
        new_orderlines = []
        for orderline in orderlines:
            new_orderlines.append((orderline[0], orderline[1], orderline[2].items()))
        parameters = (str(cid), new_orderlines, int(priority), unicode(customer).encode('utf-8'),
                           int(weigth), float(volume), attributes.items())
        self._send("insert_pipeline %s" % (simplejson.dumps(parameters)))
        return self._read_json(220)
                
    
    def _format_provpipeline(self, data):
        orders = []
        for order in data:
            cid, attributes, orderlines = order
            data = attributelist2dict_str(attributes)
            data['id'] = e2string(cid)
            data['orderlines_count'] = len(orderlines)
            data['orderlines'] = []
            for orderline in orderlines:
                quantity, product, attributes = orderline
                odata = attributelist2dict_str(attributes)
                odata['quantity'] = int(quantity)
                odata['product'] = e2string(product)
                data['orderlines'].append(odata)
            orders.append(data)
        return orders
        
    
    @nice_exception
    def provpipeline_list_new(self):
        """Returns the unprocessed contents of provpipeline.
        
        Entries are in the approximate order in which they will be processed."""
        self._send("provpipeline_list_new")
        ret = self._read_json(220)
        #{'auftragsnummer': 636142,
        # 'id': '930539',
        # 'kernel_customer': '16527',
        # 'liefertermin': '2007-12-05',
        # 'orderlines': [{'auftragsposition': 1,
        #                 'gewicht': 0,
        #                 'product': '24500',
        #                 'quantity': 30},
        #                {'auftragsposition': 2,
        #                 'gewicht': 0,
        #                 'product': '30950/EK',
        #                 'quantity': 62},
        #                {'auftragsposition': 15,
        #                 'gewicht': 0,
        #                 'product': '65325',
        #                 'quantity': 15}],
        # 'tries': 27}
        orders = self._format_provpipeline(ret)
        return orders
        
    
    @nice_exception
    def provpipeline_list_processing(self):
        """Returns the contents of provpipeline currently being processed."""
        self._send("provpipeline_list_processing")
        ret = self._read_json(220)
        orders = self._format_provpipeline(ret)
        return orders
        
    @nice_exception
    def provpipeline_list_prepared(self):
        """Returns the contents of provpipeline beeing prepared for processinf processed."""
        self._send("provpipeline_list_processing")
        ret = self._read_json(220)
        orders = self._format_provpipeline(ret)
        return orders
        
    @nice_exception
    def get_picklists(self):
        """returns one or more Picklists to be processed next.
        
        >>> get_picklist()
        [('p1195654200.622052', '40145201', 'AUSLAG', 1, {'liefertermin': '2007-11-12'},
             [('P1195654200.621917', '340059981000021932', 15, '092001', '83161', {})]),
         ('p1195654200.622053', '40145202', 'AUSLAG', 1, {'liefertermin': '2007-11-13'},
             [('P1195654200.621918', '340059981000021943', 4, '092002', '83161', {})])]
        
        """
        self._send("get_picklists")
        ret = self._read_json(220)
        if ret == 'nothing_available':
            return []
        out = []
        for data in ret:
            pick_list_id, cid, destination, attributes, parts, positions = data
            pick_list_id = e2string(pick_list_id)
            cid = e2string(cid)
            destination = e2string(destination)
            poslist = []
            for position in positions:
                (pos_id, nve, source, quantity, product, posattributes) = position
                pos_id = e2string(pos_id)
                nve = e2string(nve)
                source = e2string(source)
                product = e2string(product)
                poslist.append((pos_id, nve, source, quantity, product,
                                attributelist2dict_str(posattributes)))
            out.append((pick_list_id, cid, destination, parts, attributelist2dict_str(attributes), poslist))
        return out
    
    
    @nice_exception
    def get_retrievallists(self):
        """returns one or more Retrievallists to be processed next.
        
        >>> get_retrievallists()
        [('r1195655518.977542', '40145183', 'AUSLAG', 2, {'liefertermin': '2007-11-19'}, 
            [('m1195655518.977156', '340059981000897650', '042802', '14695', {})])]
        """
        
        self._send("get_retrievallists")
        ret = self._read_json(220)
        if ret == 'nothing_available':
            return []
        out = []
        for data in ret:
            retrieval_list_id, cid, destination, attributes, parts, positions = data
            retrieval_list_id = e2string(retrieval_list_id)
            cid = e2string(cid)
            destination = e2string(destination)
            poslist = []
            for position in positions:
                (posId, nve, source, quantity, product, posattributes) = position
                posId = e2string(posId)
                nve = e2string(nve)
                source = e2string(source)
                product = e2string(product)
                poslist.append((posId, nve, source, quantity, product, attributelist2dict_str(posattributes)))
            out.append((retrieval_list_id, cid, destination, parts,
                        attributelist2dict_str(attributes), poslist))
        return out
        
    
    @nice_exception
    def get_movementlist(self):
        """Get one or more Movements from the Server."""
        self._send("get_movementlist")
        ret = self._read_json(220)
        if ret == 'nothing_available':
            return []
        ok, mIds = ret
        out = []
        for mId in mIds:
            out.append(e2string(mId))
        return out
    
    @nice_exception
    def commit_picklist(self, cId):
        """Commits a Picklist thus marking it as done."""
        self._send("commit_picklist %s" % (cId,))
        ret = self._read_json(220)
        return ret
    
    @nice_exception
    def commit_retrievallist(self, cId):
        """Commits a Retrievallist thus marking it as done."""
        self._send("commit_retrievallist %s" % (cId,))
        ret = self._read_json(220)
        return ret
        
    
    @nice_exception
    def provisioninglist_list(self):
        self._send("provisioninglist_list")
        ret = self._read_json(220)
        return ret
        
    
    @nice_exception
    def provisioninglist_info(self, cid):
        self._send("provisioninglist_info %s" % cid)
        ret = self._read_json(220)
        ok, metadata = ret
        metadata = attributelist2dict_str(metadata)
        metadata['attributes'] = attributelist2dict_str(metadata['attributes'])
        metadata['provisioning_ids'] = [e2string(pid) for pid in metadata['provisioning_ids']]
        return metadata
        
    
    @nice_exception
    def provpipeline_info(self, cid):
        """Get information related to a provpipeline entry."""
        
        # ({u'anbruch': False,
        # u'art': '',
        # u'auftragsnummer': 1031271,
        # u'fixtermin': True,
        # u'kep': True,
        # u'kernel_customer': '17909',
        # u'kernel_enqueued_at': [[2008, 11, 10], [14, 57, 49]],
        # u'kundenname': 'Wolfgang Tries',
        # u'land': 'DE',
        # u'liefertermin': '2008-11-11',
        # u'max_packstueck_gewicht': 5700,
        # u'packstuecke': 3,
        # u'paletten': 0.074999999999999997,
        # u'picks': 1,
        # u'plz': '24837',
        # u'priority': 6,
        # u'provisioninglists': ['p06253580'],
        # u'status': u'processing',
        # u'tries': 2,
        # u'versandpaletten': 1.0,
        # u'versandtermin': '2008-11-10',
        # u'volume': 132.72,
        # u'weigth': 15240},
        # (6, '12732', {'auftragsposition': 1, 'gewicht': 0})])



        self._send("provpipeline_info %s" % cid)
        (cid, metadata, positions) = self._read_json(220)
        cid = e2string(cid)
        metadata = attributelist2dict_str(metadata)
        positions = [(quantity, e2string(artnr), attributelist2dict_str(attr)) for (quantity, artnr, attr) in positions]
        # clean up lists of strings
        for name in ['provisioninglists', 'kernel_picks', 'kernel_retrievals']:
            if name in metadata:
                metadata[name] = [e2string(pid) for pid in metadata[name]]
        return (metadata, positions)
        
    
    @nice_exception
    def feed_eap(self, artnr, prod_ve1=0, prod_exportpackage=1, export_pallet=0,
                 prod_x=0, prod_y=0, prod_z=0, prod_g=0,
                 ve1_x=0, ve1_y=0, ve1_z=0, ve1_g=0,
                 export_x=0, export_y=0, export_z=0, export_g=0):
        """Sends information about product dimensions etc. to the kernel."""
        # ensure that none values are translated to 0
        def nonone(val):
            if not val:
                return 0
            return val
        
        (artnr,  prod_ve1, prod_exportpackage, export_pallet, prod_x, prod_y, prod_z, prod_g,
         ve1_x, ve1_y, ve1_z, ve1_g, export_x, export_y, export_z,
         export_g) = [nonone(x) for x in (artnr,  prod_ve1, prod_exportpackage, export_pallet, 
                                          prod_x, prod_y, prod_z, prod_g, ve1_x, ve1_y, ve1_z, ve1_g,
                                          export_x, export_y, export_z, export_g)]
        self._send("feed_eap %s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d" % (artnr, 
                   prod_ve1, prod_exportpackage, export_pallet, prod_x, prod_y, prod_z, prod_g,
                   ve1_x, ve1_y, ve1_z, ve1_g, export_x, export_y, export_z, export_g))
        ret = self._read_json(220)
        return ret
    
    def statistics(self):
        """Get statistical information from the mypl."""
        self._send("statistics")
        ret = self._read_json(220)
        return attributelist2dict_str(ret)
                        
    def statistics_bewegungen(self):
        """Get historical movement etc. information from the mypl."""
        self._send("bewegungen")
        ret = self._read_json(220)
        ret = [(e2date(day), art, zahl) for ((day, art), zahl) in ret]
        return ret
     
    @nice_exception
    def find_empty_location(self):
        """Liefert eine Liste aller freien Locations."""
        self._send("find_empty_location_nice 1950")
        return [e2string(x) for x in self._read_json(220)]

    @nice_exception
    def push_picklist(self, cid):
        self._send("push_picklist %s" % (cid,))
        ret = self._read_json(220)
        return ret


def tester():
    from pprint import pprint
    data = {u'provisioninglists': [[u'provisioninglist', [112, 48, 48, 48, 53, 53, 49, 54, 51], 
                                    u'picklist', [57, 51, 48, 53, 53, 55], [65, 85, 83, 76, 65, 71], 
                                  [[u'kernel_customer', [49, 56, 48, 52, 48]],
                                  [[97, 117, 102, 116, 114, 97, 103, 115, 110, 117, 109, 109, 101, 114],
                                   644338], 
                                   [[108, 105, 101, 102, 101, 114, 116, 101, 114, 109, 105, 110],
                                   [50, 48, 48, 55, 45, 49, 48, 45, 49, 53]]], 
                                   1, 
                                   [[[80, 48, 48, 48, 53, 53, 49, 53, 57], 
                                   [51, 52, 48, 48, 53, 57, 57, 56, 49, 48, 48, 48, 48, 50, 48, 57, 55, 51],
                                   [49, 57, 51, 53, 48, 49], 4, [56, 52, 48, 48, 51], []]]]], 
            'orderlines_count': 1, 
            'orderlines': [
            {'auftragsposition': 1, 
            'product': '84003', 
            'gewicht': 0, 
            'quantity': 4}], 
            u'kernel_customer': '18040', 
            'liefertermin': '2007-10-15', 
            'retrieval': None, 
            u'priority': 5, 
            u'tries': 0, 
            'pick': '<Provisioning: Provisioning object>',
            'lieferschein': '<Lieferschein: Lieferschein object>',
            'auftragsnummer': 644338,
            'id': '930557'}
    for provraw in data['provisioninglists']:
        provnr, a2, a3, kommibelegnr, a5, attributes, parts, a8 = provraw
        provpipeline = attributelist2dict_str(attributes)
        provpipeline['recordtype'] = e2string(provnr)
        provpipeline['id'] = e2string(a2)
        provpipeline['type'] = e2string(a3)
        provpipeline['kommibelegnr'] = e2string(kommibelegnr)
        provpipeline['destination_location'] = e2string(a5)
        provpipeline['parts'] = parts
        provpipeline['provisionings'] = []
        provisionings = a8
        for provisioning in provisionings:
            provisioningid, mui, location, quantity, product, pattributes = provisioning
            position = attributelist2dict_str(pattributes)
            position['id'] = e2string(provisioningid)
            position['mui'] = e2string(mui)
            position['location'] = e2string(location)
            position['quantity'] = quantity
            position['product'] = e2string(product)
            provpipeline['provisionings'].append(position)
        pprint(provpipeline)


if __name__ == '__main__':
    tester()
