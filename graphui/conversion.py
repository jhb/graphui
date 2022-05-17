"""
Conversion tools for request data

Request arguments should have the name in the form of 'variable_name:type=value'
>>> convert('foo:int','42')
42

You can also guess the correct field type:
>>> guess_type([42.0])
'list:float'

A helper to just get the variable name
>>> get_varname('foo:list:dec')
'foo'
"""

from interchange.time import Date as date, \
                             Time as time, \
                             DateTime as datetime, \
                             Duration as duration
from interchange.geo import WGS84Point, CartesianPoint
from decimal import Decimal

import pytest


def str2time(string):
    return time(*[int(s) for s in string.split(':')])


def str2bool(string):
    try:
        return bool(int(string))
    except ValueError:
        return bool(string)


def widgetname(value):
    typ = guess_type(value)
    widget_map = dict(dt='datetime',
                      float='number',
                      int='number',
                      )
    return widget_map.get(typ,typ)

converters = dict(
        int=int,
        float=float,
        str=str,
        bool=str2bool,
        date=date.fromisoformat,
        time=str2time,
        dt=datetime.from_iso_format,
        dec=Decimal,
        text=str,
        list=list
)


def get_varname(key):
    return key.split(':')[0]


def convert(key: str, value):
    varname, typ = key.split(':', 1) if ':' in key else (key, 'str')
    if typ == 'list':
        typ = 'list:str'
    if typ.startswith('list:'):
        typ = typ[5:]
        return tuple(converters[typ](line) for line in value.split('\n'))
    elif typ == 'ts':
        return tuple(value.split(' '))
    elif typ == 'tc':
        return tuple(v.strip() for v in value.split(','))
    else:
        return converters[typ](value)


def guess_type(value):
    typ = type(value)
    print(typ)
    if typ in [int, float, bool, date, time, duration, WGS84Point, CartesianPoint]:
        return typ.__name__.lower()
    elif typ == datetime:
        return 'dt'
    elif typ == Decimal:
        return 'dec'
    elif typ in (str,):
        return 'text' if '\n' in value else 'str'
    elif typ in (list, tuple):
        return f'list:{guess_type(value[0])}' if value else 'list:str'


guess_type_data = [
        (42, 'int'),
        ('42', 'str'),
        (42.0, 'float'),
        (True, 'bool'),
        (date(2021, 10, 16), 'date'),
        (time(10, 41, 00), 'time'),
        (datetime(2021, 10, 16, 10, 41), 'dt'),
        (Decimal('23.42'), 'dec'),
        ('foo\nbar', 'text'),
        (['1', '2', '3'], 'list:str'),
        ([], 'list:str'),
        ([1, 2, 3], 'list:int'),
        ([1.0, 2.0], 'list:float'),
        ([True, False], 'list:bool'),
        ((date(2021, 10, 16),), 'list:date'),
        ((time(10, 41, 00),), 'list:time'),
        ((datetime(2021, 10, 16, 10, 41),), 'list:dt'),
        ((Decimal('23.42'),), 'list:dec'),
]


@pytest.mark.parametrize('value,result', guess_type_data)
def test_guess_type(value, result):
    assert guess_type(value) == result


convert_data = [
        ('foo', 'bar', 'bar'),
        ('foo', '42', '42'),
        ('foo:int', '42', 42),
        ('foo:float', '42', 42.0),
        ('foo:str', '42', '42'),
        ('foo:bool', '42', True),
        ('foo:bool', '0', False),
        ('foo:bool', 'bar', True),
        ('foo:date', '2021-10-16', date(2021, 10, 16)),
        ('foo:time', '10:42', time(10, 42, 00)),
        ('foo:dt', '2021-10-16 10:42', datetime(2021, 10, 16, 10, 42)),
        ('foo:dec', '42.23', Decimal('42.23')),
        ('foo:list', '1\n2\n3', ('1', '2', '3')),
        ('foo:list:int', '1\n2\n3', (1, 2, 3)),
        ('foo:list:str', '1\n2\n3', ('1', '2', '3')),
        ('foo:list:float', '1\n2\n3', (1.0, 2.0, 3.0)),
        ('foo:list:bool', '0\n1\n2', (False, True, True)),
        ('foo:list:date', '2021-10-15\n2021-10-16', (date(2021, 10, 15),
                                                     date(2021, 10, 16))),
        ('foo:list:time', '10:41:00\n10:41:01', (time(10, 41, 0),
                                                 time(10, 41, 1))),
        ('foo:list:dt', '2021-10-16 10:42\n2021-10-16 10:42:01', (datetime(2021, 10, 16, 10, 42),
                                                                  datetime(2021, 10, 16, 10, 42, 1))),
        ('foo:list:dec', '23.42\n42.23', (Decimal('23.42'),
                                          Decimal('42.23'))),
        ('foo:text', 'one\ntwo three\nfour', 'one\ntwo three\nfour'),
        ('foo:ts', 'one two three', ('one', 'two', 'three')),
        ('foo:tc', 'one, two three, four', ('one', 'two three', 'four'))

]


@pytest.mark.parametrize('key,value,result', convert_data)
def test_convert(key, value, result):
    assert convert(key, value) == result


def test_get_varname():
    assert get_varname('foo:list:tc') == 'foo'
