#$Id$
# -*- coding: cp1251 -*-

'''
������ ��������� � ����� ���������:
    * StaticType � ��:
        - None <-> _NONE/notSetYet
            - get/set ���� �� �� ������, ���  _typeprocess
            - ����� �������� ������� 'is None' !!! ����. db_id �� �������� ������ ����
        - enum_value = r.StaticType['enum'].dict[ r.enum ]
            !! ����� a ���� �� �� �� �������� InstrumentedAttributes ������

    * ���������:
        - ��������-��������� - �� ����� �� �� ��������!
    * mappers:
        - ������������: ��
            + joined_table & concrete_table; all-same, all-same-at-node; mixed
            + query_BASE_instances, query_ALL_instances, query_SUB_instances
            - single_table
        + references - ?? =relation /uselist=False
            + ���������� A.b->B
            + ��������: A.b->B.a->A  A.b->B.c->C.a->�; cut-cyclic-deps, use_alter, post_update, foreign keys
            + ����-������ ��: A.a->A: ������ ���� �������
                auto_set = FALSE!!
        ~ �������� - ����-���  =relation /uselist=True (1-to-many, many-to-many)

    * ������������ �����:
        + 1. ����� �� StaticType-obj � SA-obj � ����, ��� ����������� ������ � ������������ �������.
            + ������, ����� �����
        - 2. ���� �� �� ������� StaticType-obj != SA-obj:
            ++������� �� ������ ����� �� �������������� - �������� ���������, None<>notSetYet, ������������ ���������
            --������������ .save/.load/(semi-deep-copy)+dirty ���� �� ����������� ��/���; �������������??
'''

#print 'builder...', __name__

from reflector import Reflector
from mapcontext import table_inheritance_types, MappingContext, issubclass
import walkklas
import relation
import sqlalchemy
import sqlalchemy.orm
import warnings


from config import config_components, config,  column4type, column4ID, table_namer

if not config_components.polymunion_from_SA:
    from polymunion import polymorphic_union
else:
    polymorphic_union = sqlalchemy.polymorphic_union
    #this cannot handle mixed inheritances


if config_components.no_generator:
    sa = sqlalchemy
    sa_mapper   = sa.orm.mapper
    sa_backref  = sa.orm.backref
    sa_relation = sa.orm.relation
    SrcGenerator = None
else:
    import sa_generator
    sa = sa_generator
    polymorphic_union = sa.duper4polymorphic_union( polymorphic_union,
                            no_kargs= dict(
                                allow_empty_typecolname= False,     #same as below
                                dont_alias_selects= True,
                            ))
    sa.Column = sa.duper2( sqlalchemy.Column)
    sa.ForeignKey= sa.duper2( sqlalchemy.ForeignKey)
    sa_mapper   = sa.mapper
    sa_backref  = sa.backref
    sa_relation = sa.relation
    SrcGenerator = sa.Printer

if not config_components.polymunion_from_SA:
    def _polymorphic_union( table_map, typecolname, aliasname, *args_ignore):
        if config.lower_pu: aliasname = aliasname.lower()
        return polymorphic_union( table_map, typecolname, aliasname,
                allow_empty_typecolname =False,
                dont_alias_selects  =True,
            )
else:
    def _polymorphic_union( table_map, typecolname, aliasname, inheritype):
        if config.lower_pu: aliasname = aliasname.lower()
        if inheritype == table_inheritance_types.JOINED:
            typecolname = None
        return polymorphic_union( table_map, typecolname, aliasname )


###########################################



def make_klas_selectable( mapcontext, klas, tables, test =False):
    '''construct the selectable for extracting objects of
    exactly this klas (and not subklasses);
    for all cases of inheritance-represention (concrete,multitable,single)
    '''
    joined_tables = []
    base_klas = klas
    while True:     #go toward base, stop on first concrete-table
        tbase = tables[ base_klas]
        joined_tables.insert( 0, tbase)
        base_klas, inheritype = mapcontext.base4table_inheritance( base_klas)
        if inheritype == table_inheritance_types.CONCRETE:
            break

    j = joined_tables[0]
    if test:
        jtest = joined_tables[0].name

    if len(joined_tables)>1:
        for t in joined_tables[1:]:
            # explicit, allow other relations via id
            other_table = isinstance( j, sqlalchemy.Table) and j or j.right
            j = sa.join( j, t,
                    column4ID( t) == column4ID( other_table) )
            if test:
                jtest += '.join( '+t.name
                #jtest += ' /on '+ other_table.name +'.id'
                jtest += ' )'

    jfiltered = exprfilter = None
    is_non_concrete_inherited = mapcontext.is_direct_inherited_non_concrete( klas)
    if is_non_concrete_inherited:   # -> ������ �� �� ������ �� ���; correlate=False � � ����� ������
        #X.select(X.atype==X)
        exprfilter = column4type( tbase) == klas.__name__
        if isinstance( j, sqlalchemy.sql.Join): #if len(joined_tables)>1
            jfiltered = j.select( exprfilter, fold_equivalents=True)
        else:
            jfiltered = j.select( exprfilter)

        jfiltered = jfiltered.alias( 'bz4' + table_namer( klas) )
        if test:
            jtest += '.select( '+tbase.name+ '.typ=='+klas.__name__ + ' )'
    else:
        jfiltered = j

    if test: j = jtest
    return dict( filtered= jfiltered, plain= j,
                    filter= exprfilter,   #fold_equivalents=True) XXX???
                    base_table= tbase,
                )

