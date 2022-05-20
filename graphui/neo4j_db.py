import neo4j
from neo4j import GraphDatabase


class Graph:

    def __init__(self, session: neo4j.Session, debug=False):
        self._session=session
        self._tx = None
        self.debug = debug

    def run(self, statement, **kwargs):
        # sourcery skip: assign-if-exp, inline-immediately-returned-variable, lift-return-into-if
        if self.debug:
            print(statement, kwargs)
        if self._tx:
            result = self._tx.run(statement, **kwargs)
        else:
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


    def get_node(self, id):
        return self.run('match (n) where id(n)=$id return n', id=id).single()['n']

    def update_node(self, id, props):
        return self.run('match (n) where id(n)=$id set n=$props return n', id=id, props=props).single()['n']

    def get_edge(self, id):
        return self.run('match (start)-[r]->(target) where id(r)=$id return r', id=id).single()['r']

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




class Connection:

    def __init__(self, uri, username, password):
        self.uri=uri
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def graph(self, debug=False, **config) -> Graph:
        session = self.driver.session(**config)
        return Graph(session,debug=debug)


if __name__ == '__main__':


    c = Connection("neo4j://localhost:7687", 'neo4j','admin')
    g = c.graph()

    n = g.get_node(171)
    tx = g.tx

    # n2 = g.update_node(n.id,dict(n))
    # print(n2)
    r = list(g.relationships(71))
    print(r)
    tx.rollback()

