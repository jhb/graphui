from settings import config
from neo4j_db import Connection

connection = Connection(config.neo4j, config.user, config.password)
graph = connection.graph(debug=config.debug)

graph.run('DROP INDEX _searchableText if exists')
labels = [r['label'] for r  in graph.run('call db.labels()')]
propnames = [r['propertyKey'] for r  in graph.run('call db.propertyKeys()')]
labelstring = '|'.join(labels)
propstring = ','.join([f'n.`{p}`' for p in propnames])
statement = f"CREATE FULLTEXT INDEX _searchableText FOR (n:{labelstring}) ON EACH [{propstring}]"
print(statement)
graph.run(statement)

# automatic reindexing on new properties?