_subklas_selectable_doc = '''
    ������������: B ��������� �:
    ��� ������ ������ ��� ���� (��������) �������, � ������ =������������
    �� �������� �� ������ ������� + ������ ���/�������������,
    � �� ���� ��� �� ����� �����, � ������ ��-������ ������ =NULL
    � ������ single_table ���� � ���������; ����� �� ����� (���������) ������� ���� union.

    /:  concrete_table - B ������� ������ ������ �� A (� � B �� ������ ����������);
            id-���� �� � � B �� ������ ����������;
            ���������������/atype �� �������� ���� ��������� �� ��������� �� union-� ;

    //: joined_table - B ��� ���� �������������� �� ������; +join ��� �
            A ������ �� ��� ���� atype, �� ����� �� ������� ���� (�������������);
            � ������� ������ id-�� �� � � B; ���������������/atype � �.atype

    *:  single_table - B �� ���������� ���� ������� - �������� � ������ �� � �;
            (��� � ���� �� ���������� ���� �������, ������ ���� � ������� ���� ����� ����������)
            A ������ �� ��� ���� atype, �� ����� �� ������� ���� (�������������);
            � ������� ������ id-�� �� � � B; ���������������/atype � �.atype;
            ����� ���������� �� ������ � �, B �� �� ����� �� ������� ���� ����� - ������������� �
            � ������ ���� ����� ����������� �� �

    �������� �������� �� �������� ���� �� ���������� �� �������
    (not concrete_table) ��� �� (concrete_table)



������� 0. ������� �����������, �� ������ ���� (���� ��������) - ��
variant 0. same inheritance, on all levels (no mixing)
           A                      A                                          A
          / \                   // \\                                       * *
         B   D                 B     D                                     B   D
        /                     //                                          *
       C                     C                                           C
                            �.atype= (A,B,C,D)                          �.atype= (A,B,C,D)

    A.only = �              A.only = �.select( A.atype==A)              A.only = �.select( A.atype==A)
    B.only = B              B.only = A.join(B).select( A.atype==B)      B.only = A.select( A.atype==B)
    C.only = C              C.only = A.join(B).join(C)                  C.only = A.select( A.atype==C)
    D.only = A              D.only = A.join(D)                          D.only = A.select( A.atype==D)

������� 1. ������� �����������, ��������� ��� ������ � ����� ������
variant 1. mixed inheritance, different within a node and between the levels
          A                                       A
         / \\                                    / \\
        B   D                                   B   D
       / \\                                    / *   *
      C   E                                   C   E   F
                                                 //  //\
                                                 P   Q  R
                                                *
                                               S
    �.atype = (�,D)                     �.atype = (�,D,F,Q)
    B.atype = (B,E)                     B.atype = (B,E,P,S)

    A.only = �.select( A.atype==A)      A.only = �.select( A.atype==A)
    B.only = B.select( B.atype==B)      B.only = B.select( B.atype==B)
    C.only = C                          C.only = C
    D.only = A.join(D)                  D.only = A.join(D).select( A.atype==D)
    E.only = B.join(E)                  E.only = B.select( B.atype==E)
                                        F.only = A.join(D).select( A.atype==F)
                                        R.only = R
                                        Q.only = A.join(D).select( A.atype==Q).join(Q)
                                        P.only = B.select( B.atype==P).join(P)
                                        S.only = B.select( B.atype==S).join(P)

������� 2. ������� �����������, �� ������� � ���� ����� (�������� � ���������� �����)
variant 2. mixed inheritance, but same within a node (and different between nodes)
           A                                  A                                   A
          / \                               // \\                               // \\
         B   D                             B     D                             B     D
       //\\                               / \                                // \\
      C   E                              C   E                              C    E
     / \                               //\\                                / \
    P   Q                              P  Q                               P   Q
  B.atype = (B,C)                   A.atype= (A,B,D); C.atype= (C,P,Q)   A.atype= (A,B,C,D,E)

  A.only= �                         A.only= �.select( A.atype==A)        A.only= �.select( A.atype==A)
  B.only= B.select( B.atype==B)     B.only= A.join(B)                    B.only= A.join(B).select( A.atype=B)
  C.only= B.join(C)                 C.only= C.select( C.atype==C)        C.only= A.join(B).join(C)
  D.only= D                         D.only= A.join(D)                    D.only= A.join(D)
  E.only= B.join(E)                 E.only= E                            E.only= A.join(B).join(E)
  P.only= P                         P.only= C.join(P)                    P.only= P
  Q.only= Q                         Q.only= C.join(Q)                    Q.only= Q


� ����� ������ ������ ��� joined_table ���� �� �� ������� union-a:
in some special cases with joined_table, the union can be avoided:
 class A: pass
 class B(A): pass
 class C(B): pass
 A_join = A_table.outerjoin( B_table).outerjoin( C_table)
 B_join = A_table.join( B_table).outerjoin( C_table)
 A_mapper = mapper( A, A_table, select_table= A_join,
    polymorphic_on= A_table.c.type, polymorphic_identity= 'p')
 B_page_mapper = mapper( B, magazine_page_table,
    select_table= B_join, inherits= A_mapper, polymorphic_identity= 'm')
 C_mapper = mapper( C, C_table,
    inherits= B_mapper, polymorphic_identity= 'c')
���� ������ �� �� ������ ���-���� �� � ���� ��� �� ��������� ��� ���������� �������.
this is not used for now, as it is not clear how it combines in branched trees.
'''




