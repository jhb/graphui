from forwardlist import ForwardList


class Graph:

    def __init__(self):
        self.nodes = []
        self.edges = []
        self.nodes_by_id = {}
        self.edges_by_id = {}
        self.nodes_by_label = {}
        self.nodes_by_label_name = {}

    def from_neo4j(self, neo_graph):
        for node in neo_graph.nodes:
            Node(self).from_neo4j(node)

        for edge in neo_graph.relationships:
            Edge(self).from_neo4j(edge)

    def nln(self,label,name):
        return self.nodes_by_label_name[label][name]

class Node(dict):

    def __init__(self, g: Graph, **kwargs):
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
            gnl = self.g.nodes_by_label.setdefault(label,[])
            if self not in gnl:
                gnl.append(self)
            gnln = self.g.nodes_by_label_name.setdefault(label,{})
            name = self['name']
            if name not in gnln:
                gnln[name]=self
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

    def __init__(self, g, **kwargs):
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
        o =  self.source.o.setdefault(self.reltype,[])
        if self not in o:
            o.append(self)

        self.target = self.g.nodes_by_id[neo_edge.end_node.id]
        if self not in self.target.incoming:
            self.target.incoming.append(self)
        i = self.target.i.setdefault(self.reltype, [])
        if self not in i:
            i.append(self)
        return self