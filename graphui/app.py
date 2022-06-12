import os
from pprint import pprint

import babel.dates as babel_dates
import flask
import markdown
import neo4j
from chameleon_fetcher import ChameleonFetcher
from flask import Flask, request, g, redirect

import conversion
from attr_dict import AttrDict
from neo4j_db import Connection
from settings import config

connection = Connection(config.neo4j, config.user, config.password)
app = Flask(__name__, static_url_path="/static", static_folder='static')


@app.before_request
def before():
    g.graph = connection.graph(debug=config.debug)
    g.tx = g.graph.tx


@app.teardown_request
def teardown(exception):
    if hasattr(g, 'graph') and hasattr(g, 'tx'):
        if exception:
            g.graph.rollback(g.tx)
            del g.tx
        else:
            g.graph.commit(g.tx)


def get_display_title(obj, fields=('title', 'name', 'displayName')):
    return str(next((obj[field] for field in fields if field in obj), obj.id))


def get_obj_type(obj):
    return 'node' if type(obj) == neo4j.graph.Node else 'edge'


def get_obj_path(obj):
    return f'/{get_obj_type(obj)}/{obj.id}'


fetcher = ChameleonFetcher(os.path.join(os.path.dirname(__file__), 'templates'))


def tpl(template_name, **kwargs):
    return fetcher(template_name,
                   app=app,
                   flask=flask,
                   g=g,
                   graph=g.graph,
                   get_display_title=get_display_title,
                   host=connection.uri,
                   conversion=conversion,
                   get_obj_path=get_obj_path,
                   get_obj_type=get_obj_type,
                   config=config,
                   babel_dates=babel_dates,
                   markdown=markdown,
                   url_for=flask.url_for,
                   **kwargs)


def tpl_no_push(template_name, **kwargs):
    rendered = tpl(template_name, **kwargs)
    return rendered, 200, {"HX-Push": "false"}


@app.route('/')
def get_index():
    return tpl('index')


@app.route('/search')
def search():
    # an always working fulltext across nodes and relations. No indexes used though...
    # TODO: have some form of dynamic fulltext field or index

    searchterm = request.values.get('searchterm', '').strip()

    out = AttrDict()
    search_lower = searchterm.lower()

    # TODO mix in optional search in _._searchable_text

    out['nodes'] = g.graph.find_nodes(searchterm)
    out['relationships'] = g.graph.find_edges(searchterm)

    return tpl('search', result=out, searchterm=searchterm)


@app.route('/node/<int:node_id>')
@app.route('/node/<int:node_id>/')
def get_node(node_id):
    if config.debug:  # TODO use logging
        pprint(conversion.parse_form(request.values.items()))
    node = g.graph.get_node(node_id)
    return tpl('node', node=node)


def fetch_obj(obj_type, obj_or_id):
    fetch = getattr(g.graph, f'get_{obj_type}')
    return fetch(obj_or_id) if type(obj_or_id) == int else obj_or_id


@app.route('/<obj_type>/<int:obj_or_id>/<path>/<mode>', methods=['GET'])
@app.route('/<obj_type>/<int:obj_or_id>/<path>', methods=['GET', 'POST'])
def property_ (obj_type, obj_or_id, path, mode='view'):
    obj = fetch_obj(obj_type, obj_or_id)
    prop = obj[path]
    if request.method == 'POST':
        typ = conversion.guess_type(prop).split(':')[0]
        data = conversion.parse_form(request.values.items()).get(path, [])  # could be an empty list
        if config.debug:  # TODO use logging
            print('typ', typ)
        if type(prop) != list:
            prop = [prop]
            data = [data]
        inner_type = conversion.guess_inner_type(prop)
        converter = conversion.converters[inner_type]

        # update the obj
        new_props = dict(obj)
        new = [converter(data[i]) for i, p in enumerate(prop)]
        new_props[path] = new if typ == 'list' else new[0]
        update = getattr(g.graph, f'update_{obj_type}')
        update(obj.id, new_props)

        obj = fetch_obj(obj_type, obj_or_id)
        prop = obj[path]
        mode = 'view'

    return tpl_no_push('property',
                       mode=mode,
                       obj=obj,
                       prop=prop,
                       path=path,
                       obj_type=obj_type,
                       name=path)


@app.route('/<obj_type>/<int:obj_or_id>/<path>/delete', methods=['GET'])
def property_delete(obj_type, obj_or_id, path):
    obj = fetch_obj(obj_type, obj_or_id)
    new_props = dict(obj)
    del (new_props[path])
    update = getattr(g.graph, f'update_{obj_type}')
    update(obj.id, new_props)
    return redirect(f'/{obj_type}/{obj.id}')


@app.route('/<obj_type>/<int:obj_or_id>/<path>/add', methods=['GET'])
def property_add(obj_type, obj_or_id, path):
    obj = fetch_obj(obj_type, obj_or_id)
    new_props = dict(obj)
    prop = new_props[path]
    typ = conversion.guess_type(prop).split(':')[1]
    prop.append(conversion.get_default(typ))
    update = getattr(g.graph, f'update_{obj_type}')
    update(obj.id, new_props)
    return redirect(f'/{obj_type}/{obj.id}/{path}/edit')


