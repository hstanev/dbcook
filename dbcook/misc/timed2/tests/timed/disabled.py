#$Id$
# -*- coding: cp1251 -*-

'''
����������� �� ��������/������� �� ��������� '������/��������':
 1: ������� ������� �� �����������:
    - ��������� �� � ������ � ������ - ���� �� � ������� (��/�������)
    - �� ���� �� �� ������ ����������� ����� ���� ������ - �� ���� ���� �� ����
 2: ����� �� ������ �� ������ ��� ���������, ����. �������� ������:
    - �� �� ���� ������
    - �� ���� �� �� ������ ����������� ����� ���� ������
 3: �����/������� �� ������� ���������/disabled �� ������, � �� ����� ���� ���������� �����:
    - ���� �� �� ������ ����������� ����� - ������� �� �� ����
    - ������� �� ����, �.�. ������ �� �� ����� _�����_ + ������ ���������
 4: ����� �� ������, ����� ��� ���������, � �� ������ ����� �������� ��� ������:
    - �� ������ �� ������ 100%, ����. isinstance, issubclass ������ �� ��
        �������� �� ������ ������, � �� ��������

 == ����� �� ����������, �� ��������� ����� ������ �� �� ���� ����������
    (����. ���������� ������� ����� �����������)
 5: ����������� �� �� ����� ���� ����� ������, � _������_ ����� �� ����� ������� ������,
        ��������� "������� ���������"
    - ��� � ����� ���������� ����� �����������, �� �� ������ �� �� ����� ������������,
        � ���������� ���� �� �� � ����� ���� � ������� �� ����������� - ������ �� �������/���� -
        � �� ������� ��������� �� ������� Timed* ����!

�������� ��� ��� 2 �������� ������� �� "���������� �� �������� �����":
e������ � _�������_ �������� � ������� �� ��������� (2,3,4 ����� ����),
������� � "��� �������� ������� ��������" (5, � ���-��-� � ����������� �� �����������).

 6: ��� �������, �� � ����� �� �� ����� ������� �������� � ������� �� ���������,
������ �� �� ������� ���������� �� 1 � ����� ������: �������� �� ������ ����� �� ��,
� ��� ������� ������� �� �����������, ����� ����� ���������+������ ��� ����� �� ���������.

����������� �� ����������/�������� �� ����������� ��� ������������:
 �: ����� �������: (���� ����� - ��� �����, ��� ���������)
    return ������ / ������ (������ ������ None/None - ��� ������� � ���������)
 �: ����������: (���� ����� - ��� �����, ��� ���������)
    raise ������ / ������
 �: ������� �� ������� � ������ (�� ������ � �������� ???)
    obj.disabled = ������ / ������; return obj
 �: ����� �� ������, ����� ��� ���������, � �� ������ ����� �������� ��� ������:
    return WrapProxy( obj, disabled= ������/������)
    - �� ������ �� ������ 100% (���� ���� 4 ��-����)

------- ����� -----
 - ����������� �� ���� '�� ������ _������_ ��� � ���� ������' ���� �� �� � ������������:
    ����. ��� ������� �� ������(1.11); ����� �� ������(5.11); ����� �� ����� ��������( 3.11)
    ���������� ��� 5.11 � � ��� ����������� �� � �������� - ���/���� �����.
    ������� ��, ���� �� ����� �� ������ �� �� �������/����� ��������� �� ������ ����� - ������
    ��������� �� ���� ������ �� �� ����� �� ����� ��-������ ����.
 - 3) � �) �� ������ ����� ��� ������ ������ �� ���� .disabled �� �������;
    ����� ���� ���������� ���� �� � ����� ����� ��������;
 - 5) �������� ���-��������� - ���� �������� ���������... � ����� �� � ��?

��, ��� �� ����?

'''

#�������
_USE_WRAPPER_TUPLE = 0              #2
_USE_OBJECT_ATTR = 0                #3
class DisabledState: pass
_USE_SYMBOL_INSTEAD_OF_OBJECT = 1   #5
_USE_SEPARATE_HISTORY6 = 0          #6

#����������/��������
#? ���� � �)

class Disabled4Timed( object):
    __slots__ = ()
    DisabledKlas = DisabledState
    #NOT_FOUND = ... from timed

    # ������ _get_val() / _put_val() �� ������ �� Timed* ������
    def _get( me, time, include_disabled =False, **kargs):
        value = me._get_val( time, **kargs)
        if value is me.NOT_FOUND:
            #print 'empty', value
            return value                # ���� ������ ���-���

        try:
            if _USE_WRAPPER_TUPLE:
                value,disabled = value      #value ���� �� ���� ���� � disabled !
            elif _USE_OBJECT_ATTR:
                disabled = value.disabled   #value �� ���� disabled
            elif _USE_SYMBOL_INSTEAD_OF_OBJECT:
                disabled = value is me.DisabledKlas
            else: raise NotImplementedError
        except (AttributeError, ValueError):
            disabled = False

        if disabled and not include_disabled:
            #print 'disabled', value
            return me.NOT_FOUND         # '������' - raise

        #if _USE_SYMBOL_INSTEAD_OF_OBJECT:
            #XXX ������ ���������� ������� �������� ����� �����������.. ����� �� � ����?
            #XXX ���� �� �� ������ _�����_ ���������� �� ����� �� �����������!
            #XXX �� ������� ��������� �� ������� Timed* ����!
        return value

    def _getRange( me, timeFrom, timeTo, include_disabled =False, **kargs): #not quite clear, but works
        return me._get_range_val( timeFrom, timeTo, **kargs)
    def _put( me, value, time, disabled =False):
        if _USE_WRAPPER_TUPLE:
            value = value,disabled
        elif _USE_OBJECT_ATTR:
            value.disabled = disabled
            #XXX ��� ������ �� �� ����� �����!
            #except AttributeError: #cannot be disabled
        elif _USE_SYMBOL_INSTEAD_OF_OBJECT:
            if disabled:
                value = me.DisabledKlas
        else: raise NotImplementedError
        me._put_val( value, time)

    def delete( me, time):
        #XXX ���� ����������� �� ��������� �� ���� ������;
        # ��� � �����(???), ����� me._get(..) ������ ����� me._get_val()
        value = me._get_val( time)
        if value:
            me._put( value, time, disabled=True)

if _USE_SEPARATE_HISTORY6:
    class Disabled4Timed6( object):
        def __init__( me, TimedKlas):
            me.state = TimedKlas()
        #... ������ � �����!

# vim:ts=4:sw=4:expandtab:enc=cp1251:fenc=
