from forwardlist import ForwardList


class MiniGraph:

    def __init__(self, meta_labels = None):
        self.meta_labels = meta_labels is None and [] or meta_labels
        self._clear()

    def _clear(self):
        self.nodes = []
        self.edges = []
        self.nodes_by_id = {}
        self.edges_by_id = {}
        self.nodes_by_label = {}
        self.nodes_by_label_name = {}
        self.non_meta_nodes = {}

    def from_neo4j(self, neo_graph):
        self._clear()
        for node in neo_graph.nodes:
            Node(self).from_neo4j(node)

        for edge in neo_graph.relationships:
            Edge(self).from_neo4j(edge)
        return self

    def nln(self, label, name):
        return self.nodes_by_label_name.get(label,{}).get(name,{})


class Node(dict):

    def __init__(self, g: MiniGraph, **kwargs):
        super().__init__(**kwargs)
        self.g = g
        self.id = None
        self.labels = None
        self.outgoing = []
        self.incoming = []
        self.i = {}
        self.o = {}
        self.g.nodes.append(self)

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)

    def __repr__(self):
        return f"( {self['name']} {':'.join(self.labels)} )"

    @property
    def fl(self) -> ForwardList:
        return ForwardList([self])

    def from_neo4j(self, neo_node):
        self.id = neo_node.id
        self.labels = set(neo_node.labels)
        self.update(sorted(neo_node.items()))
        for label in self.labels:
            nl = self.g.nodes_by_label.setdefault(label, [])
            if self not in nl:
                nl.append(self)
            nln = self.g.nodes_by_label_name.setdefault(label, {})
            name = self['name']
            if name not in nln:
                nln[name] = self
        self.g.nodes_by_id[self.id] = self
        return self

    def outE(self, *reltypes):
        return [
                edge
                for edge in self.outgoing
                if not reltypes or edge.reltype in reltypes
        ]

    def inE(self, *reltypes):
        return [
                edge
                for edge in self.incoming
                if not reltypes or edge.reltype in reltypes
        ]


class Edge(dict):

    def __init__(self, g: MiniGraph, **kwargs):
        super().__init__(**kwargs)
        self.g = g
        self.id = None
        self.reltype = None
        self.source = None
        self.target = None
        self.g.edges.append(self)

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)

    def __repr__(self):
        return f"( {self.source['name']} ) -[{self.reltype}]-> ( {self.target['name']} )"
        # return f"-[{self.reltype}]->"

    @property
    def fl(self) -> ForwardList:
        return ForwardList([self])

    def from_neo4j(self, neo_edge):
        self.id = neo_edge.id
        self.update(sorted(neo_edge.items()))
        self.reltype = neo_edge.type

        self.source = self.g.nodes_by_id[neo_edge.start_node.id]
        if self not in self.source.outgoing:
            self.source.outgoing.append(self)
        o = self.source.o.setdefault(self.reltype, [])
        if self not in o:
            o.append(self)

        self.target = self.g.nodes_by_id[neo_edge.end_node.id]
        if self not in self.target.incoming:
            self.target.incoming.append(self)
        i = self.target.i.setdefault(self.reltype, [])
        if self not in i:
            i.append(self)
        return self