@app.route('/<obj_type>/<int:obj_or_id>/<path>/<int:pos>/delete')
def property_element_delete(obj_type, obj_or_id, path, pos):
    obj = fetch_obj(obj_type, obj_or_id)
    new_props = dict(obj)
    prop = new_props[path]
    prop.pop(pos)
    update = getattr(g.graph, f'update_{obj_type}')
    update(obj.id, new_props)
    return redirect(f'/{obj_type}/{obj.id}/{path}/edit')

@app.route('/<obj_type>/<int:obj_or_id>/add', methods=['GET'])
@app.route('/<obj_type>/<int:obj_or_id>/add/<prop_type>', methods=['GET'])
@app.route('/<obj_type>/<int:obj_or_id>', methods=['POST'])
def add_property(obj_type, obj_or_id,prop_type=None):
    obj = fetch_obj(obj_type, obj_or_id)
    if request.method == "POST":
        prop_type = request.values['prop_type']
        prop_name = request.values['prop_name'].strip()
        new_props = dict(obj)
        if prop_name not in new_props:
            typ = prop_type.split(':')[-1]
            value = conversion.get_default(typ)
            pprint(value)
            if prop_type.startswith('list:'):
                value = [value]
            new_props[prop_name] = value
            update = getattr(g.graph, f'update_{obj_type}')
            update(obj.id, new_props)
        return redirect(f'/{obj_type}/{obj.id}')

    if prop_type is None:
        prop_type = request.values.get('prop_type','str')
    if prop_type.startswith('list:'):
        prop = [conversion.get_default(prop_type[5:])]
    else:
        prop = conversion.get_default(prop_type)

    return tpl_no_push('property_add',
                       obj=obj,
                       obj_type=obj_type,
                       prop_type=prop_type,
                       prop = prop,
                       mode= 'add'
                       )


@app.route('/node/add')
def node_add():
    node = g.graph.create_node()
    return redirect(f'/node/{node.id}')


@app.route('/node/<int:node_id>/delete')
def node_delete(node_id):
    g.graph.delete_node(node_id)
    return redirect('/')


@app.route('/edge/<int:edge_id>')
def get_edge(edge_id):
    edge = g.graph.get_edge(edge_id)
    return tpl('edge', edge=edge)


@app.route('/edge/add', methods=['GET', 'POST'])
def edge_add():
    source_id = request.values.get('source_id', 'new')
    if source_id != 'new':
        source_id = int(source_id)

    target_id = request.values.get('target_id', 'new')
    if target_id != 'new':
        target_id = int(target_id)

    reltype = request.values.get('reltype', '')

    if request.method == 'POST':
        if source_id == 'new':
            source = g.graph.create_node()
            source_id = source.id
        if target_id == 'new':
            target = g.graph.create_node()
            target_id = target.id
        # TODO check that transactions work, this is a good spot for this
        edge = g.graph.create_edge(source_id, reltype, target_id)
        return redirect(f'/edge/{edge.id}')

    return tpl('edge_add',
               source_id=source_id,
               target_id=target_id,
               reltype=reltype
               )


@app.route('/edge/<int:edge_id>/delete')
def edge_delete(edge_id):
    g.graph.delete_edge(edge_id)
    return redirect('/')


@app.route('/nodefinder/<side>', methods=['GET', 'POST'])
def node_finder(side):
    searchterm = request.values.get('searchterm', '')
    nodes = []
    if searchterm:
        nodes = sorted(g.graph.find_nodes(searchterm, 10), key=lambda n: get_display_title(n))

    return tpl('show_macro',
               nodes=nodes,
               searchterm=searchterm,
               show_template_file='edge_add',
               show_widget_name='node_result',
               side=side
               )


@app.route('/nodeselect/<side>/<node_id>', methods=['GET'])
def node_select(side, node_id='new'):
    if node_id != 'new':
        node_id = int(node_id)
    node = g.graph.get_node(node_id) if node_id != 'new' else None
    return tpl_no_push('show_macro',
                       show_template_file='edge_add',
                       show_widget_name='node_selection',
                       node_id=node_id,
                       side=side,
                       node=node)


@app.route('/labels/<int:node_id>', methods=['GET', 'POST'])
def labels(node_id):
    node = g.graph.get_node(node_id)
    mode = 'edit'

    if request.method == "POST":
        new_labels = sorted({l.strip() for l in request.values.getlist('labels')})
        if add_label := request.values.get('add_label', '').strip():
            new_labels.append(add_label)
        node = g.graph.set_labels(node_id, new_labels)
        mode = 'view'

    return tpl_no_push('labels', node=node, mode=mode)


@app.route('/labels/<int:node_id>/<label>/delete')
def label_delete(node_id, label):
    label = label.strip()
    node = g.graph.get_node(node_id)
    new_labels = sorted([l for l in node.labels if l != label])
    node = g.graph.set_labels(node_id, new_labels)
    return tpl_no_push('labels', node=node, mode='edit')


@app.route('/favicon.ico')
def favicon():
    return redirect(flask.url_for('static', filename='favicon.ico'))


@app.route('/jhb')
def jhb():
    obj = g.graphnodes[172]
    print(obj)
    return str(obj['point3d'])


if __name__ == '__main__':
    app.run('0.0.0.0', use_reloader=True, port=int(config.port))
