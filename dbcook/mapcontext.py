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
    DB_inheritance = <table_inheritance_type> (default =table_inheritance_types.DEFAULT)
        table_inheritance_type: ���� �� 'joined_table' , 'concrete_table' , 'single_table';
        ���� ��������� �� ��������� / �������������� / ����� �� ������������.
      $ this setting is inherited / distributed / seen in the subclasses.

    DB_inheritance_local = <table_inheritance_type>
        �� ���������� �� ���������� ������.
        ���� ���� ������� �� ����� (�� �� �������������� � ������������),
        � ��� ��������� ��� ������� ���� DB_inheritance:
            ������: �: inh=1
                    B(A): inh_local=2
                    C(B): pass
                -> inhtype(A) == 1; inhtype(B) == 2; inhtype(C) == 1 (������ �� �)
      $ to ease some special cases.
        Applies only locally for the class (is not inherited / seen in sublasses),
        AND has priority over the above general DB_inheritance.

    DB_NO_MAPPING = boolean (default =False)
        ���� ���� ���� ��-������������ (��������, "��������", ���������).
        �������� �� ���������� �� "�������" / �������������� ��� �������� �� (������) ����������.
        ���� ���� ������� �� ����� � ����� � �������.
        ��������� ���������� - ���������� �� ����� ���� �� "��������" ��� ������ ���������� (!)
      $ this class has no DB-mapping (intermediate, "filling").
        All of its contents goes into all of its (real) subclasses.
        Applies only locally for the class.
        Use carefully - attributes of such class appear in all of its heirs/subclasses (!)

    DB_HAS_INSTANCES = boolean  (default =is_leaf)
        ���� ���� ��� ����������, �.�. �� � ���� �������� ����,
        � ������ ���������� ������ ���� ���� ������ �� �� ��������.
        ������� � ���������� ������ ���� ����������.
        ���� ���� ������� �� �����.
      $ this class has instances, i.e. is not just an intermediate level,
        and all polymorphic requests through it must include it.
        Leafs in a hierarchy always have instances.
        Applies only locally.

    DB_NEEDS_ID = boolean   (default =False, i.e. has_no_primary_key or is_joined_table-inheritance)
        ���� ���� ������ �� ��� db_id ���������� �� ��������� �� ���� �������� ����
        (��� DB_UNIQ_KEYS), �������� ������ ����� ������� �� ����� �������.
        �� ������ db_id, �� �� �� �������.
        ���� ���� ������� �� �����.
      $ this class must have db_id regardless of availability of other unique keys
        (see DB_UNIQ_KEYS), for example because other classes are pointing it directly.
        Applies only locally.

    DB_UNIQ_KEYS = ������ �� ������� �� (����� �� ������ ��� ������ (����� �� .name) )
                   $ list of lists of (field-names or fields (.name wanted) )
                   default = () #nothing
        ���� ���� ������� �� �����.
      $ Applies only locally.
    '''
    #__slots__ = [ column4ID.name ]     #db_id is automatic
    #DB_inheritance = 'concrete_table'  #default
    #DB_NO_MAPPING = True    #default; klas-local only
    #DB_HAS_INSTANCES = False   #default; klas-local only

# XXX assert not( DB_NO_MAPPING and DB_HAS_INSTANCES) ???

from dbcook.util.attr import getattr_local_instance_only, issubclass

class MappingContext:
    base_klas = None  #_Base or something else
    reflector = None  #some Reflector()

    def mappable( me, klas):
        if klas and issubclass( klas, me.base_klas) and klas is not me.base_klas:
            DB_NO_MAPPING = getattr_local_instance_only( klas, 'DB_NO_MAPPING', None)
            if not DB_NO_MAPPING: return True
        return False

    def has_instances( me, klas):
        #if not me.mappable( klas): return False
        if len( me.subklasi[ klas]) == 1: return True      #leaf
        DB_HAS_INSTANCES = getattr_local_instance_only( klas, 'DB_HAS_INSTANCES', None)
        return bool( DB_HAS_INSTANCES)

    def needs_id( me, klas):
        return getattr_local_instance_only( klas, 'DB_NEEDS_ID', False)

    def uniques( me, klas):
        'list of lists of (column-names or columns  (having .name) )'
        return getattr_local_instance_only( klas, 'DB_UNIQ_KEYS', () )

    def base( me, klas):
        '''���� (������) ����� ������� ����, None ��� ���� �����. �.�. �� ��� ����� �������� �����
         $ get (first) base that is mappable, None if no such, i.e. at or under root-mappable'''
        assert klas
        while klas is not me.base_klas:
            base = klas.__bases__[0]
            assert issubclass( base, me.base_klas)
            if me.mappable( base): return base
            # allow non-mapped classes to declare props -> added to _all_ their children
            klas = base
        return None

    def base4table_inheritance( me, klas):
        base = me.base( klas)
        inheritype = table_inheritance_types.DEFAULT
        if base:
            inheritype = getattr( klas, 'DB_inheritance', None)
            #local:
            inheritype = getattr_local_instance_only( klas, 'DB_inheritance_local', inheritype) or table_inheritance_types.DEFAULT
            try: inheritype = table_inheritance_types._all[ inheritype]
            except KeyError, e:
                assert 0, '%(klas)s: unknown DB_inheritance=%(inheritype)r' % locals()
        return base, inheritype

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
