#$Id$
# -*- coding: cp1251 -*-

'''
TODO:

������:
      * ��� 1:
        x = Reference( struct) = has_one(struct) = SubStruct(struct) = struct.Instance()
+       * ������������� (1-�������)
-?      * 2-������� 1���1: Reference( struct, backref =���_�������, singular=True)
-       * 2-������� � 1-���-�����: Reference( struct, backref =���_�������, singular=False)
            ���_������� ����� �������� ??

+     1 ��� �����:
        x = Collection( struct, backref =���_�������) = has_many
        * ���_������� ���� �� ������, �.�. ������/��������; ����� ��������( Reference)
        * Collection � 2�������� Entity ������ �� ����� ����������� Association
+       * 2-������� � �����-���-1: backref � �������

      ����� ��� �����:
        = ����
+           class myAssocAB( Association):
                DBCOOK_hidden=False
+               a = Link( ����������) - ������ �� ��� �����. Relation � ������
+               b = Link( ��������) - ���� �� ����� �����. Relation � ������, �� �� �������
            class A:
+               x = Association.Relation( myAssocAB) - ������ �� ��� ��������� Link � �����������
-           * �������� �������� ���_�_�����������
-       = ������, �������
+           ������� �� ����� ������, �� ���� ������ (��� �������� �����: DBCOOK_hidden=True)
            �� ���� �� ��� ������ �� 2 ������
                class myAssocAB( Association):
                    DBCOOK_hidden=True
+       = ������, ���������
            ������� �� ���� � ������ ����; ���������� ����� ��������
            ����� ������ (DBCOOK_hidden) - �� ���� �� ��� ������ �� 2 ������
            class A:
                x = Association.Hidden( B, ���_������� )
                    ���_������� � �� ����������� �� ������� ������ (B)
-           * �������� �������� ���_�������


+       * 2-�������
-       * �����������

'''

import sqlalchemy
import sqlalchemy.orm
import warnings
from config import config
import itertools

class Association( object):
    ''' serve as description of the association table and
    storage of association arguments - names and klases -
    which are to be processed/interpreted later.
    It is a mix-in only, to allow attaching to different bases -
    the resulting subclasses may or may not be mixable.
    Keep namespace clean - do not pollute with non-dependent stuff
    '''
    __slots__ = ()
    DBCOOK_no_mapping = True
    DBCOOK_hidden = False
    #DBCOOK_needs_id= True    #XXX db_id is a must only if table is referred

    #DBCOOK_unique_keys= [lists] or classmethod     #may override - all links by default
    @classmethod
    def DBCOOK_unique_keys( klas):
        return [ [ k for k,kklas in klas.walk_links() ] ]
        '''
mssql refused to have unique constraints other than the primary key
>Here's the TSQL for a unique index:
> CREATE UNIQUE NONCLUSTERED INDEX IX_UQ_Sample ON Sample (
> first ASC, other ASC, something ASC)
>
>I defined Sample as:
> CREATE TABLE Sample( first int NOT NULL, something int NULL, other bit NULL)
>
> I don't know how you'd get SqlAlchemy to generate this when it makes tables for you.

theres a ddl() construct used for this. docs at: http://www.sqlalchemy.org/docs/04/sqlalchemy_schema.html#docstrings_sqlalchemy.schema_DDL
        '''

    @classmethod
    def Link( klas, parent_klas, attr =None, **kargs4type):
        '''(in some assoc_klas) declaration of link to parent_klas'''
        typ = klas.Type4Reference( parent_klas, **kargs4type)
        typ.assoc = _AssocDetails( relation_attr= attr, relation_klas=parent_klas )
        #print 'Link', klas, parent_klas, attr
        return typ

    @classmethod
    def Relation( klas, assoc_klas =None, **kargs):
        '''(in some parent_klas) denotes explicit association to klas/assoc_klas'''
        if not assoc_klas: assoc_klas = klas
        if not isinstance( assoc_klas, str):
            assert issubclass( assoc_klas, Association)
            assert assoc_klas._is_valid(), 'empty explicit association %(assoc_klas)r' % locals()
        return _Relation( assoc_klas, **kargs)

    @classmethod
    def Hidden( klas, other_side_klas, other_side_attr ='', backref =''):
        #print 'Hidden Assoc', other_side_klas, '.'+ other_side_attr
        return _Relation4AssocHidden( (klas, other_side_klas), backref= backref or other_side_attr)


    @classmethod
    def get_link_info( klas, attr):
        #sees parent_klas after forward-decl-resolving
        if isinstance( attr, str):
            attr = getattr( klas, attr)
        is_substruct = klas.reflector.is_reference_type( attr)
        return is_substruct[ 'klas'], attr.assoc.relation_attr

    @classmethod
    def walk_links( klas, with_typ =False ):
        #sees parent_klasi after forward-decl-resolving
        for attr,typ in klas.reflector.attrtypes( klas).iteritems():
            is_substruct = klas.reflector.is_reference_type( typ)
            if is_substruct:
                assoc_details = getattr( typ, 'assoc', None)
                if assoc_details:
                    r = attr, is_substruct['klas']
                    if with_typ: r = r + (typ,)
                    yield r

    @classmethod
    def find_links( klas, parent_klas):  #, parent_name):
        for l_attr,l_klas in klas.walk_links():
            if l_klas is parent_klas: #... and l_attr
                yield l_attr


    ######## these must be setup by reflector types
    Type4Reference = None
    reflector = None

    _used = False       #for hidden m2m: set on first found side, to avoid duplication

    ######## internal interface
    @classmethod
    def _is_valid( klas):
        n=0
        for whatever in klas.walk_links():
            n+=1
        return n>=1 #has at least 1 Link
        #for k in dir( klas):
        #    if not k.startswith( '__') and hasattr( getattr( klas, k), 'assoc'):
        #        return True     #has at least 1 Link

    @classmethod
    def _CollectionFactory( klas):
        m = _AssocDetails.MyCollection()
        m.factory = klas
        #m.assoc_attr           #assoc side
        #m.owner, m.owner_attr  #owner side
        return m


