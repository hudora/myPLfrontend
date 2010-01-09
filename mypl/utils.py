#!/usr/bin/env python
# encoding: utf-8
"""
mypl.utils - convoinience functions without access to external state/data.

Created by Maximillian Dornseif & Lars Ronge on 2007-12-05.
Copyright (c) 2007 HUDORA. All rights reserved.
"""

import sys
from mypl.kernel.mypl_kerneladapter import Kerneladapter


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
    

def deduper(positions):
    """
    >>> deduper([(4,"10195"), (0,"14695"), (24,"66702"), (180,"66702")])
    [(4, '10195'), (204, '66702')]
    """
    sums = {}
    for quantity, product in positions:
        if quantity:
            if product not in sums:
                sums[product] = 0
            sums[product] += quantity
    ret = [(quantity, product) for product, quantity in sums.items()]
    ret.sort()
    return ret
    

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


def sort_plaetze(items):
    """Sortiert eine Menge von Lagerplätzen nach folgendem Kriterium:
    Reihen werden zu Gängen zusammengefasst, die Plätze der zu besuchenden Gänge werden abwechselnd
    auf- und absteigend sortiert. Siehe http://blogs.23.nu/disLEXiaDE/stories/15539/
    
    Paramter ist ein dictionary, dessen Schlüssel Lagerplätze nach dem Schema Reihe-Riegel-Ebene sind.
    Die Values sind beliebige Objekte.
    
    >>> sort_plaetze([{'location_from': '01-10-01'}, {'location_from': '02-12-01'}, {'location_from': '03-10-01'}, {'location_from': '03-15-01'}, {'location_from': 'EINLAG'}])
    [{'location_from': 'EINLAG'}, {'location_from': '01-10-01'}, {'location_from': '03-15-01'}, {'location_from': '02-12-01'}, {'location_from': '03-10-01'}]
    """
    
    tmp = dict()
    for item in items:
        if hasattr(item, "location_from"):
            location = item.location_from
        elif hasattr(item, "has_key") and item.has_key("location_from"):
            location = item["location_from"]

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


def split_quantities(quantity, per_unit):
    """Splits quantity in units not larger than per_unit.
    
    >>> split_quantities(512.0, 100.0)
    [100, 100, 100, 100, 100, 12]
    >>> split_quantities('512', None)
    [512]
    >>> split_quantities('512.0', 1000)
    [512]
    >>> split_quantities(512, -10)
    [512]
    """
    
    quantity = int(float(quantity))
    if not per_unit or per_unit < 1:
        return [quantity]
    else:
        per_unit = int(float(per_unit))
        ret = []
        while quantity > 0:
            ret.append(min([quantity, per_unit]))
            quantity -= per_unit
        return ret


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


def filter_locations(available=True):
    """Returns a list of warehouse locations.
 
    If available is True, the list of available locations is returned,
    otherwise, the list of occupied locations is returned.
    """

    kerneladapter = Kerneladapter()
    locations = []
    for locname in kerneladapter.location_list():
        location = kerneladapter.location_info(locname)
        if not (location['reserved_for'] or location['allocated_by']) == available:
            locations.append(location['name'])
    return locations


if __name__ == '__main__':
    import doctest
    doctest.testmod()
