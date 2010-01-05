from xml.etree import ElementTree



def dict2xml(dict, xml = ''):
    for key,value in dict.iteritems():
        exec 'content = '+ {'str': 'value', 'dict': 'dict2xml(value)'}[type(value).__name__]
        xml += '<%s>%s</%s>' % (key, str(content), key)
    return xml
    

# defines how listitems are packaged
listnames = {'positionen': 'position',
             'versandeinweisungen': 'versandeinweisung'}

def _ConvertDictToXmlRecurse(parent, dictitem):
    assert type(dictitem) is not type([])

    if isinstance(dictitem, dict):
        for (tag, child) in dictitem.iteritems():
            if type(child) is type([]):
                # iterate through the array and convert
                listelem = ElementTree.Element(tag)
                parent.append(listelem)
                for listchild in child:
                    elem = ElementTree.Element(listnames.get(tag, tag))
                    listelem.append(elem)
                    _ConvertDictToXmlRecurse(listelem, listchild)
            else:                
                elem = ElementTree.Element(tag)
                parent.append(elem)
                _ConvertDictToXmlRecurse(elem, child)
    else:
        parent.text = str(dictitem)
    

def ConvertDictToXml(xmldict, roottag='data'):
    """
    Converts a dictionary to an XML ElementTree Element 
    """

    root = ElementTree.Element(roottag)
    _ConvertDictToXmlRecurse(root, xmldict)
    return root


data = {"kommiauftragsnr":2103839,
 "anliefertermin":"2009-11-25",
 "prioritaet": 7,
 "info_kunde":"Besuch H. Gerlach",
 "auftragsnr":1025575,
 "kundenname":"Ute Zweihaus 400424990",
 "kundennr":"21548",
 "name1":"Uwe Zweihaus",
 "name2":"400424990",
 "name3":"",
 "strasse":"Bahnhofstr. 2",
 "land":"DE",
 "plz":"42499",
 "ort":"Huecksenwagen",
 "positionen": [{"menge": 12,
                 "artnr": "14640/XL",
                 "posnr": 1},
                {"menge": 4,
                 "artnr": "14640/03",
                 "posnr": 2},
                {"menge": 2,
                 "artnr": "10105",
                 "posnr": 3}],
 "versandeinweisungen": [{"guid": "2103839-XalE",
                          "bezeichner": "avisierung48h",
                          "anweisung": "48h vor Anlieferung unter 0900-LOGISTIK avisieren"},
                         {"guid": "2103839-GuTi",
                          "bezeichner": "abpackern140",
                          "anweisung": "Paletten hoechstens auf 140 cm Packen"}]
}


root = ConvertDictToXml(data)
print ElementTree.tostring(root)