from config import table_namer
def resolve_assoc_hidden( builder, klasi):
    dbg = 'assoc' in config.debug or 'relation' in config.debug
    mapcontext = builder.mapcontext
    news = {}
    for k,klas in klasi.iteritems():
        for attr, rel_typ in mapcontext.iter_attr_local( klas, attr_base_klas= _Relation4AssocHidden, dbg=dbg ):
            Assoc, other_side_klas = rel_typ.assoc_klas
            other_side_attr = rel_typ.backrefname
            if dbg: print 'assoc_hidden: ', klas, '.'+attr, '<->', other_side_klas, '.'+other_side_attr
            class AssocHidden( mapcontext.base_klas, Assoc):
                DBCOOK_hidden = True
                left  = Assoc.Link( klas, attr= attr)
                right = Assoc.Link( other_side_klas, attr= other_side_attr)
                @classmethod
                def DBCOOK_dbname( klas):
                    #this sees forward-resolved
                    this_side_klas,  this_side_attr  = klas.get_link_info( 'left')
                    other_side_klas, other_side_attr = klas.get_link_info( 'right')
                    r = '_'.join( ('_Assoc',
                            table_namer( this_side_klas ), this_side_attr,
                            '2',
                            table_namer( other_side_klas), other_side_attr
                        ))
                    return r
            #???? resolve forward-decl ? should work?
            #TODO test

            rel_typ.assoc_klas = assoc_klas = AssocHidden

            #change __name__ - see __name__DYNAMIC
            klasname = '_'.join( ('_Assoc',
                table_namer( klas), attr,
                '2',
                isinstance( other_side_klas, str) and other_side_klas or table_namer( other_side_klas),
                other_side_attr ))
            assoc_klas.__name__ = klasname

            #self-add to mappable klasi
            news[ klasname ] = assoc_klas
    klasi.update( news)

def is_association_reference( klas, attrtyp, attrklas):
    'used in table-maker'
    column_kargs = {}
    column_func = None
    if issubclass( klas, Association):
        assoc_details = getattr( attrtyp, 'assoc', None)
        if assoc_details:
            #column_kargs = dict( nullable= assoc_details.nullable )
            column_func = lambda column, cacher: relate( klas, attrklas, assoc_details.relation_attr,
                                                            column, cacher=cacher)
    return column_kargs, column_func

