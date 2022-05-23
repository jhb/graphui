from dotenv import load_dotenv, find_dotenv
from attr_dict import AttrDict
import os

# config
load_dotenv(find_dotenv())

config = AttrDict(debug=int(os.environ.get("GRAPHUI_DEBUG", 0)),
                  hx_boost=int(os.environ.get("GRAPHUI_HX_BOOST", 1)),
                  neo4j=os.environ.get("GRAPHUI_NEO4J", 'neo4j://localhost:7687'),
                  user=os.environ.get("GRAPHUI_USER", 'neo4j'),
                  password=os.environ.get("GRAPHUI_PASSWORD", 'admin'),
                  port=os.environ.get("GRAPHUI_PORT", '5003'),
)
