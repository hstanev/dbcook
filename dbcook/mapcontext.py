#$Id$
# -*- coding: cp1251 -*-

class table_inheritance_types:      #db-layout
    JOINED    = 'joined_table'      #it's own (extra-base) fields only + join(base)
    CONCRETE  = 'concrete_table'    #each is complete and separate, stand-alone
    SINGLE    = 'single_table'      #all-in-one: all fields go in base's table - no own representation
    DEFAULT = CONCRETE
    #TODO:  ������ ������ �� �����������: ��� JOINED ����������� ��� ���� ������ (=����� �� ����)
    #       ���� �� ���� ��� ��������� (������) ������� - ���� single_table
    #       special case for optimisation: JOINED inheritance without new fields (=change of type)
    #       can do without own (empty)             table - like single_table
    _all = dict( (v,v) for k,v in locals().iteritems() if not k.startswith('__') )
    _all.update( (v.split('_table',1)[0],v) for v in _all.keys() )

class _Base( object):   #use as example/template
    '''������������ �����, �.�. persistent;
    ��� �� (��������� ��� ���������/��������) ��������/�������;
    ������� (�� ������) �� ����� ��� ������ ����� ������ ��� ���� "�������".
    ���������� (�������) �� ��������������� ������/������� � ������������
    �� ������� �������� �� �������, �.�. ��� ����� ����� �� �� �������������.
  $ persistent object;
    it has (own or shared/assembled) collection/table;
    an attribute (of someone) of this type always becomes a link to this "table".
    Hierarchy (tree) of persistent objects/classes is a subset of the full hierarchy of classes,
    i.e. there can be nodes which are not persisting.

  ���������:
$ settings:
    DBCOOK_inheritance = <table_inheritance_type> (default =table_inheritance_types.DEFAULT)
        table_inheritance_type: ���� �� 'joined_table' , 'concrete_table' , 'single_table';
        ���� ��������� �� ��������� / �������������� / ����� �� ������������.
      $ this setting is inherited / distributed / seen in the subclasses.

    DBCOOK_inheritance_local = <table_inheritance_type>
        �� ���������� �� ���������� ������.
        ���� ���� ������� �� ����� (�� �� �������������� � ������������),
        � ��� ��������� ��� ������� ���� DBCOOK_inheritance:
            ������: �: inh=1
                    B(A): inh_local=2
                    C(B): pass
                -> inhtype(A) == 1; inhtype(B) == 2; inhtype(C) == 1 (������ �� �)
      $ to ease some special cases.
        Applies only locally for the class (is not inherited / seen in sublasses),
        AND has priority over the above general DBCOOK_inheritance.

    DBCOOK_no_mapping = boolean (default =False)
        ���� ���� ���� ��-������������ (��������, "��������", ���������).
        �������� �� ���������� �� "�������" / �������������� ��� �������� �� (������) ����������.
        ���� ���� ������� �� ����� � ����� � �������.
        ��������� ���������� - ���������� �� ����� ���� �� "��������" ��� ������ ���������� (!)
      $ this class has no DB-mapping (intermediate, "filling").
        All of its contents goes into all of its (real) subclasses.
        Applies only locally for the class.
        Use carefully - attributes of such class appear in all of its heirs/subclasses (!)

    DBCOOK_has_instances = boolean  (default =is_leaf)
        ���� ���� ��� ����������, �.�. �� � ���� �������� ����,
        � ������ ���������� ������ ���� ���� ������ �� �� ��������.
        ������� � ���������� ������ ���� ����������.
        ���� ���� ������� �� �����.
      $ this class has instances, i.e. is not just an intermediate level,
        and all polymorphic requests through it must include it.
        Leafs in a hierarchy always have instances.
        Applies only locally.

    DBCOOK_needs_id = boolean   (default =False, i.e. has_no_primary_key or is_joined_table-inheritance)
        ���� ���� ������ �� ��� db_id ���������� �� ��������� �� ���� �������� ����
        (��� DBCOOK_unique_keys), �������� ������ ����� ������� �� ����� �������.
        �� ������ db_id, �� �� �� �������.
        ���� ���� ������� �� �����.
      $ this class must have db_id regardless of availability of other unique keys
        (see DBCOOK_unique_keys), for example because other classes are pointing it directly.
        Applies only locally.

    DBCOOK_unique_keys = ������ �� ������� �� (����� �� ������ ��� ������ (����� �� .name) )
                   $ list of lists of (field-names or fields (.name wanted) )
                   default = () #nothing
        ���� ���� ������� �� �����.
      $ Applies only locally.
    '''
    #__slots__ = [ column4ID.name ]     #db_id is automatic
    #DBCOOK_inheritance = 'concrete_table'  #default
    #DBCOOK_no_mapping = True    #default; klas-local only
    #DBCOOK_has_instances = False   #default; klas-local only

# XXX assert not( DBCOOK_no_mapping and DBCOOK_has_instances) ???

from dbcook.util.attr import getattr_local_instance_only, issubclass
class _NOTFOUND: pass