###############################
def get_DBCOOK_references( klas):
    refs = getattr( klas, '_DBCOOK_references', {} )
    klas._DBCOOK_references = refs
    return refs

def make_table_column4id_fk( column_name, other_klas,
                            type =None, fk_kargs ={}, **column_kargs):
    dbg = 'column' in config.debug
    if dbg: print 'make_table_column4id_fk', column_name, '->', other_klas.__name__
    assert type
    assert other_klas
    fk = sa.ForeignKey(
                table_namer( other_klas)+'.'+column4ID.name,
                **fk_kargs
            )
    if dbg: print '  foreignkey', column_name, column_kargs, fk, fk_kargs

    #if column_kargs.get( 'nullable'): column_kargs['autoincrement'] = False
    c = sa.Column( column_name,
                type,
                fk,     #must be in *args
                autoincrement= False,       #meaningless, regardless nullable or not
                **column_kargs  #typemap_kargs
            )
    if dbg: print '    = ', repr(c)
    return c

def make_table_column4struct_reference( klas, attrname, attrklas, mapcontext, **column_kargs):
#    print '  as_reference', attrname,attrklas
    #if column_kargs.get( 'primary_key') and column_kargs.get( 'nullable'):
    #    column_kargs.update( column4ID.typemap4pkfk)
    dbg = 'column' in config.debug
    if dbg: print klas,':',
    c = make_table_column4id_fk(
            column4ID.ref_make_name( attrname),
            other_klas = attrklas,
            type = column4ID.typemap['type'],
            **column_kargs
        )
    return c




def make_table_columns( klas, builder, fieldtype_mapper, name_prefix ='', ):
    dbg = 'column' in config.debug
    if dbg: print 'make_table_columns', klas, name_prefix
    mapcontext = builder.mapcontext
    columns = []
    id_columns = set()

    reflector = mapcontext.reflector
    base_klas, inheritype = mapcontext.base4table_inheritance( klas)
    is_joined_table = (inheritype == table_inheritance_types.JOINED)
    indexes = mapcontext.indexes( klas)
    defaults = mapcontext.defaults( klas)
    nonnullables = mapcontext.nonnullables( klas)

    refs = get_DBCOOK_references( klas)
    assert base_klas or not is_joined_table
    for attr,typ in reflector.attrtypes( klas).iteritems():
        if is_joined_table:
            #joined_table: subclass' tables consist of extra attributes -> joins
            if attr in reflector.attrtypes( base_klas):
                if dbg: print '  inherited:', attr
                continue
        if dbg: print '  own:', attr

        #else: 'concrete_table' - each class OWN table
        k = name_prefix + attr
        is_substruct = reflector.is_reference_type( typ)
        if is_substruct:
            attrklas = is_substruct[ 'klas']
            if not is_substruct[ 'as_value']:
                if dbg: print '  as_reference', k,typ
