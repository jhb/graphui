import os
from pprint import pprint

import flask
from chameleon import PageTemplateLoader
from flask import Flask, request, g, redirect
from neo4j_db import Connection
import conversion
import neo4j
import babel.dates as babel_dates
import markdown
from dotenv import load_dotenv, find_dotenv


class AttrDict(dict):

    def __getattr__(self, item):
        return self[item]


# config
load_dotenv(find_dotenv())

config = AttrDict(debug=int(os.environ.get("GRAPHUI_DEBUG", 0)),
                  hx_boost=int(os.environ.get("GRAPHUI_HX_BOOST", 1)))

connection = Connection("neo4j://localhost:7687", 'neo4j', 'admin')
app = Flask(__name__, static_url_path="/static")


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


def get_templates():
    return PageTemplateLoader(os.path.join(os.path.dirname(__file__), 'templates'), '.pt',
                              boolean_attributes={"selected", "checked"},
                              auto_reload=True)


templates = get_templates()


def tpl(template_name, **kwargs):
    # this is not the best place because of performance
    template = templates[template_name]
    return template(templates=templates,
                    template_name=template_name,
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
                    **kwargs)


def get_display_title(obj, fields=('title', 'name', 'displayName')):
    return next((obj[field] for field in fields if field in obj), obj.id)


def get_obj_type(obj):
    return 'node' if type(obj) == neo4j.graph.Node else 'edge'


def get_obj_path(obj):
    return f'/{get_obj_type(obj)}/{obj.id}'


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

    query = f"""
    
        MATCH ()-[x]->() WHERE 
            ANY(prop in keys(x) where 
                any(word in apoc.convert.toStringList(x[prop]) where toLower(word) contains $searchterm)
                or toLower(prop) contains $searchterm
                )  or 
                id(x) =  toInteger($searchterm) or
                toLower(type(x)) = $searchterm
        return distinct x

        """

    if config.debug:  # TODO use logging
        print(query.replace('$searchterm', f'"{search_lower}"'))
    r = g.graph.run(query, searchterm=search_lower)
    out['relationships'] = [row['x'] for row in r]
    return tpl('search', result=out, searchterm=searchterm)


@app.route('/node/<int:node_id>')
@app.route('/node/<int:node_id>/')
def get_node(node_id):
    if config.debug:   # TODO use logging
        pprint(conversion.parse_form(request.values.items()))
    node = g.graph.get_node(node_id)
    return tpl('node', node=node)


@app.route('/<obj_type>/<int:obj_or_id>/<path>/<mode>', methods=['GET'])
@app.route('/<obj_type>/<int:obj_or_id>/<path>', methods=['GET', 'POST'])
def property_edit(obj_type, obj_or_id, path, mode='view'):
    fetch = getattr(g.graph, f'get_{obj_type}')
    obj = fetch(obj_or_id) if type(obj_or_id) == int else obj_or_id
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

        obj = fetch(obj.id)
        prop = obj[path]
        mode = 'view'

    elif mode == 'delete':
        new_props = dict(obj)
        del (new_props[path])
        update = getattr(g.graph, f'update_{obj_type}')
        update(obj.id, new_props)
        return redirect(f'/{obj_type}/{obj.id}')

    elif mode == 'add':
        new_props = dict(obj)
        prop = new_props[path]
        typ = conversion.guess_type(prop).split(':')[1]
        prop.append(conversion.get_default(typ))
        update = getattr(g.graph, f'update_{obj_type}')
        update(obj.id, new_props)
        return redirect(f'/{obj_type}/{obj.id}/{path}/edit')

    return tpl('property',
               mode=mode,
               obj=obj,
               prop=prop,
               path=path,
               obj_type=obj_type,
               name=path), 200, {"HX-Push": "false"}


@app.route('/<obj_type>/<int:obj_or_id>/<path>/<int:pos>/delete')
def property_element_delete(obj_type, obj_or_id, path, pos):
    fetch = getattr(g.graph, f'get_{obj_type}')
    obj = fetch(obj_or_id) if type(obj_or_id) == int else obj_or_id
    new_props = dict(obj)
    prop = new_props[path]
    prop.pop(pos)
    update = getattr(g.graph, f'update_{obj_type}')
    update(obj.id, new_props)
    return redirect(f'/{obj_type}/{obj.id}/{path}/edit')


@app.route('/<obj_type>/<int:obj_or_id>/add', methods=['GET'])
@app.route('/<obj_type>/<int:obj_or_id>', methods=['POST'])
def add_property(obj_type, obj_or_id):
    fetch = getattr(g.graph, f'get_{obj_type}')
    obj = fetch(obj_or_id) if type(obj_or_id) == int else obj_or_id
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

    return tpl('property_add',
               obj=obj,
               obj_type=obj_type,
               ), 200, {"HX-Push": "false"}


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
    rendered = tpl('show_macro',
                   show_template_file='edge_add',
                   show_widget_name='node_selection',
                   node_id=node_id,
                   side=side,
                   node=node)

    return rendered, 200, {"HX-Push": "false"}


def get_property_keys():
    result = g.graph.run('CALL db.propertyKeys()')
    return [r['propertyKey'] for r in result]

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

    return tpl('labels', node=node, mode=mode), 200, {"HX-Push": "false"}


@app.route('/labels/<int:node_id>/<label>/delete')
def label_delete(node_id,label):
    label = label.strip()
    node = g.graph.get_node(node_id)
    new_labels = sorted([l for l in node.labels if l!=label])
    node = g.graph.set_labels(node_id, new_labels)
    return tpl('labels', node=node, mode='edit'), 200, {"HX-Push": "false"}

@app.route('/favicon.ico')
def favicon():
    return ''


@app.route('/jhb')
def jhb():
    obj = g.graphnodes[172]
    print(obj)
    return str(obj['point3d'])


if __name__ == '__main__':
    app.run('0.0.0.0', use_reloader=True, port=5003)
