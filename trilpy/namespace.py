"""Extra trilpy namespaces for use with rdflib."""
from rdflib import Namespace
# from rdflib.namespace import NamespaceManager

LDP = Namespace('http://www.w3.org/ns/ldp#')
ACL = Namespace('http://www.w3.org/ns/auth/acl#')
EX = Namespace('http://example.org/')

# class Graph(Graph_rdflib):
#
#    def __init__(self):
#        """Initialize Graph with useful prefixes."""
#        super(Graph).__init__()
#        #self.bind("ldp", LDP)
