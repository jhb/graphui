import json
import os
from pprint import pprint
import flask
import markdown
import neo4j
from chameleon_fetcher import ChameleonFetcher
from flask import Flask, request, g, redirect, session
from attr_dict import AttrDict
from graphui.graphui import conversion
from neo4j_db import Connection
from settings import config
from flask_session import Session
from minigraph import MiniGraph
from time import time
from forwardlist import ForwardList

connection = Connection(config.neo4j, config.user, config.password)
app = Flask(__name__, static_url_path="/static", static_folder='static')
fetcher = ChameleonFetcher(os.path.join(os.path.dirname(__file__), 'templates'))
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = 'sessions'
Session(app)

meta_labels = {'Label', 'Relation', 'Property', 'SOURCE', 'TARGET', 'PROP'}

meta = MiniGraph()

def fetchMeta():
    neo = connection.graph(debug=config.debug)
    result = neo.run('match (n)  where n:Label or n:Relation or n:Property '
                     'optional match (n)-[r:PROP|SOURCE|TARGET]-(m) '
                     'return *;')
    meta.from_neo4j(result.graph())
    # meta.time = getMetaTime()
    return meta



@app.before_request
def before():
    g.graph = connection.graph(debug=config.debug)
    g.tx = g.graph.tx
    # getMetaTime()
    g.meta = fetchMeta()


@app.teardown_request
def teardown(exception):
    if hasattr(g, 'graph') and hasattr(g, 'tx'):
        if exception:
            g.graph.rollback(g.tx)
            del g.tx
        else:
            g.graph.commit(g.tx)


def tpl(template_name, **kwargs):
    return fetcher(template_name,
                   app=app,
                   flask=flask,
                   g=g,
                   graph=g.graph,
                   markdown=markdown,
                   session=session,
                   url_for=flask.url_for,
                   kwargs=kwargs,
                   json=json,
                   tpl=tpl,
                   get_value=get_value,
                   meta=g.meta,
                   request=request,
                   **kwargs)


def tpl_no_push(template_name, **kwargs):
    rendered = tpl(template_name, **kwargs)
    return rendered, 200, {"HX-Push": "false"}


@app.route('/<path:subpath>')
def other(subpath):
    return tpl(subpath)


@app.route('/')
def get_index():
    return tpl('index')


@app.route('/query', methods=['POST'])
def query():
    querystring = request.values.get('querystring', '')
    display_name = request.values.get('display', 'resultset')
    result = g.graph.run(querystring)
    resultgraph = result.graph()
    nodes = [n.id for n in resultgraph.nodes]
    edges = [[r.id, r.start_node.id, r.end_node.id] for r in resultgraph.relationships]
    resultset = dict(nodes=nodes, edges=edges)
    session['resultset'] = resultset

    return tpl('query', querystring=querystring,
               resultgraph=resultgraph,
               result=result,
               resultset=resultset,
               display_name=display_name)


def get_resultset():
    return session.get('resultset', dict(nodes=[], edges=[]))


def get_resultdata(resultset):
    out = dict(nodes=[], edges=[])

    result = g.graph.run('match (n) where id(n) in $nodeids with distinct n as n return n',
                         nodeids=resultset['nodes'])
    for row in result:
        out['nodes'].append(row['n'])

    query = 'match (n)-[r]-(m) where id(r) in $edgeids ' \
            'return distinct r,n,m'
    result = g.graph.run(query,
                         edgeids=[e[0] for e in resultset['edges']])
    for row in result:
        out['edges'].append(row['r'])
    out['edges'] = sorted(list(set(out['edges'])), key=lambda e: e.id)
    return out


def get_value(obj, keys=['name', 'title', 'id']):
    for key in keys:
        if key in obj:
            return obj[key]
    return 'unknown'


def node2dict(node):
    out = AttrDict()
    out['id'] = node.id
    out['labels'] = ", ".join(list(node.labels))
    out['properties'] = AttrDict(node)
    out['nodename'] = get_value(out['properties'])
    return out


def edge2dict(edge):
    out = AttrDict()
    out['id'] = edge.id
    out['type'] = edge.type
    out['source_id'] = edge.start_node.id
    out['target_id'] = edge.end_node.id
    out['properties'] = AttrDict(edge)
    return out


def resultdata2dicts(resultdata):
    out = dict(nodes={},
               edges={})
    for node in resultdata['nodes']:
        out['nodes'][node.id] = node2dict(node)
    for edge in resultdata['edges']:
        out['edges'][edge.id] = edge2dict(edge)
    return out