#                print klas.__name__, k, typ
                assoc_kargs, assoc_columner= relation.is_association_reference( klas, typ, attrklas, )
                nullable = is_substruct[ 'nullable']
                if nullable !='default':
                    assoc_kargs.update( nullable=nullable)
                c = make_table_column4struct_reference( klas, k, attrklas, mapcontext, **assoc_kargs)
                if assoc_columner: assoc_columner( c, cacher=builder)
                columns.append( c)
                id_columns.add( k)
                refs[k] = attrklas
            else:   #inline_inside_table/embedded
                #... ���������� �� �������� �� �������������� ���� ������ ����
                if dbg: print '  as_value', k,typ
                raise NotImplementedError

        else:   #plain non-struct attribute, no foreign-keys
            if dbg: print '  plain non-struct attribute', k, typ
            mt = fieldtype_mapper( typ )
            if dbg: print '    ->', mt
            mt = mt.copy()      #just for the sake of it
            constraints = mt.pop( 'constraints', ())
            type = mt.pop( 'type' )
            c = sa.Column( k, type,
                    index= k in indexes,
                    default= defaults.get( k, None),
                    nullable = k not in nonnullables,
                    *constraints, **mt )
            if dbg: print '    = ', repr(c)
            columns.append( c)

    ## column4type
    if mapcontext.need_typcolumn( klas):
        c = sa.Column( column4type.name, **column4type.typemap_() )
        if dbg: print '  need_typcolumn', c
        columns.append( c)


    ## separate column4ID primary_key?
    #only 1 primary_key allowed, so options are:
    # - no primary_keys whatsoever
    # - predefined primary_key columns, and no need for explicit db_id
    # - db_id as primary_key if joined_table or being referenced;
    #   all else wanna-be-primary-keys become just unique constraints
    # note: sqlite cannot have composite partialy-autoincrementing primary key

    uniques = []
    primary_key = [ c for c in columns if c.primary_key]
    needs_id_primary_key = is_joined_table or mapcontext.needs_id( klas) # needs such, because of being referenced / inherits via joined_table
    #XXX subtle: mapcontext.needs_id may return None,False,True
    if not primary_key or needs_id_primary_key:
        if dbg: print '  invent primary_key', column4ID.name
        c = None
        if is_joined_table:
            c = make_table_column4id_fk( column4ID.name, base_klas, **column4ID.typemap)
        elif needs_id_primary_key is not False:     #allow no primary key AND no dbid XXX?
            c = sa.Column( column4ID.name, **column4ID.typemap_() )
        if c is not None:
            columns.append( c)
            if primary_key:     #convert it to just uniq constraint
                for c in primary_key: c.primary_key = False
                if dbg: print '  uniq-from-primarykey:', key
                uniques.append( sa.UniqueConstraint( *[d.name for d in primary_key]))

    if 0:   #uniques may not be ready yet - assoc.walk_links??
        #make_table_uniques( klas)
        for u in mapcontext.uniques( klas):
            key = [ getattr( c, 'name', c) for c in u ]
            key = [ (k in id_columns and column4ID.ref_make_name( k) or k) for k in key ]
            if dbg: print '  uniq:', table, ':', key
            uniques.append( sa.UniqueConstraint( *key) )

    ## check for duplicate column-names/constraint-names
    chk = set()
    for c in columns:
        key = c.name    #type
        assert key not in chk, 'multiple columns named '+repr( key)
        chk.add( key)

    return columns + uniques

def make_table_uniques( klas, mapcontext, table =None ):
    dbg = 'table' in config.debug
    if dbg: print 'make_table_uniques', klas
    uniques = []
    id_columns = get_DBCOOK_references( klas)
    for u in mapcontext.uniques( klas):
        key = [ getattr( c, 'name', c) for c in u ]
        key = [ (k in id_columns and column4ID.ref_make_name( k) or k) for k in key ]
        if dbg: print '  uniq:', table or '', ':', key
        uc = sa.UniqueConstraint( *key)
        uniques.append( uc)
    if table:
        for uc in uniques:
            table.append_constraint( uc)
    return uniques

def make_table( klas, metadata, builder, **kargs):
    dbg = 'table' in config.debug
    if dbg: print '\n'+'make_table for:', klas.__name__, kargs
    columns = make_table_columns( klas, builder, **kargs)
    name = table_namer( klas)
    t = sa.Table( name, metadata, *columns )
    if dbg: print repr(t)
    return t

def fix_one2many_relations( klas, builder):
    dbg = 'table' in config.debug or 'relation' in config.debug or 'column' in config.debug
    if dbg: print 'make_one2many_table_columns', klas
    mapcontext = builder.mapcontext
    for attr_name,collection in mapcontext.iter_attr_local( klas, attr_base_klas= relation.Collection, dbg=dbg ):
        child_klas = collection.assoc_klas
        if isinstance( child_klas, str):
            try: child_klas = builder.klasi[ child_klas]
            except KeyError: assert 0, '''undefined relation/association class %(child_klas)r in %(klas)s.%(attr_name)s''' % locals()
        #one2many rels can be >1 between 2 tables
        #and many classes can relate to one child klas with relation with same name

        backrefname = collection.setup_backref( klas, attr_name)
        fk_column_name = backrefname
        fk_column = make_table_column4struct_reference( child_klas, fk_column_name, klas, mapcontext)
        if dbg: print '  attr:', attr_name, 'of child:', child_klas, '.', fk_column_name, '; fk_column:', repr(fk_column)
        child_tbl = builder.tables[ child_klas]
        child_tbl.append_column( fk_column)

        relation.relate( child_klas, klas, attr_name, fk_column, cacher=builder)
        get_DBCOOK_references( child_klas)[ backrefname] = klas


