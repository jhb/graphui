import neo4j
from neo4j import GraphDatabase


class Graph:

    def __init__(self, session: neo4j.Session, debug=False):
        self._session=session
        self._tx = None
        self.debug = debug

    def run(self, statement, **kwargs) -> neo4j.Result:
        # sourcery skip: assign-if-exp, inline-immediately-returned-variable, lift-return-into-if
        if self.debug:
            print(statement, kwargs)
        if self._tx:
            if self.debug:
                print('tx')
            result = self._tx.run(statement, **kwargs)
        else:
            if self.debug:
                print('session')
            result =  self._session.run(statement, **kwargs)

        return result

    @property
    def tx(self):
        if self._tx is None:
            self._tx = self._session.begin_transaction()
        return self._tx

    def commit(self, tx=None):
        tx:neo4j.Transaction
        tx = self._tx if tx is None else tx
        if tx is not None:
            tx.commit()
        self._tx = None

    def rollback(self, tx=None):
        tx: neo4j.Transaction
        tx = self._tx if tx is None else tx
        if tx is not None:
            tx.rollback()
        self._tx = None


    def create_node(self, *labels, **props):
        if not props:
            props = dict(title='...')
        if labels:
            labelstring = ':'.join(labels)
            labelstring = ':'+labelstring
        if props:
            return self.run(f'create (n{labelstring}) set n=$props return n', props=props).single()['n']
        else:
            return self.run(f'create (n{labelstring}) return n').single()['n']

    def get_node(self, id):
        return self.run('match (n) where id(n)=$id return n', id=id).single()['n']

    def update_node(self, id, props):
        return self.run('match (n) where id(n)=$id set n=$props return n', id=id, props=props).single()['n']

    def update_node_property(self,id,name,value):
        return self.run(f'match (n) where id(n)=$id set n.{name}=$value return n',id=id,value=value).single()['n']

    def set_labels(self, node_id, labels=None):
        labels = labels if labels is not None else []

        node = self.get_node(node_id)
        add_labels = ':'.join(list(set(labels) - node.labels))
        remove_labels = ':'.join(list(node.labels - set(labels)))

        remove_string = f'remove n:{remove_labels}' if remove_labels else ''
        add_string = f'set n:{add_labels}' if add_labels else ''

        result = self.run(f"""match (n) where id(n)=$node_id
                              {remove_string}
                              {add_string} 
                              return n""",
                          node_id=node_id)
        return result.single()['n']

    def delete_node(self, node_id):
        self.run('match (n) where id(n)=$node_id detach delete n', node_id=node_id)

    def create_edge(self, source_id, reltype, target_id):
        return self.run(f"""match (source) where id(source)=$source_id
                           match (target) where id(target)=$target_id
                           create (source)-[r:{reltype}]->(target)
                           return r
                           """,source_id=source_id, reltype=reltype, target_id=target_id).single()['r']

    def get_edge(self, id):
        return self.run('match (start)-[r]->(target) where id(r)=$id return start,r,target', id=id).single()['r']

    def update_edge(self, id, props):
        return self.run('match ()-[r]->() where id(r)=$id set r=$props return r', id=id, props=props).single()['r']

    def delete_edge(self, edge_id):
        self.run('match ()-[r]->() where id(r)=$edge_id delete r', edge_id=edge_id)

    def edges(self, start_id=None, target_id=None):
        wheres = []
        if start_id:
            wheres.append(f'id(start)={start_id}')
        if target_id:
            wheres.append(f'id(target)={target_id}')

        statement = 'match (start)-[r]->(target) '
        if wheres:
            statement +=' where '
            statement += 'AND'.join(wheres)
        statement += ' return start,r,target'
        return self.run(statement).graph().relationships


    def find_nodes(self,searchterm, limit=1000):
        search_lower = searchterm.lower()
        query = f"""
    
                MATCH (x) WHERE 
                    ANY(prop in keys(x) where 
                        any(word in apoc.convert.toStringList(x[prop]) where toLower(word) contains $searchterm)
                        or toLower(prop) contains $searchterm
                        ) or 
                        id(x) = toInteger($searchterm) or
                        any(word in labels(x) where toLower(word) = $searchterm)
                RETURN distinct x limit $limit
            """

        # if self.debug:
        #     print(query.replace('$searchterm', f'"{search_lower}"'))
        r = self.run(query, searchterm=search_lower, limit=limit)
        return [row['x'] for row in r]

    def find_edges(self, searchterm, limit=1000):
        search_lower = searchterm.lower()
        query = f"""

                MATCH (source)-[x]->(target) WHERE 
                    ANY(prop in keys(x) where 
                        any(word in apoc.convert.toStringList(x[prop]) where toLower(word) contains $searchterm)
                        or toLower(prop) contains $searchterm
                        )  or 
                        id(x) =  toInteger($searchterm) or
                        toLower(type(x)) = $searchterm
                return distinct source,x,target limit $limit

                """
        # if self.debug:  # TODO use logging
        #     print(query.replace('$searchterm', f'"{search_lower}"'))

        r = self.run(query, searchterm=search_lower, limit=limit)
        return [row['x'] for row in r]

    def labels(self):
        return sorted([r['label'] for r in self.run('call db.labels')])

    def reltypes(self):
        return sorted([r['relationshipType'] for r in self.run('call db.relationshipTypes')])

    def get_property_keys(self):
        result = self.run('CALL db.propertyKeys()')
        return [r['propertyKey'] for r in result]

    def get_schemata(self):
        result = self.run("match (n) where n.title='GraphUI Schema' return n")
        if not result:
            return []
        schema_node=result.single()['n']
        where = ' and '.join(f'n.{p} is not NULL' for p in schema_node['schema_properties'])
        result2 = self.run(f"match (n) where {where} return distinct n order by n.title")
        return [row['n'] for row in result2]


class Connection:

    def __init__(self, uri, username, password):
        self.uri=uri
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def graph(self, debug=False, **config) -> Graph:
        session = self.driver.session(**config)
        return Graph(session, debug=debug)


if __name__ == '__main__':


    c = Connection("neo4j://localhost:7687", 'neo4j','admin')
    g = c.graph()

    n = g.get_node(171)
    tx = g.tx

    # n2 = g.update_node(n.id,dict(n))
    # print(n2)
    r = g.get_edge(71)
    print(r)
    tx.rollback()

