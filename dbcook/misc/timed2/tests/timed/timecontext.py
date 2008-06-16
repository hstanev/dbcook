#$Id$
# -*- coding: cp1251 -*-

'''
TimeContext: ������� �������� �� ������ ��������/������� - ���-�������� (bi-temporal).
    trans_time: ����� �� ���������� �� ������������/���������
    valid_time: ��/�� ���� � ������� ����������/��������� (������)
����������:
 - �� �� ������ ���� ���������� ����� (�������� ������?) � Timed*
 - �� �� ������� ���������� �� ���������: t.trans, t.valid
 - �� �� ������ ��������� ������ ����� - _����_ � �������
�.�. ����. �������/�������� � ���.�����

������ �����-�������� �����/��������� �� �������� �� ����� �������-��������.
    ����. �� x = a+b, ������ � � b �� �������, ������ �� �������� ����:
    x = a.get( time) + b.get( time)

�� ��������� ��� ���������� ��� �������� ����������� �� �������������/�������� �� ���������� ��:

 - Translator* - �������� ��������� ������ � ������� �� �������� �� �����:
      x=a+b->
        t = Translator( time, locals() )
        x = t.a + t.b
    Translator1 � �����, �� �� ������ � ���������� ������, �.�. b.c.d ������ �� �� ������� �������������:
      x=a+b.c.d->
        t = Translator1( time, a=a, bcd=b.c.d )
        x = t.a + t.bcd
    Translator2 � ������ � ���������� ������, �� ���� �� �� ������ ��� ������ ������:
      x=a+b.c.d->
        t = Translator2( time, locals() )
        x = t.a + t.b.c.d

 - �������� �������� �� �������:
    �� �� ������ �� ������ �������� ��� ���� �������� �������� (�.�. �� ������������/default)
    - ������ �� �� �� ������� �� �� ������������ !!
    - ������� �������� ��������� �� ������ TimedObj ������ (!), ����� ���� �� �� � �����������
    ��������:
        tmp = newDefaultTimeContext( time)
        x = a + b + c.get( time -1)
        tmp.restoreTimeContext()    #��� ���� ����������� ����������

'''

class TimeContext( tuple):
    '''
    ���� � �������� ������, �� ���� �� ���������� �� ��������.
    ������ �� �������� �� ���������� �����!
        - ������: ������� .trans, .valid, .as_trans_valid() � .as_valid_trans().
        - ���������: ���� ���� keyword ��������� (trans=,valid=),
            ��� �� ����� �� ���� �����.
    (��������� ������ valid � trans ���� �� �� ������� valid_time � trans_time)

    ������ ������� ������ �� �� �� ��� TimeContext.Time (����������);
    (��� ��� ������� TransTime, trans ������ �� � TransTime,

    ����� � ���� ���� ���������� �� ������ �������� �������, ����� � ��
    ��������� �� ����� �� �����, �� �� �������, ���� �� ������
    ��������� - �� ���� �� �� ������.
    '''

    Time = object
#    TransTime = None
    @classmethod
    def isTime( klas, time): return isinstance( time, klas.Time)
    _isTime = isTime    #save it
    @classmethod
    def isTransTime( klas, time): return isinstance( time, getattr( klas, 'TransTime', klas.Time))
    _isTransTime = isTransTime #save it

    def __new__( klas, **kargs):
        ''' ctor( trans=, valid=)
            ctor( trans_time=, valid_time=)
            ctor( time_trans=, time_valid=)
        '''
        return klas._ctor2( **kargs)
    @classmethod
    def copy( klas, tm):
        'copy_ctor( another_TimeContext_of_SAME_type)'
        assert isinstance( tm, klas)
        return tuple.__new__( klas, tm)

    @classmethod
    def _ctor1( klas, valid, trans):
        assert klas.isTime( valid), `valid`
        assert klas.isTransTime( trans), `trans`
        return tuple.__new__( klas, (valid,trans))
    @classmethod
    def _ctor2( klas, **kargs):
        valid = trans = None
        for k,v in kargs.iteritems():
            if k in klas._names4valid:
                if valid is None: valid = v
                else: raise TypeError, 'multiple values for time_valid; use only one of ' +klas._names4valid
            if k in klas._names4trans:
                if trans is None: trans = v
                else: raise TypeError, 'multiple values for time_trans; use only one of ' +klas._names4trans
        if valid is None:
            raise TypeError, 'time_valid not specified; use one of ' +klas._names4valid
        if trans is None:
            raise TypeError, 'time_trans not specified; use one of ' +klas._names4trans
        return klas._ctor1( valid, trans)

    class _Pickler(object):
        def __new__( klas, valid,trans):
            return TimeContext._ctor1( valid,trans)
    def __reduce__( me):
        return _Pickler, me.as_trans_valid()

    valid = time_valid = valid_time = property( lambda me: tuple.__getitem__(me,0) ) #me[0] )
    trans = time_trans = trans_time = property( lambda me: tuple.__getitem__(me,1) ) #me[1] )
    _names4valid = 'valid', 'valid_time', 'time_valid'
    _names4trans = 'trans', 'trans_time', 'time_trans'
    def as_trans_valid( me): return me.trans,me.valid   #tuple.__getitem__(me,1)],me[0] ,me[0]
    def as_valid_trans( me): return tuple(me)
    def __str__( me): return 'TimeContext( trans=%r, valid=%r)' % me.as_trans_valid()
    __repr__ = __str__
    def __getitem__( me,*a):
        raise NotImplementedError, 'DO NOT use direct indexes!'