@app.route('/display')
def display():
    display_name = request.values.get('display', 'resultset')
    resultset = get_resultset()
    resultdata = get_resultdata(resultset)
    return tpl(f'display_{display_name}',
               resultset=resultset,
               resultdata=resultdata,
               resultdicts=resultdata2dicts(resultdata))


@app.route('/node/<int:nodeid>')
def node(nodeid):
    res = g.graph.run('match (n) where id(n) = $nodeid return n', nodeid=nodeid)
    return tpl('node',
               node=res.single()['n'])

@app.route('/edge/<int:edgeid>')
def edge(edgeid):
    res = g.graph.run('match (n)-[r]-(m) where id(r) = $edgeid return n,r,m', edgeid=edgeid)
    return tpl('edge',
               edge=res.single()['r'])

@app.route('/<obj_type>/<int:_id>/<path>', methods=['GET', 'POST'])
def property_(obj_type, _id, path):
    res = g.graph.run('match (n) where id(n) = $nodeid return n', nodeid=_id)
    node = res.single()['n']
    if request.method == 'POST':
        value = request.values['value']
        new_props = {path: value}
        g.graph.update_node_property(_id, path, value)
        if set(node.labels).intersection(meta_labels):
            setMetaTime()
        return redirect(f'/{obj_type}/{_id}')

    value = node[path]
    return tpl('property',
               obj_type=obj_type,
               _id=_id,
               path=path,
               node=node,
               value=value, )


@app.route('/nodefinder', methods=['GET', 'POST'])
def nodefinder():
    if request.method != 'POST':
        return tpl('nodefinder')
    searchstring = request.values['searchstring']
    if len(searchstring) > 0:
        nodes = g.graph.find_nodes(searchstring)
        if context_label := request.values.get('context_label', None):
            nodes = [node for node in nodes if context_label in node.labels]
            print(nodes, context_label)
    else:
        nodes = []
    return tpl('nodefinder_results', nodes=nodes)


@app.route('/node_add', methods=['GET', 'POST'])
def node_add():

    if request.method != 'POST':
        return tpl('node_add',fl=ForwardList)
    label_name = request.values['label_name']


    thelabel = g.meta.nln('Label', label_name)
    props = {
        propname: request.values[f'properties:{propname}']
        for propname in thelabel.fl.outE('PROP').target['name']
    }
    newnode = g.graph.create_node(label_name,**props)


    if label_name == 'Relation':
        source_ids = [int(source_id) for source_id in request.values.getlist('source_ids')]
        target_ids = [int(target_id) for target_id in request.values.getlist('target_ids')]
        if not source_ids or not target_ids:
            return tpl('node_add', fl=ForwardList)
        for source_id in source_ids:
            g.graph.create_edge(source_id, 'SOURCE', newnode.id)
        for target_id in target_ids:
            g.graph.create_edge(newnode.id, 'TARGET', target_id)

    if label_name == 'Label':
        property_ids = [int(source_id) for source_id in request.values.getlist('property_ids')]
        for property_id in property_ids:
            g.graph.create_edge(newnode.id, 'PROP', property_id)



    return redirect(f'/node/{newnode.id}')


def get_nodes():
    return [r['n'] for r in g.graph.run('Match (n) return n')]

@app.route('/edge_add', methods=['GET', 'POST'])
def edge_add():
    print(request.values)
    if not request.values.get('submit',''):
        return tpl('edge_add', time=time(),get_nodes=get_nodes)
    print(request.values)
    type_name = request.values['type_name']
    thetype = g.meta.nln('Relation', type_name)
    source_id = int(request.values['source_id'])
    target_id = int(request.values['target_id'])
    props = {
            propname: request.values[f'properties:{propname}']
            for propname in thetype.fl.outE('PROP').target['name']
    }
    newedge = g.graph.create_edge(source_id, type_name, target_id)
    return redirect(f'/edge/{newedge.id}')

def setMetaTime():
    t = time()
    g.graph.run("call apoc.static.set('graphui.meta.time',$t)",t=t)
    print(f'Set metatime to {t}')
    return t

def getMetaTime():
    r = g.graph.run("RETURN apoc.static.get('graphui.meta.time') AS t;")
    t = r.single()['t']
    print(f'Got metatime as {t}')
    return t

@app.route('/test', methods=['GET', 'POST'])
def test():
    return tpl('test')

@app.route('/favicon.ico')
def favicon():
    return redirect(flask.url_for('static', filename='favicon.ico'))


if __name__ == '__main__':
    app.run('0.0.0.0', use_reloader=True, port=int(config.port))
