```plantuml
@startuml

agent Query
agent Result
agent Detail
agent Properties
agent EditProperty
agent 3D
circle "Resultlist\n      ID" as Resultlist
Query --> Result
Result -> Detail
Detail --> Properties
Properties --> EditProperty
Detail <-- EditProperty
Result ..> Resultlist
Resultlist .> 3D
Result <--> 3D
Detail <-- 3D
@enduml
```