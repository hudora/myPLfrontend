from sqlobject import SQLObject, StringCol, IntCol, DateTimeCol, sqlhub, connectionForURI

def to_dict(self):
    "Returns the attributes of a SQLObject as a dictionary"
    return dict(self._reprItems())

SQLObject.__getitem__ = SQLObject.__getattribute__
SQLObject.to_dict = to_dict

def set_connection(scheme):
    """
    Sets the databases connection.
    Examples:
        postgres://chris@localhost/mypl_archive
        postgres://kernele@hurricane.local.hudora.biz/mypl_archive
    """
    sqlhub.processConnection = connectionForURI(scheme)

class Unit(SQLObject):
    #id = StringCol(length=128, notNone=True, unique=True)
    mui = StringCol(length=32, notNone=True)
    quantity = IntCol(notNone=True)
    product = StringCol(length=20, notNone=True)
    transaction = StringCol(length=32, notNone=True)
    ref = StringCol(notNone=True)
    location = StringCol(length=20, notNone=True)
    height = IntCol(notNone=True)
    created_at = DateTimeCol(notNone=True)
    archived_at = DateTimeCol(notNone=True)
    
    class sqlmeta:
        table = "unitarchive"
        idType = str

class Pick(SQLObject):
    #id = StringCol(length=128, notNone=True, unique=True)
    mui = StringCol(length=32, notNone=True)
    quantity = IntCol(notNone=True)
    product = StringCol(length=20, notNone=True)
    transaction = StringCol(length=32, notNone=True)
    ref = StringCol(notNone=True)
    created_at = DateTimeCol(notNone=True)
    archived_at = DateTimeCol(notNone=True)
    
    class sqlmeta:
        table = "pickarchive"
        idType = str

class Movement(SQLObject):
    #id = StringCol(length=128, notNone=True, unique=True)
    mui = StringCol(length=32, notNone=True)
    quantity = IntCol(notNone=True)
    product = StringCol(length=20, notNone=True)
    transaction = StringCol(length=32, notNone=True)
    ref = StringCol(notNone=True)
    created_at = DateTimeCol(notNone=True)
    archived_at = DateTimeCol(notNone=True)
    
    class sqlmeta:
        table = "movementarchive"
        idType = str