def make_mapper( klas, table, **kargs):
    dbg = 'mapper' in config.debug
    if dbg:
        print '\n'+'make_mapper for:', klas.__name__
        print '  table=', table, '\n  '.join( '%s=%s' % kv for kv in kargs.iteritems())

    m = sa_mapper( klas, table, **kargs)
    return m

class FKeyExtractor( dict):
    def __init__( me, klas, table, mapcontext, tables):
        dict.__init__( me)
        me.table = table
        me._add_fkeys( table)
        subklasi = mapcontext.subklasi[ klas]
        if '''this is to propagate post_update of a link to concrete-inherited bases AND subklasi,
            because of the required relink'ing of concrete-inherited references in SA 0.3.4
            ''':
            #bases
            kl = klas
            while kl:
                base_klas, inheritype = mapcontext.base4table_inheritance( kl)
                if base_klas and inheritype == table_inheritance_types.CONCRETE:
                    kl = base_klas
                    me._add_fkeys( tables[ kl])
                else: break
            #subklasi
            for kl in subklasi:
                if kl is klas: continue
                base_klas, inheritype = mapcontext.base4table_inheritance( kl)
                assert base_klas
                if inheritype == table_inheritance_types.CONCRETE:
                    me._add_fkeys( tables[ kl])

    def _add_fkeys( me, table ):
        for fk in table.foreign_keys:
            c = fk.parent   #this-table column
            attr = column4ID.ref_strip_name( c.name)
            me.setdefault( attr, []).append( fk)

    def get_relation_kargs( me, k):
        fks = me.get( k, None)
        if not fks: return {}
        post_update = 0
        fk = None
        for f in fks:
            if f.parent.table is me.table:
                fk = f
            post_update += f.use_alter
        assert fk
            #|= the respective fk on any of concrete inherited/inheriting relation because of relinking
        rel_kargs = dict(
                post_update = bool(post_update),
                primaryjoin = (fk.parent == fk.column),
                foreign_keys = fk.parent,
                remote_side = fk.column,
            )
        return rel_kargs

def make_mapper_props( klas, mapcontext, mapper, tables ):
    'as second round - refs can be cyclic'
    dbg = 'mapper' in config.debug or 'prop' in config.debug
    reflector = mapcontext.reflector

    need_mplain = bool( not config_components.non_primary_mappers_dont_need_props
                    and mapper.plain is not mapper.polymorphic_all)

    refs = get_DBCOOK_references( klas)
    for m in [mapper.polymorphic_all] + need_mplain*[ mapper.plain]:
        if dbg: print 'make_mapper_props for:', klas.__name__, m
        table = m.local_table

        fkeys = FKeyExtractor( klas, table, mapcontext, tables)

        base_klas, inheritype = mapcontext.base4table_inheritance( klas)
        for k,typ in reflector.attrtypes( klas).iteritems():
            if base_klas and k in reflector.attrtypes( base_klas):
                if inheritype != table_inheritance_types.CONCRETE:
                    if dbg: print '  inherited:', k
                    continue
                else:
                    if dbg: print '  concrete-inherited-relink:', k
            else:
                if dbg: print '  own:', k
            is_substruct = reflector.is_reference_type( typ)
            if is_substruct:
                attrklas = is_substruct[ 'klas']
                if is_substruct[ 'as_value']:
                    raise NotImplementedError
                else:
                    if m.non_primary:
                        if dbg: print ' non-primary, reference ignored:', k    #comes from primary mapper
                        continue

                    rel_kargs = fkeys.get_relation_kargs( k)

                    if (issubclass( attrklas, klas)         #not supported by SA + raise
                            or issubclass( klas, attrklas)  #seems not supported by SA + crash
                        ):
                        lazy = True
                    elif config.force_lazy:
                        lazy = True
                    else:
                        lazy = getattr( attrklas, 'DBCOOK_reference_lazy', False
                                        ) or is_substruct[ 'lazy']
                        if lazy == 'default':
                            lazy = config.default_lazy

                    rel_kargs[ 'lazy'] = lazy
                    rel_kargs[ 'uselist'] = False
                    if dbg: print '  reference:', k, attrklas, ', '.join( '%s=%s' % kv for kv in rel_kargs.iteritems() )
                    m.add_property( k, sa_relation( attrklas, **rel_kargs))
                    assert refs[k] == attrklas