def relate( klas, parentklas, relation_attr, column, cacher ):
    dbg = 'relation' in config.debug
    if dbg:
        print 'relate parent:', parentklas, 'to child:', klas
        print '  attrname:', relation_attr, 'column:', column

    ### collect relation_attr to be created by make_relation() if not already done explicitly
    lcache = cacher.assoc_links = getattr( cacher, 'assoc_links', {})
    links = lcache.setdefault( parentklas, set() )
    link = (klas, relation_attr)
    assert link not in links, '''duplicate definition
            of assoc_link %(klas)s.%(relation_attr)s to %(parentklas)s''' % locals()
    links.add( link )

    ### collect foreign_keys
    #parentklas.column is pointed by klas.relation_attr
    #dict( klas: dict( parentklas: dict( relation_attr:column)))
    fcache = cacher.foreign_keys = getattr( cacher, 'foreign_keys', {})
    foreign_keys = fcache.setdefault( klas, {})
    kk = foreign_keys.setdefault( parentklas, {} )
    key = relation_attr

    if key is not None:
        assert key not in kk, '''duplicate/ambigious association to %(parentklas)s in %(klas)s;
            specify attr=<assoc_relation_attr> explicitly
            key=%(key)s
            kk=%(kk)s''' % locals()
    else:
        if key in kk:
            warnings.warn( '''duplicate/ambigious/empty association to %(parentklas)s in %(klas)s;
                specify attr=>assoc_relation_attr> explicitly''' % locals() )
    kk[ key ] = column


class _Unspecified: pass

class _Relation( object):
    __slots__ = [ 'rel_kargs', 'assoc_klas', 'backref' ]
    def __init__( me, assoc_klas, backref =None, rel_kargs ={}):
        me.assoc_klas = assoc_klas
        me.rel_kargs = rel_kargs
        if backref and not isinstance( backref, dict):
            backref = dict( name= backref)
        me.backref = backref
    def __str__( me):
        return me.__class__.__name__+'/'+str(me.assoc_klas)

    def resolve( me, builder):
        'needed separately before make()'
        assoc_klas = me.assoc_klas
        if isinstance( assoc_klas, str):
            try: me.assoc_klas = builder.klasi[ assoc_klas]
            except KeyError: assert 0, '''undefined relation/association class %(assoc_klas)r''' % locals()

    def make( me, builder, klas, name ):
        'return relation_klas, actual_relation_klas, relation_kargs'
        dbg = 'relation' in config.debug
        me.resolve( builder)
        assoc_klas = me.assoc_klas
        if dbg: print ' ' , me, '->', klas, '.', name or None

        foreign_keys = builder.foreign_keys[ assoc_klas]
        if dbg: print ' ', me, 'assoc_fkeys:', foreign_keys

        try: fks = foreign_keys[ klas ]
        except KeyError: assert 0, '''missing declaration of link in association %(assoc_klas)s -> %(klas)s.%(name)s ''' % locals()

        assert name, 'relation/association %(assoc_klas)r relates to %(klas)r but no attrname specified anywhere' % locals()
        for key in (name, None):
            try:
                fk = fks[ key]
                break
            except KeyError: pass
        else:
            assert 0, '''missing/wrong relation for association %(klas)s.%(name)s <- %(assoc_klas)s
attrname: %(name)s;
available: %(fks)s;
all foreign_keys: %(foreign_keys)s.
Check for double-declaration with different names''' % locals()

        collection_class = getattr( assoc_klas, '_CollectionFactory', None)
        #if collection_class:
        #    c = collection_class
        #    collection_class = lambda : c( owner=klas, owner_attr=name, assoc_attr= klas)) #klas
        rel_kargs = dict(
                lazy    = True,
    #           cascade = 'all, delete-orphan',    #DB_hidden-relation does FlushError with this
                uselist = True,
                collection_class = collection_class     #needed if InstrumentedList.append is replaced
            )
        rel_kargs.update( me.rel_kargs)

        colid = builder.column4ID( klas )

        ERR_CANNOT_HIDE_ASSOC = '''association %(assoc_klas)s between more than 2 items
            cannot be DBCOOK_hidden (which one to give as other side?)'''

        if getattr( assoc_klas, 'DBCOOK_hidden', None):
            if assoc_klas._used:
                return None
            assoc_klas._used = True
            if len(fks)==2:     #2 diff links to same klas
                #print 'same klas x2'
                assert len(foreign_keys) == 1, ERR_CANNOT_HIDE_ASSOC % locals()
                for k in fks:
                    if k != key: break
                else:
                    assert 0, 'internal error, wrong .foreign_keys[%(klas)s] on %(assoc_klas)s' % locals()
                othername = k
                otherfk = fks[k]
                otherklas = klas
            else:   #2 diff klasi
                #print '2diff', foreign_keys
                assert len(foreign_keys) == 2, ERR_CANNOT_HIDE_ASSOC % locals()
                for otherklas in foreign_keys:
                    if otherklas is not klas: break
                #else:  cannot happen because of above assert
                otherfks = foreign_keys[ otherklas]
                assert len(otherfks) == 1
                othername, otherfk = otherfks.items()[0]
                #assert othername

            assoc_klas_actual = otherklas
            rel_kargs.update(
                    secondary   = builder.tables[ assoc_klas],
                    primaryjoin = (fk == colid),
                    secondaryjoin = (otherfk == builder.column4ID( otherklas)),
                )
        else:
            assoc_klas_actual = assoc_klas
            rel_kargs.update(
                    primaryjoin = (fk == colid),
                    remote_side = fk,
                )
        if dbg: print ' ', me, 'made:', assoc_klas, assoc_klas_actual, rel_kargs
        return assoc_klas, assoc_klas_actual, rel_kargs

