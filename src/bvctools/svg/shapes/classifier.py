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

import json
from pathlib import Path
from typing import Optional, TYPE_CHECKING

#===============================================================================

import shapely

#===============================================================================

if TYPE_CHECKING:
    from ..source import SVGBondgraph

from ..settings import settings

from . import Shape, SHAPE_TYPE
from .bondgraph import BG_ELEMENT_PREFIXES
from .connections import ConnectionEndFinder
from .labels import make_labels, make_name
from .line_finder import LineFinder, MAX_LINE_WIDTH
from .utils import add_class, svg_element

#===============================================================================

"""
Parse SVG.
* assign IDs to component blocks, nodes and connections (==> rewrite SVG)
* extract BG structure (as RDF)
* create a `properties.json`

"""

#===============================================================================

class ShapeClassifier:
    def __init__(self, svg_bg: 'SVGBondgraph'):
        self.__svg_bg = svg_bg
        self.__bond_graph = {
            'connections': [],
            'containers': [],
            'elements': [],
            'text': [],
        }
        self.__line_finder = LineFinder()
        self.__connections = []
        self.__elements = {}
        self.__features = {}

    @property
    def features(self):
        return self.__features

    def classify(self):
    #==================
        last_shape = None
        node_text = []
        other_text = []
        shapes = self.__svg_bg.shapes
        for shape in shapes.flatten():
            if shape.shape_type == SHAPE_TYPE.TEXT:
                if shape.text.strip() != '':
                    text_pos = (shape.left, shape.baseline)
                    if last_shape is not None and shapely.contains_xy(last_shape.geometry, *text_pos):
                        node_text.append(shape.text)
                    else:
                        other_text.append(shape.text)
            else:
                if last_shape is not None:
                    self.__output_shape(last_shape, node_text)
                    node_text = []
                    text_pos = None
                last_shape = shape
        if last_shape is not None:
            self.__output_shape(last_shape, node_text)
        if other_text:
            print('EXTRA TEXT:', make_name(other_text))

        end_finder = ConnectionEndFinder(self.__elements.values())
        for shape in self.__connections:
            ends = end_finder.get_ends(shape.connection)
            print(shape.id,
                '   ', self.__element_name(ends[0].id) if ends[0] and ends[0].id else None,
                '-->', self.__element_name(ends[1].id) if ends[1] and ends[1].id else None)

    def __element_name(self, id: str) -> Optional[str]:
    #===================================================
        if id in self.__elements:
            return self.__elements[id].name

    def save(self, output_file: str | Path):
    #=======================================
        with open(output_file, 'w') as fp:
            json.dump(self.__bond_graph, fp, indent=4)

    def __output_shape(self, shape: Shape, text: list[str]):
    #================================================================================================
        id = self.__svg_bg.get_shape_id(shape)
        if (name := make_name(text)) != '':
            shape.name = name
            if BG_ELEMENT_PREFIXES.match(name):
                bg_group = 'elements'
                add_class(shape.element, 'element')
                self.__elements[shape.id] = shape
                self.__features[id] = {
                    'name': name,
                    'label': make_labels(name)
                }
            else:
                bg_group = 'containers'
                add_class(shape.element, 'container')
            self.__bond_graph[bg_group].append({
                'id': id,
                'name': name,
                'area': shape.geometry.area,
                'fill': shape.fill,
                'stroke': shape.stroke
            })
        else:
            bounds = shape.geometry.bounds
            width = abs(bounds[2] - bounds[0])
            height = abs(bounds[3] - bounds[1])
            if (shape.geometry.area > 0
            and shape.geometry.area/(width*height) > 0.9
            and width > MAX_LINE_WIDTH
            and height > MAX_LINE_WIDTH):
                connection = None
            else:
                try:
                    connection = self.__line_finder.get_line(shape)
                except NotImplementedError:
                    connection = None
            if connection is not None:
                add_class(shape.element, 'connection')
                self.__bond_graph['connections'].append({
                    'id': id
                })
                shape.connection = connection
                self.__connections.append(shape)
                if settings.debug_connections:
                    self.__svg_bg.add_element(svg_element(connection, classes='centreline'))
            else:
                add_class(shape.element, 'container')
                self.__bond_graph['containers'].append({
                    'id': id,
                    'area': shape.geometry.area,
                    'fill': shape.fill,
                    'stroke': shape.stroke
                })

#===============================================================================
#===============================================================================
