#$Id$
#s.dobrev 2k4

'''some additional python-reflection tools
- multilevel getattr/ setattr/ import /getitemer
- local vs see-through-hierarchy getattr
- fail-proof issubclass()
'''

def set_attrib( self, name, value, getattr =getattr, setattr=setattr):
    'setattr over hierachical name'
    if isinstance( name, basestring):
        name = name.split('.')
    name1 = name[-1]
    if len(name)>1:
        for a in name[:-1]:
            self = getattr( self, a)
    setattr( self, name1, value )
    #exec( 'self.'+name+'=value' )

def get_attrib( self, name, *default_value, **kargs):
    'getattr over hierachical name'
    if isinstance( name, basestring):
        name = name.split('.')
    _getattr = kargs.get( 'getattr', getattr)
    for a in name:
        try:
            self = _getattr( self, a)
        except AttributeError:
            if not default_value: raise
            return default_value[0]
    return self
    #if name.find('.')>0: return eval( 'self.'+name )
    #return getattr( self, name)

class get_itemer:
    '''dict simulator for hierarchical names/lookups:
       use: "%(a.b.c.d)s %(e)s" % get_itemer( locals() ) '''
    def __init__( me, d): me.d = d
    def __getitem__( me, k):
        names = k.split('.', 1)
        r = me.d[ names[0] ]
        if len(names)>1:
            r = get_attrib( r, names[1] )
        return r


#######
# getattr(klas) looks up bases! hence use __dict__.get

def getattr_local_instance_only( me, name, *default_value):
    'lookup attr in instance, and not in class/bases'
    try:
        return me.__dict__[ name]
    except KeyError:
        if not default_value: raise AttributeError, name
        return default_value[0]

def getattr_local_class_only( me, name, *default_value):
    'lookup attr in leaf class, and not in instance nor in bases'
    try:
        return me.__class__.__dict__[ name]
    except KeyError:
        if not default_value: raise AttributeError, name
        return default_value[0]

def getattr_local_instance_or_class( me, name, *default_value):
    'lookup attr in instance or leaf class, but not in base classes'
    try:
        return me.__dict__[ name]
    except KeyError:
        return getattr_local_class_only( me, name, *default_value)

#'lookup attr in instance, leaf class, or any bases
getattr_global = getattr

def getattr_in( me, local =True, klas =True, *a,**k):
    'lookup attr in all ways'
    if local and klas:
        return getattr_local_instance_or_class( me, *a,**k)
    if local:
        return getattr_local_instance_only( me, *a,**k)
    if klas:
        return getattr_local_class_only( me, *a,**k)
    return getattr_global( me, *a,**k)     #plain getattr with all the lookup

#######

def setattr_kargs( *args, **kargs):
    'may just copy the last line instead of calling here'
    assert len(args)==1
    x = args[0]
    for k,v in kargs.iteritems(): setattr( x, k, v)

########

def getattr_each_by_inheritance( klas, name,
        without_self =False,
        order_flattened =(),    #__mro__ by default; careful, this should be leaf-to-root
        getattr =getattr,   #=getattr: yields at first visible place (leaf-most)
                            #=getattr_local_instance_only: yields at place of declaration (root-most)
    ):
    '''for rich multiple inheritance, define things locally, then use this to collect them all
       e.g. many have local setup() methods - single setup_all() can call them all without omissions
    '''
    used = set()
    notfound = used
    for k in order_flattened or klas.__mro__:
        k = k or klas   #None means self
        if without_self and k is klas: continue
        f = getattr( klas, name, notfound)
        if f is not notfound and f not in used:
            used.add(f)
            yield f

########

def flatten_vars( klas, ignore_hidden=True):
    res = {}
    for dic in reversed( [ vars(k) for k in klas.mro() ] ):
        res.update( dic)
    if ignore_hidden:
        return dict( (k,v) for k,v in res.iteritems() if not k.startswith('__'))
    return res


# util/base.py
__issubclass = issubclass
def issubclass( obj, klas):
    'fail/fool-proof issubclass() - works with ANY argument'
    from types import ClassType
    return isinstance( obj, (type, ClassType)) and __issubclass(obj, klas)


def isiterable( obj, string_is_iterable =False):
    if isinstance( obj, basestring):
        return string_is_iterable
    try:
        x = iter( obj)
    except TypeError:
        return False
    return True


def iscollection( obj):
    return isinstance( obj, (list, tuple, set))

########
# util/module.py

def import_fullname( name, last_non_modules =0, **kargs):
    'replacement of __import__ returning the leaf module'
    subnames = name.split('.')
    if last_non_modules:
        name = '.'.join( subnames[:-last_non_modules])
    m = __import__( name, **kargs)
    for k in subnames[1:]: m = getattr(m,k)
    return m

def find_valid_fullname_import( paths, last_non_modules =1):
    'search for a valid attribute path, importing them if needed'
    if isinstance( paths, basestring): paths = paths.split()
    for p in paths:
        try:
            return import_fullname( p, last_non_modules=last_non_modules)
        except Exception,e:
#            print e
            pass
    assert 0, 'cant find any of ' + str(paths)

# vim:ts=4:sw=4:expandtab
