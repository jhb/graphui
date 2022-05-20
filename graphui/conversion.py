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

from neo4j.time import Date as date, \
    Time as time, \
    DateTime as datetime, \
    Duration as duration
from neo4j.spatial import WGS84Point, CartesianPoint
from decimal import Decimal

import pytest


def str2time(string):
    return time(*[int(s) for s in string.split(':')])


def str2bool(string):
    try:
        return bool(int(string))
    except ValueError:
        return bool(string)


def data2cartesianpoint(d):
    return CartesianPoint([float(v) for v in d.values()])


def data2wgs84point(d):
    return WGS84Point([float(v) for v in d.values()])


def data2duration(d):
    return duration(**{k: float(v) for k, v in d.items()})


def widgetname(value, mode='view'):
    typ = guess_type(value)
    print('guessed', typ)
    if mode == 'edit':
        widget_map = dict(float='number',
                          int='number',
                          str='text',
                          )
        return widget_map.get(typ, typ) + '_edit'
    else:
        widget_map = dict(str='text',
                          )
        name = widget_map.get(typ, 'str') + '_view'
        print(name)
        return name


converters = dict(
        int=int,
        float=float,
        str=str,
        bool=str2bool,
        date=date.fromisoformat,
        time=str2time,
        datetime=datetime.from_iso_format,
        dec=Decimal,
        text=str,
        list=list,
        cartesianpoint=data2cartesianpoint,
        wgs84point=data2wgs84point,
        duration=data2duration
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
    if typ in [int, float, bool, date, time, duration, WGS84Point, CartesianPoint]:
        return typ.__name__.lower()
    elif typ == datetime:
        return 'datetime'
    elif typ == Decimal:
        return 'dec'
    elif typ in (str,):
        return 'text' if '\n' in value and 0 else 'str'
    elif typ in (list, tuple):
        return f'list:{guess_type(value[0])}' if value else 'list:str'


def guess_inner_type(value):
    return guess_type(value).split(':')[-1]


guess_type_data = [
        (42, 'int'),
        ('42', 'str'),
        (42.0, 'float'),
        (True, 'bool'),
        (date(2021, 10, 16), 'date'),
        (time(10, 41, 00), 'time'),
        (datetime(2021, 10, 16, 10, 41), 'datetime'),
        (Decimal('23.42'), 'dec'),
        ('foo\nbar', 'text'),
        (['1', '2', '3'], 'list:str'),
        ([], 'list:str'),
        ([1, 2, 3], 'list:int'),
        ([1.0, 2.0], 'list:float'),
        ([True, False], 'list:bool'),
        ((date(2021, 10, 16),), 'list:date'),
        ((time(10, 41, 00),), 'list:time'),
        ((datetime(2021, 10, 16, 10, 41),), 'list:datetime'),
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
        ('foo:datetime', '2021-10-16 10:42', datetime(2021, 10, 16, 10, 42)),
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
        ('foo:list:datetime', '2021-10-16 10:42\n2021-10-16 10:42:01', (datetime(2021, 10, 16, 10, 42),
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


def parse_form(data):  # iterable of tuples with key value elements
    out = {}
    for key, value in data:
        parts = key.split('.')
        if len(parts) == 1:
            out[key] = value
        elif len(parts) == 2:
            first, second = parts
            try:
                pos = int(second)
                the_list = out.setdefault(first, [])
                if pos == len(the_list):
                    the_list.append(value)
                elif pos < len(the_list):
                    the_list[pos] = value
            except ValueError:
                the_dict = out.setdefault(first, dict())
                the_dict[second] = value
        elif len(parts) == 3:
            first, second, third = parts
            pos = int(second)
            the_list = out.setdefault(first, [])
            if pos == len(the_list):
                the_list.append({})
            the_dict = the_list[pos]
            the_dict[third] = value
    return out


def fetch_prop(obj, path):
    parts = path.split('.')
    if len(parts) == 1:
        return obj.get(path)
    elif len(parts) == 2:
        first, second = parts
        value = obj.get(first)
        return value[int(second)]


testdata = [('direct', 1),
            ('list.0', 2),
            ('list.1', 3),
            ('sub.one', 4),
            ('sub.two', 5),
            ('sublist.0.one', 6),
            ('sublist.1.two', 7)
            ]


# print(parse_form(testdata))

def test_parse_form():
    expected = dict(direct=1,
                    list=[2, 3],
                    sub=dict(one=4,
                             two=5),
                    sublist=[dict(one=6),
                             dict(two=7)])
    assert parse_form(testdata) == expected