from dbcook.util.attr import setattr_kargs

class _AssocDetails:
    __init__ = setattr_kargs

    #do not pollute Association' namespace
    class MyCollection( list):
        #owner = None
        factory = None
        @sqlalchemy.orm.collections.collection.internally_instrumented
        def append( me, obj =_Unspecified, **kargs):
            if obj is _Unspecified:
                assert len(kargs)>1, 'give all kargs, or maybe use hidden assoc (DBCOOK_hidden=true)'
                obj = me.factory( **kargs)
            if not me.factory.DBCOOK_hidden:
                assert isinstance( obj, me.factory), 'give premade %r object, or maybe use hidden assoc (DBCOOK_hidden=true)' % me.factory
            me._append( obj)
            return obj
        @sqlalchemy.orm.collections.collection.appender
        def _append( me, *a,**k): return list.append( me, *a, **k)

class _Relation4AssocHidden( _Relation):
    @property
    def backrefname( me): return me.backref and me.backref['name'] or ''

##############################

class Collection( _Relation):
    '''define one2many relations - in the 'one' side of the relation
    (parent-to-child/ren relations in terms of R-DBMS).
    '''
    __slots__ = [ 'backrefname' ]

    def __init__( me, child_klas,
                    backref =None,   #backref name or dict( name, **rel_kargs)
                    #unique =False,  #   ??
                    **rel_kargs ):   #order_by =None, etc
        _Relation.__init__( me, child_klas, backref, rel_kargs)
        me.backrefname = None   #decided later
    def setup_backref( me, parent_klas, parent_attr):
        from config import column4ID
        backref = me.backref
        if backref:
            backrefname = backref[ 'name']
        else:
            backrefname = column4ID.backref_make_name( parent_klas, parent_attr)
        me.backrefname = backrefname
        return backrefname

