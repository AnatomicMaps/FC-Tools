#===============================================================================
#
#  Flatmap viewer and annotation tools
#
#  Copyright (c) 2020 - 2025  David Brooks
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#===============================================================================

from ..rdf import Literal, Namespace, RDFGraph, URIRef
from ..svg import SVGDiagram
from ..utils.colours import ColourMatcherDict

from .classifier import ShapeClassifier
from .namespaces import BGF, NAMESPACES, RDF, RDFS

#===============================================================================

BONDGRAPH_NODES = ColourMatcherDict({
    '#00B050': 'dissapator',        # green         v
    '#042433': 'reaction',          # navy blue     v
    '#FF0000': 'storage',           # red           q, u
})
    # 'K'
    # 'TF'      "TF_NTS_f.br"
    # 'FTU:'    "FTU: Cardiomyocyte"

#===============================================================================

BONDGRAPH_SPECIFIC_ELEMENTS = {
    'dissapator': {
        'H2O': BGF.HydraulicResistanceNode,
        'Na+': BGF.ChemicalReactionNode,
        'NKE': BGF.NKETransporterNode,
    },
    'reaction': {
        'H2O': BGF.HydraulicResistanceNode,
        'Na+': BGF.ChemicalReactionNode,
        'NKE': BGF.NKETransporterNode,
    },
    'storage': {
        'H2O': BGF.HydraulicElasticStorageNode,
        'Na+': BGF.ChemicalStorageNode,
    },
}

#===============================================================================

def bond_element(properties: dict) -> URIRef:
#============================================
    element_type = None
    if 'stroke' in properties:
        element_type = BONDGRAPH_NODES.lookup(properties['stroke'])
    else:
        base_symbol = properties['symbol']
        if base_symbol in ['q', 'u']:
            element_type = 'storage'
        elif base_symbol == 'v':
            element_type = 'dissapator'
    if element_type is not None:
        element = BONDGRAPH_SPECIFIC_ELEMENTS.get(element_type, {}).get(properties['species'])
        if element is None:
            raise ValueError(f'Cannot find specific element for {element_type} {properties['name']}')
        return element
    raise ValueError(f'Cannot find determine element type for {properties['name']}')


'''
:ID-0000040 a bgf:q ;
    bgf:hasSymbol "q_pt_Na+" .

:ID-0000010 a bgf:q ;
    bgf:hasSymbol "q_vc_H2O_,_u_vc_osmotic" .


"symbol": "u",
            "species": "Na+",
            "location": "gi",


'''

def make_symbol(properties: dict) -> Literal:
#============================================
    symbol = [
        properties['symbol'],
        properties['location'],
        properties['species'].replace('Na+', 'Na')
    ]
    return Literal('_'.join(symbol))

#===============================================================================
#===============================================================================

MODEL_NS = Namespace('#')

#===============================================================================

class BondgraphMaker:
    def __init__(self, svg_bg: SVGDiagram):
        self.__uri = MODEL_NS[svg_bg.id]
        self.__rdf_graph = RDFGraph(NAMESPACES)
        self.__rdf_graph.add_namespace('', str(MODEL_NS))
        self.__rdf_graph.add((self.__uri, RDF.type, BGF.BondgraphModel))
        self.__classified_shapes = {
            'compartments': {},
            'connections': {},
            'elements': {},
        }
        self.__classifier = ShapeClassifier(svg_bg, self)
        self.__classifier.classify()

    @property
    def classified_shapes(self):
        return self.__classified_shapes

    @property
    def features(self):
        return self.__classifier.features

    def add_compartment(self, properties: dict):
    #===========================================
        id = properties['id']
        self.__classified_shapes['compartments'][id] = properties

    def add_connection(self, properties: dict):
    #==========================================
        id = properties['id']
        self.__classified_shapes['connections'][id] = properties
        uri = MODEL_NS[id]
        self.__rdf_graph.add((uri, BGF.hasSource, MODEL_NS[properties['source']]))
        self.__rdf_graph.add((uri, BGF.hasTarget, MODEL_NS[properties['target']]))

    def add_element(self, properties: dict):
    #=======================================
        id = properties['id']
        self.__classified_shapes['elements'][id] = properties
        uri = MODEL_NS[id]
        self.__rdf_graph.add((self.__uri, BGF.hasBondElement, uri))
        self.__rdf_graph.add((uri, RDF.type, bond_element(properties)))
        self.__rdf_graph.add((uri, BGF.hasSymbol, make_symbol(properties)))
        if 'label' in properties:
            self.__rdf_graph.add((uri, RDFS.label, Literal(properties['label'])))

    def save_bondgraph(self, output_file):
    #=====================================
        with open(output_file, 'w') as fp:
            fp.write(self.__rdf_graph.serialise())

#===============================================================================
#===============================================================================
