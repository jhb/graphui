import json
import os
from pprint import pprint
import flask
import markdown
import neo4j
from chameleon_fetcher import ChameleonFetcher
from flask import Flask, request, g, redirect, session
from attr_dict import AttrDict
from neo4j_db import Connection
from settings import config
from flask_session import Session

connection = Connection(config.neo4j, config.user, config.password)
app = Flask(__name__, static_url_path="/static", static_folder='static')
fetcher = ChameleonFetcher(os.path.join(os.path.dirname(__file__), 'templates'))
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"]='sessions'
Session(app)

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
    querystring = request.values.get('querystring','')
    result = g.graph.run(querystring)
    resultgraph = result.graph()
    nodes = [n.id for n in resultgraph.nodes]
    edges = [[r.id,r.start_node.id,r.end_node.id] for r in resultgraph.relationships]
    data = dict(nodes=nodes,edges=edges)
    session['resultset']=data
    jdata = json.dumps(data, indent=2)


    return tpl('query', querystring=querystring,
                        resultgraph = resultgraph,
                        result=result,
                        data=data,
                        jdata=jdata)

@app.route('/display_resultset')
def display_3d():
    return tpl('display_resultset')

@app.route('/favicon.ico')
def favicon():
    return redirect(flask.url_for('static', filename='favicon.ico'))

if __name__ == '__main__':
    app.run('0.0.0.0', use_reloader=True, port=int(config.port))