def make_relations( builder, sa_relation_factory, sa_backref_factory, FKeyExtractor ):
    dbg = 'relation' in config.debug

    #XXX TODO move all this into make_mapper_props ??

    for m in builder.itermapi( primary_only =True):
        if dbg: print 'make_relations', m

        klas = m.class_

        fkeys = FKeyExtractor( klas, m.local_table, builder.mapcontext, builder.tables)

        assoc_links = getattr( builder, 'assoc_links', {}).get( klas, () )

        if assoc_links:
            #match assoc-links with real rels
            assoc_links_names = dict( (rel_attr, assoc_klas) for assoc_klas, rel_attr in assoc_links )
            for name,typ in builder.mapcontext.iter_attr( klas, local= False):
                assert name not in assoc_links_names, '''%(klas)s.%(name)s specified both
                        as attribute and as link in association ''' % locals() + str( assoc_links_names[ name] )
            for name,typ in builder.mapcontext.iter_attr( klas, attr_base_klas= _Relation, local= False):
                typ.resolve( builder)

                try: assoc_links.remove( (typ.assoc_klas, name) )       #match real rel to named link
                except KeyError:
                    try: assoc_links.remove( (typ.assoc_klas, None))    #match real rel to unnamed link
                    except KeyError:
                        #print 'notfound'
                        pass
                    else:
                        if dbg: print '  found matching noname-assoc_link for', name
                        pass
                else:
                    if dbg: print '  found matching named-assoc_link and relation for', name
                    pass
                    #or error as duplicate??

            #only missing links left here in assoc_links... now combine with all other _Relation
            if dbg and assoc_links: print '  association-implied implicit relations:', assoc_links

        relations = {}

        #XXX this may invent wrong (backref) relation !
        assoc_implicit_rels = [ (rel_attr, _Relation( assoc_klas))
                                    for assoc_klas, rel_attr in assoc_links
                                    if rel_attr and not getattr( assoc_klas, 'DBCOOK_hidden', None)
                                        #if no name on this side: nothing here, all at other side
                                        #if DBCOOK_hidden: nothing here, all at other/explicit side
                                ]
        if dbg and assoc_links: print '  association-implied valid implicit relations:', assoc_implicit_rels

        iter_rels = builder.mapcontext.iter_attr_local( klas, attr_base_klas= _Relation, dbg=dbg )

        for name,typ in itertools.chain( iter_rels, assoc_implicit_rels ):
            rel_info = typ.make( builder, klas, name)    #any2many
            if not rel_info:
                if dbg: print '  DONE ON OTHERSIDE:', name
                assert 0, 'must not come here???'
                #continue
            rel_klas, rel_klas_actual, rel_kargs = rel_info
            #if not rel_klas_actual: rel_klas_actual = rel_klas

            #forward link
            r = fkeys.get_relation_kargs( name)
            if dbg: print '  FORWARD:', name, r, fkeys
            rel_kargs.update( r)

            #backward link 1:n
            backref = typ.backref
            if backref:
                r = fkeys.get_relation_kargs( typ.backrefname)
                if dbg: print '  BACKREF:', typ.backrefname, r, backref
                for p in 'post_update remote_side'.split():
                    try: backref[ p] = r[p]
                    except KeyError: pass
                #explicit - as SA does if backref is str
                pj = rel_kargs[ 'primaryjoin']
                sj = rel_kargs.get( 'secondaryjoin')
                if rel_kargs.get( 'secondary') and sj: pj,sj=sj,pj
                backref = sa_backref_factory(
                            #secondary = secondary,
                            primaryjoin  = pj,
                            secondaryjoin= sj,
                            ##XXX uselist= False, #??? goes wrong if selfref - both sides become lists
                            **backref)
                rel_kargs[ 'backref'] = backref

            #print ' property', name, 'on', klas, 'via', rel_klas, rel_klas is not rel_klas_actual and '/'+str(rel_klas_actual) or '',
            #print ', '.join( '%s=%s' % kv for kv in rel_kargs.iteritems() )
            m.add_property( name, sa_relation_factory( rel_klas_actual, **rel_kargs) )
            relations[ name ] = rel_klas

        klas._DBCOOK_relations = relations



'''
1. declare intermediate association class as subclass of Association, and
    using attrname = Association.Link( klasname), any number of these.
    other attributes as required
2. End-object attr for relation is specified either in above Base4Association.Link( attr=relname),
    or explicit in the End-object:
        relname = IntermediateKlas.Relation()
     or relname = Base4Association.Relation( IntermediateKlas)
    if both specified, the last declared is taken (overrides).
    Having such relation-attr is not mandatory, some End-object may not need it.
'''

if 10:
    from aboutrel import about_relation
    def get_class_of_relation(*a,**k): return about_relation(*a,**k).otherside.klas
else:
    class get_class_of_relation( object):
        '''use as
            get_class_of_relation(x)        #=== .otherside(x)
            get_class_of_relation.otherside(x)
            get_class_of_relation.child(x)
            get_class_of_relation.reference(x)
            get_class_of_relation.parent(x) #=== .reference
            '''
        @staticmethod
        def _klas_attr( klas_attr_or_klas, attr =None):
            if attr is not None: return getattr( klas_attr_or_klas, attr)
            return klas_attr_or_klas

        @classmethod
        def child( me, klas_attr_or_klas, attr =None):
            'get_child_class'
            klas_attr = me._klas_attr( klas_attr_or_klas, attr )
            return klas_attr.impl.collection_factory().factory
            #return parent_klas._DBCOOK_relations[ attr]   #needs flatening from all the inh-classes

        @classmethod
        def reference( me, klas_attr_or_klas, attr =None):
            'get_parent_class'
            klas_attr = me._klas_attr( klas_attr_or_klas, attr )
            return klas_attr.property.mapper.class_
        parent = reference

        def otherside( me, klas_attr_or_klas, attr =None):
            klas_attr = me._klas_attr( klas_attr_or_klas, attr )
            prop = getattr( klas_attr, 'property', None)
            if prop is not None: #parent - ref2one ... or isinstance???
                return prop.mapper.class_
            #child - rel2many
            impl = getattr( klas_attr, 'impl', None)
            assert impl is not None, 'not a relation klas_attr: %(klas_attr)r' % locals()
            return impl.collection_factory().factory
        __new__ = otherside
        otherside = classmethod( otherside)

# vim:ts=4:sw=4:expandtab
