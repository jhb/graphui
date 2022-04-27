import os

import flask
import py2neo as py2neo
from chameleon import PageTemplateLoader
from flask import Flask, request, g

import conversion

connection = dict(host='localhost', user='neo4j', password='admin')
app = Flask(__name__, static_url_path="/static")


@app.before_request
def before():
    g.graph = py2neo.Graph(**connection)
    g.tx = g.graph.begin()


@app.teardown_request
def teardown(exception):
    if exception:
        if hasattr(g, 'tx') and hasattr(g, 'graph'):
            g.graph.rollback(g.tx)
    else:
        if hasattr(g, 'tx') and hasattr(g, 'graph'):
            g.graph.commit(g.tx)


class AttrDict(dict):

    def __getattr__(self, item):
        return self[item]


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
                    host=connection['host'],
                    conversion=conversion,
                    **kwargs)


def get_display_title(obj, fields=('title', 'name', 'displayName')):
    return next((obj[field] for field in fields if field in obj), obj.identity)


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

    print(query.replace('$searchterm', f'"{search_lower}"'))
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

    print(query.replace('$searchterm', f'"{search_lower}"'))
    r = g.graph.run(query, searchterm=search_lower)
    out['relationships'] = [row['x'] for row in r]
    return tpl('search', result=out, searchterm=searchterm)


@app.route('/node/<int:nodeid>')
def get_node(nodeid):
    node = g.graph.nodes[nodeid]
    return tpl('node', node=node)


@app.route('/edge/<int:edgeid>')
def get_edge(edgeid):
    edge = g.graph.relationships[edgeid]
    return tpl('edge', edge=edge)


def get_property_keys():
    result = g.graph.run('CALL db.propertyKeys()')
    return [r['propertyKey'] for r in result]


@app.route('/favicon.ico')
def favicon():
    return ''


if __name__ == '__main__':
    app.run('0.0.0.0', use_reloader=True, port=5003)