class MappingContext:
    base_klas = None  #_Base or something else
    reflector = None  #some Reflector()

    def mappable( me, klas):
        if klas and issubclass( klas, me.base_klas) and klas is not me.base_klas:
            DBCOOK_no_mapping = getattr_local_instance_only( klas, 'DBCOOK_no_mapping', None)
            if not DBCOOK_no_mapping: return True
        return False

    def has_instances( me, klas):
        #if not me.mappable( klas): return False
        if len( me.subklasi[ klas]) == 1: return True      #leaf
        DBCOOK_has_instances = getattr_local_instance_only( klas, 'DBCOOK_has_instances', None)
        return bool( DBCOOK_has_instances)

    def getattr_local_or_nonmappable_base( me, klas, attr, *default):
        assert klas
        base_klas = me.base_klas
        while klas is not base_klas:
            r = getattr_local_instance_only( klas, attr, _NOTFOUND)
            if r is not _NOTFOUND:
                #XXX tricky: klas.__dict__['xyz'] is not klas.xyz, esp. for classmethods/descriptors
                #this is the only place so far, it is safe to getattr
                return getattr( klas, attr)

            for base in klas.__bases__:
                if issubclass( base, base_klas): break
            else:
                assert 0, '%(klas)s does not inherit baseklas %(base_klas)s' % locals()
            if me.mappable( base): break
            # allow non-mapped classes to declare DBCOOK_configs for their children
            klas = base
        if default: return default[0]
        raise AttributeError, 'no attr %(attr)s in %(klas)s' % locals()

    def needs_id( me, klas):
        return getattr_local_instance_only( klas, 'DBCOOK_needs_id', None)

    def uniques( me, klas):
        'list of lists of (column-names or columns  (having .name) )'
        #association must see attrs belonging to base non-mappable classes
        r = me.getattr_local_or_nonmappable_base( klas, 'DBCOOK_unique_keys', () )
        if callable( r): r = r()
        return r

    def base( me, klas):
        '''���� (������) ����� ������� ����, None ��� ���� �����. �.�. �� ��� ����� �������� �����
         $ get (first) base that is mappable, None if no such, i.e. at or under root-mappable'''
        #TODO optimize via __mro__
        assert klas
        base_klas = me.base_klas
        while klas is not base_klas:
            for base in klas.__bases__:
                if issubclass( base, base_klas): break
            else:
                assert 0, '%(klas)s does not inherit baseklas %(base_klas)s' % locals()
            if me.mappable( base): return base
            # allow non-mapped classes to declare props -> added to _all_ their children
            klas = base
        return None

    def base4table_inheritance( me, klas):
        base = me.base( klas)
        inheritype = table_inheritance_types.DEFAULT
        if base:
            inheritype = getattr( klas, 'DBCOOK_inheritance', None)
            #local:
            inheritype = getattr_local_instance_only( klas, 'DBCOOK_inheritance_local', inheritype) or table_inheritance_types.DEFAULT
            try: inheritype = table_inheritance_types._all[ inheritype]
            except KeyError, e:
                assert 0, '%(klas)s: unknown DBCOOK_inheritance=%(inheritype)r' % locals()
        return base, inheritype

    def iter_attr_local( me, klas, **kargs):
        return me.iter_attr( klas, local= True, **kargs)

    def iter_attr( me, klas, attr_base_klas =None, **kargs):
        if not attr_base_klas:
            return me.reflector.attrtypes( klas).iteritems()
        return me._iter_attr( klas, attr_base_klas, **kargs)

    def _iter_attr( me, klas, attr_base_klas, local =False, dbg =False):
        base_klas, inheritype = me.base4table_inheritance( klas)
        is_joined_table = (inheritype == table_inheritance_types.JOINED)
        dir_base_klas = is_joined_table and dir( base_klas) or ()
            #joined_table: subclass' tables consist of extra attributes -> joins
        for k in dir( klas):
            attr = getattr( klas, k)
            if not isinstance( attr, attr_base_klas): continue
            if local and k in dir_base_klas:
                if dbg: print '  inherited:', k
                continue
            yield k,attr

    def is_direct_inherited_non_concrete( me, klas):
        for sk in me.subklasi[ klas].direct:
            _base_klas, sk_inheritype = me.base4table_inheritance( sk)
            if sk_inheritype != table_inheritance_types.CONCRETE:
                return True
        return False

    def root( me, klas):
        '''������ ������� ������� ���� ���-������ �� ������ �� ����������; ����� ����� ��� � �����
         $ get the mappable base class nearest to real root; input klas if at root'''
        assert klas
        while klas:
            root = klas
            klas = me.base( root)
        return root

    def need_typcolumn( me, klas):
        '''��� klas e _�����_ �������� �� ������ � ��-concrete_table,
            � ��������� � (�.�. �) concrete_table
         $ if klas is directly inherited by someone with non-concrete_table,
            AND inherits with (is) concrete_table
        '''
        _base_klas, inheritype = me.base4table_inheritance( klas)
        if inheritype != table_inheritance_types.CONCRETE: return False

        return me.is_direct_inherited_non_concrete( klas)

    SET = set
    DICT = dict

#    def __init__( me): me.subklasi = {}
    def make_subklasi( me, iterklasi ):
        'subklasi = { klas: (subklas1,subklas2) }'
        SET = me.SET
        class Subklasi( SET):
            def __init__( me, klas):
                SET.__init__( me, (klas,) )
                me.direct = SET()
        subklasi = me.DICT()
        for klas in iterklasi:
            #issubclass klas, klas
            subklasi.setdefault( klas, Subklasi( klas) )
            base_klas = klas
            level = 0
            while True:
                base_klas = me.base( base_klas)
                if not base_klas: #me.mappable( base_klas):
                    break
                #issubclass klas, base_klas
                subs = subklasi.setdefault( base_klas, Subklasi( base_klas))
                subs.add( klas)
                if not level:
                    subs.direct.add( klas)
                level += 1
        me.subklasi = subklasi
        return subklasi

# vim:ts=4:sw=4:expandtab
