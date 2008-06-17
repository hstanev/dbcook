#$Id$
# -*- coding: cp1251 -*-
from engine.testutils import testMain
from engine.testbase import Case
from datetime import datetime
VERBOSE = 0

class _Timed2_withDisabled_protocol:
    '''testing only - Timed protocol for tests to use
        ALWAYS USE KEYWORD-ARGS ONLY!
    '''
    def get( me, trans, valid, with_disabled =False):
        return None or object
    def put( me, value, trans, valid, disabled =False):
        pass
    def getRange( me, trans, validFrom, validTo, with_disabled =False):
        return [] or list

    #FORCE using keyword-args only
    class EnforcingWrapper( object):
        __slots__ = ('org',)
        def __init__( me, timed_klas ): me.org = timed_klas()
        def get( me, **kargs): return me.org.get( **kargs)
        def put( me, **kargs): return me.org.put( **kargs)
        def getRange( me, **kargs): return me.org.getRange( **kargs)
        def __str__( me): return str( me.org)
        def __getattr__( me, name): return getattr( me.org, name)


class TimedTestSimpleCase( Case):
    'base4test'
    Timed2_withDisabled_klas = None     #klas with additional get.with_disabled, put.disabled args

    def __init__( me, doc, inputDatabase, testingSamples):
        Case.__init__( me, doc, inputDatabase, testingSamples)
        me._testDefaultTime = False
        me.obj = _Timed2_withDisabled_protocol.EnforcingWrapper( me.Timed2_withDisabled_klas )
    def setupEach( me, f):
        me.obj.put( value=f.value, trans=f.trans, valid=f.valid, disabled=(f.status == 'd') )
    def testEach( me, t):
        if me._testDefaultTime: t.trans = t.valid = datetime.now()
        return me.obj.get( trans=t.trans, valid=t.valid, with_disabled=False)
    def systemState( me): return str( me.obj)


class TimedCombinationsTestCase( TimedTestSimpleCase):
    def setup( me):
        import comb
        i = 0
        comb.res = []
        for vday, rday in comb.makeCombinations( list(range(1, 20, 2)), 2):
            valid = datetime( 2006, 2, vday)
            trans = datetime( 2006, 2, rday)
            me.obj.put( value= i, trans= trans, valid= valid)
            if me.verbosity > 2: print 'DB:', trans, valid, ' value', i
            i += 1

class TimedDefaultGetTestCase( TimedTestSimpleCase):
    ''' tests getting default (most recent) object
        relies on fact that test sequense dates are below current time,
        i.e. current time is after September 2006
    '''
    def __init__( me, doc, inputDatabase, testingSamples):
        TimedTestSimpleCase.__init__( me, doc, inputDatabase, testingSamples)
        me._testDefaultTime = True

class TimedRangeTestCase( TimedTestSimpleCase):
    def testEach( me, t):
        return me.obj.getRange( trans=t.trans, validFrom=t.valid, validTo=t.validTo, with_disabled=False)

def test( Timed2_withDisabled_klas, verbosity =VERBOSE, title= None):
    TimedTestSimpleCase.Timed2_withDisabled_klas = Timed2_withDisabled_klas
    import testdata
    t1 = TimedTestSimpleCase(       'test2_idb2',   testdata.idb2,  testdata.test2)
    t2 = TimedTestSimpleCase(       'test0_idb0',   testdata.idb0,  testdata.test0)
    t3 = TimedTestSimpleCase(       'test1_idb1',   testdata.idb1,  testdata.test1)
    t4 = TimedCombinationsTestCase( 'testComb',     [],             testdata.testComb)
    t5 = TimedDefaultGetTestCase(   'test_default', testdata.idbDefault, testdata.testDefault)
    t6 = TimedRangeTestCase(        'test_range',   testdata.idb_range,  testdata.testRange)
    t7 = TimedTestSimpleCase(       'test_false',   testdata.idb_false,  testdata.test_false)
    t8 = TimedRangeTestCase(        'test_range_false', testdata.idb_false,  testdata.test_range_false)
    cases = [ t1, t2, t3, t4, t5, t6,
        #t7, t8     #fix these to work for SA too - cant as SA is strong-typed
    ]
    sep = '\n\n==================, '
    if title: print sep+title
    return testMain( cases, verbosity= verbosity)

# vim:ts=4:sw=4:expandtab
