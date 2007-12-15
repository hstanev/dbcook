#$Id$
# -*- coding: cp1251 -*-

''' simple O3RM builder:
 - attribute types are only used for DB columns
 - DB-related objects should inherit Base / Association
 - no other (python) restrictions are imposed on objects

Either use the new Builder here, or staticaly
modify the base original: setup( builder.Builder).
Then use the Base, Association, Type4Reference, either
via Builder.xxxx, or directly from here.
'''


from dbcook import builder
table_inheritance_types = builder.table_inheritance_types

class Type( object): pass
class Type4Reference( Type):
    def __init__( me, klas, lazy ='default', as_value =False):
        assert not as_value
        me.itemklas = klas
        me.lazy = lazy
        me.as_value = False
    @staticmethod
    def resolve_forward1( typ, *namespaces):
        assert isinstance( typ, Type4Reference)
        assert isinstance( typ.itemklas, str)
        for namespace in namespaces:
            try:
                r = typ.itemklas = namespace[ typ.itemklas]
                return r
            except KeyError: pass
        raise KeyError, typ.itemklas
    @staticmethod
    def resolve_forwards( namespace, klas_attrvalue_iterator, namespace2 ={}):
        for typ in klas_attrvalue_iterator:
            if isinstance( typ, Type4Reference):
                if isinstance( typ.itemklas, str):
                    Type4Reference.resolve_forward1( typ, namespace, namespace2)
    def __str__( me):
        return me.__class__.__name__ + '/'+repr(me.itemklas)

class Reflector4sa( builder.Reflector):
    '''reflector is static sigleton, hence the attrtypes stay on klas._attrtypes,
    and not in the reflector.somedict[klas] (or it may grow forever).
    The only reason for the Reflector to be static and not local to Builder
    is the Base's __str___/obj2str below...
    '''
    def _attrtypes( me, klas):
        try:
            d = klas.__dict__[ '_attrtypes']
        except KeyError:
            klas._attrtypes = d = {}
            for k in dir( klas):
                if k.startswith('__'): continue
                v = getattr( klas,k)
                if isinstance( v, Type): d[k]=v
        return d
    def attrtypes_iterkeys( me, klas):   return me._attrtypes( klas).iterkeys()
    def attrtypes_itervalues( me, klas): return me._attrtypes( klas).itervalues()
    def attrtypes_iteritems( me, klas):  return me._attrtypes( klas).iteritems()
    def attrtypes_hasattr( me, klas, attr):
        return attr in me._attrtypes( klas)
    def attrtypes_clean( me, klas):
        try: del klas._attrtypes
        except AttributeError: pass

    ##############
    def type_is_substruct( me, typ):
        if not isinstance( typ, Type4Reference):
            return None
        klas = typ.itemklas
        return dict( klas=typ.itemklas, lazy=typ.lazy, as_value=typ.as_value)

    def type_is_collection( me, typ): return False

    ##############
    def _resolve_forward_references( me, namespace, base_klas):
        import sys
        for klas in namespace.itervalues():
            if not builder.issubclass( klas, base_klas): continue
            Type4Reference.resolve_forwards( namespace,
                    me.attrtypes_itervalues( klas),
                    sys.modules[ klas.__module__].__dict__ )
        #this can also remove all Type4Reference's from klas
    def _resolve_forward_reference1( me, klas, namespace):
        return Type4Reference.resolve_forward1( klas, namespace)



reflector = Reflector4sa()

class Base( object):
    def __str__( me): return reflector.obj2str( me, Base, builder.column4ID.name)
    __repr__ = __str__

class Association( builder.relation.Association):
    Type4Reference = Type4Reference

class Collection( builder.relation.Collection):
    Type4Reference = Type4Reference


def setup( s):
    s.reflector = reflector
    s.Type4Reference = Type4Reference
    s.Base = Base
    s.Association = Association
    s.Collection = Collection

class Builder( builder.Builder): pass
setup( Builder)

#############################################

#XXX TODO one common example

if __name__ == '__main__':
    import sqlalchemy
    class Text( Type): pass
    fieldtypemap = {
        Text: dict( type= sqlalchemy.String, ),
    }

    class A( Base):
        name = Text()
        DBCOOK_has_instances =True
    class B( A):
        alias = Text()
    class C( Base):
        color = Text()
        blink = Type4Reference( B)

    from samanager import SAdb
    SAdb.Builder = Builder
    SAdb.config.getopt()
    sadb = SAdb()

    sadb.open( recreate=True)
    sadb.bind( locals(), fieldtypemap, )#, debug='mapper')

     #create some instances
    a = A()
    a.name = 'ala'

    b = B()
    b.name = 'bala'
    b.alias = 'ba'

    c = C()
    c.color = 'red'
    c.blink = b

     #save them
    populate_namespace = locals()
    session = sadb.session()
    sadb.saveall( session, populate_namespace )
    session.flush()
    session.close()

    for klas in [ A,B,C]:
        print '==', klas
        for qy in [ sadb.query_ALL_instances, sadb.query_BASE_instances, sadb.query_SUB_instances ]:
            print ' --', qy.__name__
            r = qy( session, klas)
            for a in r: print a

    sadb.destroy()

# vim:ts=4:sw=4:expandtab
