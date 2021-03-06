
from tests.util.context import *
if USE_STATIC_TYPE:
    Base.auto_set = False
else:
    from svd_util.attr import setattr_karg
    class Base( Base):
        __init__ = setattr_kargs

SAdb.config.getopt()
print 'config:', SAdb.config

def tsingle():
    class Kid( Base): name = Text()
    class Parent( Base):
        things  = orm.Collection( Kid)
    return locals()

def t2collects():
    class Kid( Base): name = Text()
    class Parent( Base):
        things  = orm.Collection( Kid)
        mings   = orm.Collection( Kid)
    return locals()

def t3inheritparent():
    class Kid( Base): name = Text()
    class Parent( Base):
        things  = orm.Collection( Kid)
    class Parent2( Parent):
        DBCOOK_inheritance = 'joined'
        a = Text()
    return locals()

for namespacer in tsingle, t2collects, t3inheritparent:
    sa = SAdb()
    sa.open( recreate=True)
    print '---', namespacer.__name__
    types = namespacer()
    Kid = types['Kid']
    sa.bind( types, base_klas= Base )

    s= sa.session()

    parentklas = types.get( 'Parent2', types[ 'Parent'] )
    use_mings = 'mings' in dir( parentklas)

    parent = parentklas()
    for i in range(3):
        p = Kid( name= 'a'+str(i) )
        parent.things.append( p)
        if use_mings:
            p = Kid( name= 'b'+str(i) )
            parent.mings.append( p)

    op = ['a'+str(i) for i in range(3) ]
    os = ['b'+str(i) for i in range(3) ]

    sa.saveall( s, parent)
    s.flush()
    assert [ k.name for k in parent.things ] == op
    if use_mings:
        assert [ k.name for k in parent.mings  ] == os

    s.clear()
    print list( s.query( parentklas) )
    parent = s.query( parentklas).first()
    print ' collection:', parent.things
    if use_mings: print ' collect2:', parent.mings

    assert [ k.name for k in parent.things ] == op
    if use_mings: assert [ k.name for k in parent.mings  ] == os

    sa.destroy()

# vim:ts=4:sw=4:expandtab
