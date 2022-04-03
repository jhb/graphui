import py2neo as py2neo

connection = dict(host='localhost', user='neo4j', password='admin')
graph = py2neo.Graph(**connection)
graph.run('match (n) where n.name="propnode" detach delete n')

query = """MERGE (n:PROPNODE {name:'propnode',
                     integer:23,
                     float: 2.3,
                     string: "foobar",
                     boolean: true,
                     date: date(),
                     datetime: datetime(),
                     time: time(),
                     duration: duration('P14DT16H12M'),
                     point2d: point({latitude:13.43, longitude:56.21}),
                     point3d: point({latitude:13.43, longitude:56.21, height: 2}),
                     pointC2d: point({x:13.43, y:56.21}),
                     pointC3d: point({x:13.43, y:56.21, z: 2}),
                     
                     list_integer: [1,2,3],
                     list_float: [1.1,1.2,3.3],
                     list_string: ["foo","bar"],
                     list_boolean: [True, False],
                     list_date: [date(),date()],
                     list_datetime: [datetime(),datetime()],
                     list_time: [time(), time()],
                     list_duration: [duration('P1DT1H1M'),duration('P2DT2H2M')],
                     list_point2d: [point({latitude:13.43, longitude:56.21}),
                                    point({latitude:14.43, longitude:57.21})],
                     list_point3d: [point({latitude:13.43, longitude:56.21, height: 2}),
                                    point({latitude:14.43, longitude:57.21, height: 3})],       
                     list_pointC2d: [point({x:13.43, y:56.21}),point({x:14.43, y:57.21})],
                     list_pointC3d: [point({x:13.43, y:56.21, z: 2}),point({x:14.43, y:57.21, z: 3})]                       
                     }) return id(n)"""

print(graph.run(query))

