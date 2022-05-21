import os
from pprint import pprint

import flask
from chameleon import PageTemplateLoader
from flask import Flask, request, g, redirect
from neo4j_db import Connection
import conversion
import neo4j

class AttrDict(dict):

    def __getattr__(self, item):
        return self[item]
# config
config = AttrDict(debug=0,
                  hx_boost=1)

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
            del(g.tx)
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
                    config = config,
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
    # an always working fulltext accross nodes and relations. No indexes used though...
    # TODO: have some form of dynamic fulltext field or index

    searchterm = request.values.get('searchterm', '').strip()

    out = AttrDict()
    search_lower = searchterm.lower()

    # TODO mix in optional search in _._searchable_text

    query = f"""
        
        MATCH (x) WHERE 
            ANY(prop in keys(x) where 
                any(word in apoc.convert.toStringList(x[prop]) where toLower(word) contains $searchterm)
                or toLower(prop) contains $searchterm
                ) or 
                  id(x) = toInteger($searchterm) or
                  any(word in labels(x) where toLower(word) = $searchterm)
        RETURN distinct x
    """

    if config.debug: print(query.replace('$searchterm', f'"{search_lower}"'))
    r = g.graph.run(query, searchterm=search_lower)
    out['nodes'] = [row['x'] for row in r]

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

    if config.debug: print(query.replace('$searchterm', f'"{search_lower}"'))
    r = g.graph.run(query, searchterm=search_lower)
    out['relationships'] = [row['x'] for row in r]
    return tpl('search', result=out, searchterm=searchterm)


@app.route('/node/<int:nodeid>')
@app.route('/node/<int:nodeid>/')
def get_node(nodeid):
    if config.debug: pprint(conversion.parse_form(request.values.items()))
    node = g.graph.get_node(nodeid)
    return tpl('node', node=node)

@app.route('/<obj_type>/<int:obj_or_id>/<path>/<mode>', methods=['GET'])
@app.route('/<obj_type>/<int:obj_or_id>/<path>', methods=['GET','POST'])
def property_edit(obj_type, obj_or_id, path, mode='view'):
    fetch = getattr(g.graph,f'get_{obj_type}')
    obj = fetch(obj_or_id) if type(obj_or_id) == int else obj_or_id
    prop = obj[path]
    if request.method == 'POST':
        data = conversion.parse_form(request.values.items())[path]
        typ = conversion.guess_type(prop).split(':')[0]
        if config.debug: print('typ',typ)
        if type(prop) != list:
            prop = [prop]
            data = [data]
        inner_type = conversion.guess_inner_type(prop)
        converter = conversion.converters[inner_type]

        newprops = dict(obj)
        new = [converter(data[i]) for i,p in enumerate(prop)]
        newprops[path] = new if typ == 'list' else new[0]
        update = getattr(g.graph,f'update_{obj_type}')
        update(obj.id,newprops)

        obj = fetch(obj.id)
        prop = obj[path]
        mode = 'view'

    elif mode == 'delete':
        newprops = dict(obj)
        del(newprops[path])
        update = getattr(g.graph,f'update_{obj_type}')
        update(obj.id,newprops)
        return redirect(f'/{obj_type}/{obj.id}')

    elif mode == 'add':
        newprops = dict(obj)
        prop = newprops[path]
        typ = conversion.guess_type(prop).split(':')[1]
        prop.append(conversion.get_default(typ))
        update = getattr(g.graph, f'update_{obj_type}')
        update(obj.id, newprops)
        return redirect(f'/{obj_type}/{obj.id}/{path}/edit')

    return tpl('property',
               mode = mode,
               obj = obj,
               prop = prop,
               path = path,
               obj_type=obj_type,
               name=path), 200, {"HX-Push":"false"}


@app.route('/<obj_type>/<int:obj_or_id>/<path>/<int:pos>/delete')
def property_element_delete(obj_type, obj_or_id, path, pos):
    fetch = getattr(g.graph, f'get_{obj_type}')
    obj = fetch(obj_or_id) if type(obj_or_id) == int else obj_or_id
    newprops = dict(obj)
    prop = newprops[path]
    prop.pop(pos)
    update = getattr(g.graph, f'update_{obj_type}')
    update(obj.id, newprops)
    return redirect(f'/{obj_type}/{obj.id}/{path}/edit')

@app.route('/<obj_type>/<int:obj_or_id>/add', methods=['GET'])
@app.route('/<obj_type>/<int:obj_or_id>', methods=['POST'])
def add_property(obj_type, obj_or_id):
    fetch = getattr(g.graph, f'get_{obj_type}')
    obj = fetch(obj_or_id) if type(obj_or_id) == int else obj_or_id
    if request.method=="POST":

        prop_type = request.values['prop_type']
        prop_name = request.values['prop_name'].strip()
        typ = prop_type.split(':')[-1]
        value = conversion.get_default(typ)
        pprint(value)
        if prop_type.startswith('list:'):
            value = [value]
        new_props = dict(obj)
        new_props[prop_name]=value
        update = getattr(g.graph, f'update_{obj_type}')
        pprint(new_props)
        update(obj.id, new_props)
        return redirect(f'/{obj_type}/{obj.id}')

    return tpl('property_add',
               obj=obj,
               obj_type=obj_type,
               ), 200, {"HX-Push": "false"}


@app.route('/edge/<int:edgeid>')
def get_edge(edgeid):
    edge = g.graph.get_edge(edgeid)
    return tpl('edge', edge=edge)


def get_property_keys():
    result = g.graph.run('CALL db.propertyKeys()')
    return [r['propertyKey'] for r in result]


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