class _MapExt( sqlalchemy.orm.MapperExtension):
    def __init__( me, klas): me.klas = klas
    def before_insert( me, mapper, connection, instance):
        assert instance.__class__ is not me.klas, 'load_only_object - no save: ' + str( me.klas)+ ':'+ str( instance.__class__) + ' via ' + str(mapper)
        return sqlalchemy.orm.EXT_CONTINUE
    before_update = before_delete = before_insert

class Builder:
    reflector = None    #Reflector()    #override - just a default
    Base = MappingContext.base_klas     #override - just a default

    SETordered  = sqlalchemy.util.OrderedSet
    DICTordered = sqlalchemy.util.OrderedDict
    DICT = dict
    SrcGenerator = SrcGenerator
    table_inheritance_types = table_inheritance_types

    def __init__( me, metadata, namespace, fieldtype_mapper,
                base_klas =None,
                force_ordered =False,
                reflector =None,

                debug = None,       #same as config.debug
                generator =None,    #None->see config.generate; True->use SrcGenerator; anything non-empty, use it as the src_generator
                only_table_defs = False,    #stop after metadata.tables setup and no metadata.create_all
                only_declarations= False,   #do not metadata.create_all - work on empty metadata
            ):
        #config/setup
        if debug is not None:
            config.debug = debug

        if generator is None: generator = config.generate
        if generator is True:
            me.generator = callable( SrcGenerator) and SrcGenerator()
        else:
            me.generator = generator

        if reflector is None: reflector = me.reflector
        assert isinstance( reflector, Reflector)

        if base_klas is None: base_klas = me.Base
        assert base_klas

        mc = MappingContext()
        mc.base_klas = base_klas
        mc.reflector = reflector
        me.mapcontext = mc

        if force_ordered:
            me.DICT = mc.DICT = me.DICTordered
            mc.SET  = me.SETordered

        #get/scan class declarations to be processed
        walkklas._debug = 'walk' in config.debug
        namespace = walkklas.walker( namespace, reflector, base_klas)

        me._load_klasi( namespace)
        me._cleanup_klasi()     #here? or after resolve_forward_references?
        relation.resolve_assoc_hidden( me, me.klasi)
        reflector.resolve_forward_references( me.klasi, base_klas)

        if force_ordered:
            me.klasi = me.DICT( sorted( me.klasi.items() ))

        #fieldtype_mapper
        if isinstance( fieldtype_mapper, (list, tuple)):
            # [ Type ] -> obtaining sa.Column kargs from Type.column_def
            fieldtype_mapper = dict( (typ,None) for typ in fieldtype_mapper )
        if isinstance( fieldtype_mapper, dict):
            # { Type: one-of
            #       instance/subclass of sa.AbstractType to be used as type= for sa.Column
            #       dict( kargs-for-sa.Column )
            #       func returning above dict/kargs
            #       None -> obtain any of the above from Type.column_def
            from sqlalchemy.types import AbstractType
            def fm( typ):
                r = fieldtype_mapper[ typ.__class__ ]
                if r is None: r = typ.column_def
                if isinstance( r, AbstractType) or issubclass( r, AbstractType):
                    r = dict( type = r)
                elif callable(r): r = r( typ)
                return r
        else:
            fm = fieldtype_mapper
        assert callable( fm)

        #work
        me.make_subklasi()

        me.make_tables( metadata, fieldtype_mapper=fm,
                            only_table_defs= only_table_defs or only_declarations )
        if not only_table_defs:
            me.make_mappers()

    def _load_klasi( me, namespace_or_iterable):
        try: itervalues = namespace_or_iterable.itervalues()        #if dict-like
        except AttributeError: itervalues = namespace_or_iterable   #or iterable

        #me.aliasi = dict() XXX TODO
        klasi = me.DICT()
        for typ in itervalues:      #for k in getattr( namespace, '_order', itervalues):
            if me.mapcontext.mappable( typ):
                k = typ.__name__
                assert k and not k.startswith('__')
                klasi[ k] = typ     #aliases are ignored; same-name items are overwritten
        me.klasi = klasi

    def _cleanup_klasi( me):
        for klas in me.iterklasi():
            me.reflector.cleanup( klas)    #XXX this makes repeateable-over-same-clas plainwrap tests FAIL. see NO_CLEANUP there
            for k in '_DBCOOK_relations'.split():
                try: delattr( klas, k)
                except AttributeError: pass


    def iterklasi( me): return me.klasi.itervalues()
    def column4ID( me, klas):
        return column4ID( me.tables[ klas] )
    def itermapi( me, primary_only =False):
        #primary
        for m in me.mappers.itervalues():
            yield m.polymorphic_all
        if not primary_only:
            # non-primary mappers
            for m in me.mappers.itervalues():
                if m.plain is not m.polymorphic_all:
                   yield m.plain


    def make_subklasi( me):
        me.mapcontext.make_subklasi( me.iterklasi() )


    def make_tables( me, metadata, only_table_defs =False, **kargs):
        me.tables = me.DICT()
        for klas in me.iterklasi():
            me.tables[ klas] = make_table( klas, metadata, me, **kargs)
        for klas in me.iterklasi(): #to be sure all tables exists already
            fix_one2many_relations( klas, me)
        for klas in me.iterklasi(): #to be sure all tables+references exists already
            make_table_uniques( klas, me.mapcontext, me.tables[ klas])

        from table_circular_deps import fix_table_circular_deps
        cut_fkeys = fix_table_circular_deps(
                            metadata.tables.values(),
                            count_multiples = True,
                            exclude_selfrefs= False,
                            dbg= int('table' in config.debug) + 2*int('graph' in config.debug)
                        )

        #for src-generator/generator
        for fkey in cut_fkeys:
            if hasattr( fkey,'tstr'):
                fkey.tstr.kargs.update( dict( use_alter=True, name=fkey.name))

        def getprops( klas):
            return [ column4ID.name ] + list( me.reflector.attrtypes( klas).iterkeys()) #if not k.startswith('link')]

        try:
            if not only_table_defs:
                metadata.create_all()
        finally:
            if me.generator:
                me.generator.ptabli( metadata)
                me.generator.pklasi( me.mapcontext.base_klas, me.iterklasi(),
                        getprops= getprops
                    )


    class Mapper:
        def __init__( me):
            me.plain = me.polymorphic_all = me.polymorphic_sub_only = None

    def make_klas_selectable( me, klas, **kargs):
        return make_klas_selectable( me.mapcontext, klas, me.tables, **kargs)

    def make_mappers( me, **kargs):
        me.mappers = me.DICT()
        iterklasi = [ mklas for mklas in me.iterklasi()
                        if not getattr( mklas, 'DBCOOK_hidden', None)
                    ]

        me.klas_only_selectables = me.DICT( (klas, me.make_klas_selectable( klas))
                                            for klas in iterklasi)

        try:
            for klas in iterklasi:
                me._make_mapper_polymorphic( klas, **kargs)

            for klas in iterklasi:    #table=me.tables[ klas],
                make_mapper_props( klas, me.mapcontext, me.mappers[ klas], me.tables )

            relation.make_relations( me, sa_relation, sa_backref, FKeyExtractor)
            sqlalchemy.orm.compile_mappers()
        finally:
            if me.generator:
                me.generator.pmapi( m.polymorphic_all for m in me.mappers.itervalues() )
                me.generator.pmapi( m.plain for m in me.mappers.itervalues()
                                            if m.plain is not m.polymorphic_all)
                me.generator.psubs( (m.polymorphic_sub_only, m.polymorphic_all) for m in me.mappers.itervalues()
                                            if m.polymorphic_sub_only)

    def _outerjoin_polymorphism( me, klas, subklasi, dbg):
        ss = me.klas_only_selectables[ klas ]
        j = ss['plain']
        tbase = ss['base_table']
        for sklas in subklasi:
            if sklas is klas: continue
            s_base_klas, s_inheritype = me.mapcontext.base4table_inheritance( sklas)
            if s_inheritype == table_inheritance_types.CONCRETE:  # or != JOINED ??XXX
                if dbg: print 'outer_join_ok not ok', sklas, s_inheritype
                return None
            t = me.tables[ sklas]
            j = sa.outerjoin( j, t, (column4ID( t) == column4ID( tbase)) )

        if dbg: print 'outer_join_ok', klas, ':', j, '\n',j.c
        outer_join_ok = True
        pjoin = j
        pjoin_key = column4type( tbase)
        return pjoin, pjoin_key


    def _make_mapper_polymorphic( me, klas, **kargs):
        if klas in me.mappers: return
        #polymorphic mapper - things of type klas AND all subtypes
        ''' ��������:
            �) 3 �������� ������������ (mapper) �� query_BASE_instances, query_ALL_instances, query_SUB_instances
                ��� �� � ���� ��� �� �� ������� �������������� ����� mapper-���
            �) 1 ��� (����������,��������-��������,������ ������ ������) �� query_ALL_instances,
                + ��.������ (pjoin().select) �� query_SUB_instances.
                + ��.������ (table.select) �� query_BASE_instances
              ���� �� ������ �� query_BASE_instances - ���� pjoin.atype ����� �� ���� � ���������;
            �) 1 ��� (����������,��������-��������,������ ������ ������) �� query_ALL_instances,
                ��.������ �� query_SUB_instances,
                � ����� (��-���������� - �� ��������!) �� query_BASE_instances.
            ��� ������������ �� � ��������, ���� _polymorphic_map - �� ���� �� �� ������ ��� ��� ����� ���� ��� �������
            #submappers = dict( (sklas.__name__, me.mappers[ sklas].plain) for sklas in subklasi.itervalues() if sklas is not excluded )
        '''
        dbg = 'mapper' in config.debug
        if dbg: print '\n--- _make_mappers', klas.__name__
        base_klas, inheritype = me.mapcontext.base4table_inheritance( klas)
        if dbg: print '  inherits', base_klas and base_klas.__name__, 'via', inheritype

        table = me.tables[ klas]
        subklasi = me.mapcontext.subklasi[ klas]
        assert klas in subklasi
        name = klas.__name__

        if 0:
            if 'some inherits this by table_inheritance_types.SINGLE':
                # ������ �� �� �������� �� subtables, �� �� �� ������� � �.atype=='�',
                # t.e. pjoin ���� �� ����� == table ->None � ������ ������
                pjoin_key = column4type( pjoin or table)

        subtables = None
        outer_join_ok = False
        if len( subklasi)>1:   #��� ����������
            if config_components.outerjoin_for_joined_tables_instead_of_polymunion:
                outer_join_ok = me._outerjoin_polymorphism( klas, subklasi, dbg)
            if outer_join_ok:
                pjoin, pjoin_key = outer_join_ok
            else:
                # ���� ������ �� ������� ��� ������ ������ - �������/ ������� �����������
                subtables = me.DICT(
                                    (sklas.__name__, me.klas_only_selectables[ sklas]['filtered'])
                                    for sklas in subklasi
                                        if me.mapcontext.has_instances( sklas)
                                )
                pjoin = _polymorphic_union( subtables.copy(), column4type.name, 'pu_'+name, inheritype)
                pjoin_key = column4type( pjoin)
        else:
            pjoin = None
            pjoin_key = None

        base_mapper = None
        if base_klas:
            if base_klas not in me.mappers:
                me._make_mapper_polymorphic( base_klas, **kargs)
            base_mapper = me.mappers[ base_klas]

        m = me.mappers[ klas] = me.Mapper()

        inherit_condition = None
        is_concrete = False
        if base_mapper:
            if inheritype == table_inheritance_types.JOINED:
                inherit_condition = (column4ID( table) == column4ID( me.tables[ base_klas]))
            is_concrete = (inheritype == table_inheritance_types.CONCRETE)

        if inheritype == table_inheritance_types.SINGLE:
            #primary/all
            table = None
            pjoin = None
            pjoin_key = None
            #me_only
            t_only = THE_base_table_or_join.select( column4type( THE_base_with_type) == name )
            #subclasses_only
            subatypes = [ sk.__name__ for sk in subklasi if sk != name]
            m.polymorphic_sub_only = THE_table.select( column4type( THE_table).in_( *subatypes) )
            #also, explicitly list all properties to be included/excluded from base_klas

        inherits= base_mapper and base_mapper.polymorphic_all or None
        is_pm = inherits and inherits.polymorphic_on or pjoin_key

        extension = None
        if not me.mapcontext.has_instances( klas):
            if dbg: print ' load-only - disable mapper.save/.delete'
            extension = _MapExt( klas)

        me.reflector.before_mapping( klas)      #eventualy hide klas.descriptors

        #primary, eventualy polymorphic_all if pjoin
        pm = make_mapper( klas, table,
                    polymorphic_identity= is_pm and name or None,
                    concrete= is_concrete,
                    select_table= pjoin,
                    polymorphic_on= pjoin_key,
                    inherits= inherits,
                    inherit_condition= inherit_condition,
                    extension = extension,
                )
        m.polymorphic_all = pm

        if pjoin:
            if 1<len( [ k for k in subklasi if k is not klas and
                        me.mapcontext.base4table_inheritance( k)[1] == table_inheritance_types.CONCRETE
                    ]):
                warnings.warn( 'polymorphism over concrete inheritance not supported/SA - queries may not work' )


        if pjoin:
            #non-primary, plain
            t = me.klas_only_selectables[ klas]['filtered']
            pm = make_mapper( klas,
                    table =t,
#                    polymorphic_identity= is_pm and name or None,
                    concrete= is_concrete,
                    non_primary= True,
                    extension = extension,
                )

        m.plain = pm

        if pjoin:
            if dbg: print ' non-primary, SUBclasses_only'
            if outer_join_ok:
                #non-mapper - primary over sub-union-select
                m.polymorphic_sub_only = ~ me.klas_only_selectables[ klas]['filter']
            else:
                #non-mapper - primary over sub-union-select
                subtables.pop( name, None)  #all but this
                m.polymorphic_sub_only = _polymorphic_union( subtables,
                                            #v04/r3515: m.polymorphic_all.polymorphic_on._label
                                            column4type.name,
                                            'psub_'+name,
                                            inheritype
                                        )

# vim:ts=4:sw=4:expandtab
