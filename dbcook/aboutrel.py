#$Id$
# -*- coding: cp1251 -*-

'''sqlalchemy
1toN:
    containerthis: getattr( prop.parent.class_, prop.key)
      this: getattr( prop.parent.class_, prop.local_side[0])
      <- other: getattr( prop.mapper.class_, prop.remote_side[0])
    other: getattr( prop.mapper.class_, ??????)
*to1:
    this: getattr( prop.parent.class_, prop.key)
      this: getattr( prop.parent.class_, prop.local_side[0])
      -> other: getattr( prop.mapper.class_, prop.remote_side[0])
    containerother: getattr( prop.mapper.class_, ??????)
m2m: hidden
    containerthis: getattr( prop.parent.class_, prop.key)
      this: getattr( prop.parent.class_, prop.local_side[0])
        <- midthis: getattr( prop.secondary, prop.remote_side[0])
        midother: getattr( prop.secondary, prop.remote_side[1])
      -> other: getattr( prop.mapper.class_, prop.local_side[1])
    containerother: getattr( prop.mapper.class_, ??????)
m2m: explicit/assocproxy
  1toN
    containerthis: getattr( prop.parent.class_, prop.key)
      this: getattr( prop.parent.class_, prop.local_side[0])
      <- midthis: getattr( prop.mapper.class_, prop.remote_side[0])
    midthis: getattr( prop.mapper.class_, ??????)
  Nto1
    midother: getattr( prop.parent.class_, prop.key)
      midother: getattr( prop.parent.class_, prop.local_side[0])
      -> other: getattr( prop.mapper.class_, prop.remote_side[0])
    containerother: getattr( prop.mapper.class_, ??????)
'''

class about_relation( object):
    '''usage:
        a = about_relation(x)
        print a.this, a.this.klas, a.this.name, a.this.has_many
        print a.other, a.other.klas, a.other.name, a.other.has_many
        if a.this.has_many:
            assert a.ownedside is a.otherside
            assert a.ownerside is a.thisside
        else:
            assert a.ownerside is a.otherside
            assert a.ownedside is a.thisside
        '''

    __slots__ = ''' _klas_attr no_backref
        thisside otherside midthis midother
        '''.split()

    class _About( object):
        __slots__ = '''klas name attr has_many column'''.split()
        @property
        def cardinality( me): return me.has_many and '1' or 'N'
        def __str__( me):
            if not me.column:
                assert me.has_many
            if me.klas: r = '%s.%s' % ( me.klas.__name__, me.name)
            else:
                assert not me.name
                r = None
            return '( %s /%s)' % ( r, me.column)
        @property
        def anyname( me): return me.name or me.column.key
        @property
        def anyexpr( me): return me.attr and me.attr.expression_element() or me.column

        def __init__( me, prop =None):
            for a in me.__slots__: setattr( me, a, None)
            if prop:
                me.has_many = bool( prop.secondary) or prop.uselist
                #print 'AAAAAAAAAAAA', prop, prop.secondary, prop.uselist, me.has_many, prop.backref
                me.klas = prop.parent.class_    #same as impl.class_
                me.name = prop.key
                me.column = prop.local_side[0]


    @property
    def ownerside( me):
        'only for 1:many/many:1'
        if me.thisside.has_many == me.otherside.has_many: return None
        return me.thisside.has_many and me.thisside or me.otherside
    @property
    def ownedside( me):
        'only for 1:many/many:1'
        if me.thisside.has_many == me.otherside.has_many: return None
        return me.thisside.has_many and me.otherside or me.thisside


    @property
    def cardinality( me):
        r = [ me.thisside.cardinality, me.otherside.cardinality ]
        #if me.midthis: r.insert( 1, me.middle)
        return ':'.join( r)


    def __str__( me):
        r = me.__class__.__name__[:5]+ ' %s %s this=%s / other=%s: %s' % (
                    not me.no_backref and 'backref' or 'no_backref',
                    me.thisside,
                    me.thisside.has_many  and 'collection' or 'reference',
                    me.otherside.has_many and 'collection' or 'reference',
                    me.otherside,
                )
        if me.midthis:
            r += '\n via %s / %s' % ( me.midthis, me.midother )
        return r

    def __init__( me, klas_attr_or_klas, attr_name =None):
        if attr_name is None: klas_attr = klas_attr_or_klas
        else: klas_attr = getattr( klas_attr_or_klas, attr_name)
        try:
            prop = klas_attr.property
            mapper = prop.mapper
        except AttributeError, e:
            assert 0, 'not a relation klas_attr: '+ repr( klas_attr) + ' / ' + str( klas_attr)

        #me._klas_attr = klas_attr
        #TODO: try on 1:1/backref and n:n

        me.no_backref = None
        this = me.thisside  = me._About( prop)
        #print 'AAAAAAAAAAAA', prop, prop.secondary, prop.uselist, me.has_many, prop.backref
        this.attr = klas_attr
        assert klas_attr is getattr( this.klas, this.name)

        if prop.secondary:
            mthis = me.midthis = me._About()
            mother= me.midother= me._About()
            mthis.column  = prop.remote_side[0]
            mother.column = prop.remote_side[1]
        else: me.midthis = me.midother = None

        #'other': #slave
        revprop = prop._reverse_property
        other = me.otherside = me._About( revprop)
        if revprop is not None:
            #print 'BBBBBBBBBBBB', revprop, revprop.secondary, revprop.uselist, revprop.backref
            me.no_backref = False
            assert other.klas is mapper.class_
        else:
            other.klas = mapper.class_
            other.has_many = bool( prop.secondary) or not this.has_many
            if 0:
                print 'ZZZZZZZ', prop
                for k in '''
                        target secondary remote_side local_side
                        '''.split():
                    a = getattr( prop, k)
                    if isinstance( a, set): a = ', '.join( str(s) for s in a)
                    print ' .'+ k, ' \t', a

            me.no_backref = True
            if not other.has_many:
                    #ok on 1:m
                    #not ok on m:m - see local_side/_opposite_side but those are db_id
                if prop.secondary:
                    other.column = prop.local_side[ 1]
                else:
                    other.column = prop.remote_side[0]
            other.name = None
        other.attr = other.name and getattr( other.klas, other.name) or None

def about_relation_assoc_explicit( ab):
    assocklas = ab.otherside.klas
    midthis_attr = ab.otherside.name
    assert midthis_attr, 'cannot guess otherside, unknown midthis: %(ab)s' % locals()
    oattr = None
    from sqlalchemy.orm.properties import PropertyLoader
    for attr in ab.thisside.attr.property.mapper.iterate_properties: #assocklas.walk_links():
        if not isinstance( attr, PropertyLoader): continue
        if attr.key == midthis_attr: continue
        else:
            assert not oattr, 'cannot guess otherside for more than 2 links in %(assocklas)s' % locals()
            oattr = attr.key
    assert oattr, '%(oattr)r, %(xx)s' % locals()
    other = about_relation( assocklas, oattr)
    ab.midthis = ab.otherside
    ab.midother= other.thisside
    ab.otherside = other.otherside
    return ab


#return parent_klas._DBCOOK_relations[ attr]   #needs flatening from all the inh-classes

#klas_attr.impl.* thisside
#print  prop._reverse_property - needs backref
#print  prop._reverse_property.impl.key  - otherside name, needs backref
#print  prop.backref.key  - otherside attrname, needs backref
# prop.remote_side - otherside , set of columns

# vim:ts=4:sw=4:expandtab