####
    if 0:
        class DefaultTimeContext( object):
            #XXX
            ''' ��������!:
                a = DefaultTimeContext( xx)
                b = DefaultTimeContext( yy)
               ������ ����� �� ������ (�������� � yy), ������
                d = DefaultTimeContext( xx)
                d = DefaultTimeContext( yy)     #������ d!
               ���� �� �� ������� ������� �� ������ - ������ xx !!??
            '''#XXX

            import threading
            _thread_default = threading.local()
            _thread_default.timeContexts = []
            pushDefaultTimeContext = _thread_default.timeContexts.append
            popDefaultTimeContext  = _thread_default.timeContexts.pop

            def last( me): return me._thread_default.timeContexts[-1]
            __slots__ = ( 'any',)
            def __init__( me, tm):
                assert isinstance( tm, TimeContext)
                me.pushDefaultTimeContext( tm)
                me.any = True
                print 'push'
            def restore( me):
                if (me.any): me.popDefaultTimeContext()
                me.any = False
                print 'restore'
            __del__ = restore

        def default(): return DefaultTimeContext.last()


TM = TimeContext
_Pickler = TimeContext._Pickler

import timed2 as _timed2
class _Timed2overTimeContext( _timed2.Timed2):
    __slots__ = ()
    TimeContext = TimeContext

    #to Timed2 internal protocol
    def time2key_valid_trans( me, time):
        assert isinstance( time, me.TimeContext)
        return time

    #from Timed2 internal protocol
    def key_valid_trans2time( me, (valid, trans) ):
        return me.TimeContext( trans=trans, valid=valid)


class _Test( _timed2.Test):
    @staticmethod
    def timekey2input( timed, (v,t)): return (t,v)
    @staticmethod
    def input2time( (t,v)): return TimeContext( trans=t,valid=v)

if __name__ == '__main__':
    try: c = TimeContext( 1,2)
    except TypeError: pass
    try: c = TimeContext( trans=1)
    except TypeError: pass
    try: c = TimeContext( valid=1)
    except TypeError: pass
    c = TimeContext( trans=1,valid=2)

    test2 = _Test()
    t = _Timed2overTimeContext()
    objects = test2.fill( t, [1,3,2,4]  )
    err = test2.test_db( t)
#    if not err: print t
    test2.test_get( t, objects,)
    test2.exit()

    import module_timed
    from datetime import datetime, timedelta

    class Timed2dict( Timed2):
        def time2key_valid_trans( me, time):                #to Timed2 protocol
            return (time['valid'],time['trans'])
        def key_valid_trans2time( me, (trans, valid)):      #from Timed2 protocol
            return dict( trans=trans, valid=valid)

    class Customer:
        def __init__( me):
            me.name = Timed2dict()
            me.salary = Timed2dict()
        def get( me, time):
            return dict(
                name   = me.name.get( time),
                salary = me.salary.get( time),
            )
    from translator import Translator
    def dod_calculate( customer, dod, time):
        t = Translator( time, salary=customer.salary, dod=dod, )
        print t.dod
        return t.dod and t.dod.dod(t.salary) or 0

######
    Converter = module_timed.mod2time__all_in_fname___trans_valid
    class mod2time__converter( Converter):
        str2time1 = staticmethod( module_timed.dateYYYYMMDD2datetime)
        def maketime( me, trans, valid):
            return dict( trans=trans, valid=valid)

    DOD = module_timed.Module( 'dod2', Timed2dict,
                mod2time__converter
            )
    print DOD
    c = Customer()
    c.name.put( 'alex yosifov', dict( trans=datetime(2006,1,2), valid=datetime(2006,1,2)))
    c.salary.put( 333,          dict( trans=datetime(2006,2,2), valid=datetime(2006,2,2)))
    c.salary.put( 500,          dict( trans=datetime(2006,5,2), valid=datetime(2006,5,2)))
    c.salary.put( 2000,         dict( trans=datetime(2006,5,22),valid=datetime(2006,6,2)))
    c.name.put( 'A. Yosifov',   dict( trans=datetime(2006,8,2), valid=datetime(2006,9,2)))
    one_u = timedelta(microseconds=1)
    for i in range(1, 13):
        dt = datetime(2006, i, 1) - one_u
        print dt, dod_calculate( c, DOD, dict( trans=dt, valid=dt) )    #Timed2 used by module_timed above

# vim:ts=4:sw=4:expandtab
