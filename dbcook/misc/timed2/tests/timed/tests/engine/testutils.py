#$Id$
import unittest

# Tools
ERR = 1
FAL = 2
class HorTestResult( unittest._TextTestResult):
    "our test result respecting verbosity level to not show traceback always"
    def getDescription( me, test):
        desc = unittest._TextTestResult.getDescription( me, test)
        return ('\n'*2)+desc
    def printErrors(me):
        if me.dots or me.showAll:
            me.stream.writeln()
        me.printErrorList('ERROR', me.errors, ERR)
        me.printErrorList('FAIL', me.failures)
    def printErrorList( me, flavour, errors, erkind =FAL):
        for test, err in errors:
            me.stream.writeln( me.separator1)
            me.stream.writeln( "%s: %s" % (flavour,me.getDescription(test)))
            if me.showAll or ERR == erkind:
                me.stream.writeln( me.separator2)
                me.stream.writeln( str( err) )


class HorTestRunner( unittest.TextTestRunner):
    def _makeResult( me):
        return HorTestResult( me.stream, me.descriptions, me.verbosity)

class HorTestCase( unittest.TestCase):
    def __init__( me):
        unittest.TestCase.__init__( me, methodName ='testRun') #lius 10m vdesno
        me.docString = me.setupMethod = me.testMethod = None
    def setUp( me): me.setupMethod()
    def testRun( me): me.testMethod()
    def shortDescription( me):
        desc = str( me.docString)
        if desc != me.__class__.__name__: desc += ' ' + me.__class__.__name__
        doc = "%s %s" % ( me, desc)
        return doc.strip()

    def diff( me, result, expected, result_name='result', expected_name ='expected', ):
        if result == expected: return False
        err=0
        try:
            keys = expected.iterkeys()
        except AttributeError:
            if isinstance( expected, (tuple,list)):
                keys = range( len(expected))
        else:
            print 'diffing by items...'
            for k in keys:
                v = expected[k]
                try:
                    rv = result[k]
                except (KeyError,IndexError):
                    rv = '<NOT-SET>'
                    ok = False
                else:
                    ok = me.diff( rv, v)
                if not ok:
                    print 'key', k,':\n', result_name,':',rv, '\n', expected_name,':', v
                    err +=1
        if not err:
            print ' WARNING: diff as whole, no diff piece-by-piece ??!!'
        return True

    def assertEquals( me, a,b, **kargs):
        try:
            unittest.TestCase.assertEquals( me, a,b)
        except me.failureException:
            if not me.diff( a,b, **kargs):
                print ' WARNING: second diff gives no diff ??!!'
            raise

def testMain( testcases, verbosity =0):
    import sys
    verbosity = max( verbosity, sys.argv.count('-v') )
    suite = unittest.TestSuite()
    for case in testcases:
        case.verbosity = verbosity
        suite.addTest( case)
    return HorTestRunner( descriptions= True, verbosity= verbosity).run( suite).wasSuccessful()

# vim:ts=4:sw=4:expandtab