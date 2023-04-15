Match (n) detach delete n;
CREATE
(label:Label              {name: 'Label',
                           description: 'Defines a Label',
                           graph: 'metaschema'}),

(relation:Label           {name: 'Relation',
                           description: 'Defines a Relation type',
                           graph: 'metaschema'}),

(property:Label            {name: 'Property',
                           description: 'Defines a Property',
                           graph: 'metaschema'}),

(source:Relation          {name: 'SOURCE',
                           description: 'Start labels of Relation',
                           sourcearity: '*',
                           targetarity: '*',
                           graph: 'metaschema'}),

(target:Relation          {name: 'TARGET',
                           description: 'End labels of relation',
                           sourcearity: '*',
                           targetarity: '*',
                           graph: 'metaschema'}),

(prop:Relation            {name: 'PROP',
                           description: 'Label has Property',
                           sourcearity: '*',
                           targetarity: '*',
                           graph: 'metaschema'}),

(name:Property            {name: 'name',
                           description: 'name of a node',
                           widget: 'string',
                           graph: 'metaschema'}),

(sourcearity:Property     {name: 'sourcearity',
                           description: 'How many relations of this type can the source have',
                           arity: '1',
                           widget: 'string',
                           graph: 'metaschema'}),

(targetarity:Property     {name: 'targetarity',
                           description: 'How many relations of this type can the target have',
                           arity: '1',
                           widget: 'string',
                           graph: 'metaschema'}),

(widget:Property          {name: 'widget',
                           description: 'What widget to use for this property (implies scalar)',
                           widget: 'string',
                           graph: 'metaschema'}),

(description:Property     {name: 'description',
                           description: 'What does it mean?',
                           widget: 'string',
                           graph: 'metaschema'}),

(arity:Property           {name: 'arity',
                           description: 'How many values (regex style)',
                           widget: 'string',
                           arity: '?',
                           graph: 'metaschema'}),

(person:Label             {name: 'Person',
                           description: 'A living human',
                           graph: 'metaschema'}),

(firstname:Property       {name: 'firstname',
                           description: 'Given name',
                           widget: 'string',
                           graph: 'metaschema'}),

(lastname:Property        {name: 'lastname',
                           description: 'Family name',
                           widget: 'string',
                           graph: 'metaschema'}),

(likes:Relation           {name: 'LIKES',
                           description: 'xoxoxo',
                           sourcearity: '*',
                           targetarity: '*',
                           graph: 'metaschema'}),

(alice:Person             {name: 'alice',
                           firstname: 'Alice',
                           lastname: 'Alison',
                           graph: 'metaschema'}),

(bob:Person               {name: 'bob',
                           firstname: 'Bob',
                           lastname: 'Bobson',
                           graph: 'metaschema'}),

(label)-[:PROP]->(name),
(relation)-[:PROP]->(name),
(property)-[:PROP]->(name),
(label)-[:SOURCE]->(prop),
(label)-[:PROP]->(description),
(source)-[:TARGET]->(label),
(target)-[:TARGET]->(label),
(relation)-[:SOURCE]->(source),
(relation)-[:SOURCE]->(target),
(relation)-[:PROP]->(description),
(property)-[:PROP]->(arity),
(prop)-[:TARGET]->(property),
(property)-[:PROP]->(description),
(relation)-[:PROP]->(sourcearity),
(relation)-[:PROP]->(targetarity),
(property)-[:PROP]->(widget),

(person)-[:PROP]->(firstname),
(person)-[:PROP]->(lastname),
(likes)-[:SOURCE]->(person),
(person)-[:TARGET]->(likes),
(person)-[:PROP]->(name),

(alice)-[:LIKES]->(bob),
(bob)-[:LIKES]->(alice);

// The whole graph above
match (n {graph:'metaschema'}) return *;

// Just fetch the metagraph itself, e.g. all definitions

match (n)-[r:PROP|SOURCE|TARGET]-() where n:Label or n:Relation or n:Property return *;