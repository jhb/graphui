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
                           widget: 'string',
                           graph: 'metaschema'}),

(targetarity:Property     {name: 'targetarity',
                           description: 'How many relations of this type can the target have',
                           widget: 'string',
                           graph: 'metaschema'}),

(widget:Property          {name: 'widget',
                           description: 'What widget to use for this property (implies scalar)',
                           widget: 'string',
                           graph: 'metaschema'}),

(description:Property     {name: 'description',
                           description: 'What does it mean?',
                           arity: '?',
                           widget: 'string',
                           graph: 'metaschema'}),


(human:Label             {name: 'Human',
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

(alice:Human             { firstname: 'Alice',
                           lastname: 'Alison',
                           graph: 'metaschema'}),

(bob:Human               { firstname: 'Bob',
                           lastname: 'Bobson',
                           graph: 'metaschema'}),

(label)-[:PROP]->(name),
(relation)-[:PROP]->(name),
(property)-[:PROP]->(name),
(label)-[:SOURCE]->(prop),
(label)-[:PROP]->(description),
(label)-[:SOURCE]->(source),
(target)-[:TARGET]->(label),
(source)-[:TARGET]->(relation),
(relation)-[:SOURCE]->(target),
(relation)-[:PROP]->(description),
(prop)-[:TARGET]->(property),
(relation)-[:SOURCE]->(prop),
(property)-[:PROP]->(description),
(relation)-[:PROP]->(sourcearity),
(relation)-[:PROP]->(targetarity),
(property)-[:PROP]->(widget),

(human)-[:PROP]->(firstname),
(human)-[:PROP]->(lastname),
(human)-[:SOURCE]->(likes),
(likes)-[:TARGET]->(human),

(alice)-[:LIKES]->(bob),
(bob)-[:LIKES]->(alice);

// The whole graph above
match (n {graph:'metaschema'}) return *;

// Just fetch the metagraph itself, e.g. all definitions

match (n) where n:Label or n:Relation or n:Property optional match (n)-[r:PROP|SOURCE|TARGET]-(m) return *;