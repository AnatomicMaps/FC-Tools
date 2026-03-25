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

import re
from typing import Optional

#===============================================================================

import shapely

#===============================================================================

from ..svg import SVGDiagram

from ..shapes import Shape, SHAPE_TYPE

#===============================================================================

## This is SVG specific ==> frpm JSON
# Performed in order
TEXT_SUBSTITUTIONS = {
    'H_2_O': 'H2O',
    'Na_+': 'Na+',
    'CO_2': 'CO2',
    'O_2': 'O2',    # NB. After CO_2
    'k_idney': 'kidney',
}

def make_name(text: list[str]) -> str:
#=====================================
    name = re.sub(r'__+', '_', '_'.join(text)).replace('_._', '.')
    for s, r in TEXT_SUBSTITUTIONS.items():
        name = name.replace(s, r)
    return name

#
#===============================================================================

class ShapeClassifier:
    def __init__(self, svg_diagram: SvgDiagram):
        self.__diagram = svg_diagram
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
        for shape in self.__diagram.shapes:
            if shape.shape_type == SHAPE_TYPE.TEXT:
                if shape.text.strip() != '':
                    text_pos = (shape.left, shape.baseline)
                    if last_shape is not None and shapely.contains_xy(last_shape.geometry, *text_pos):
                        node_text.append(shape.text)
                    else:
                        other_text.append(shape.text)
            else:
                if last_shape is not None:
                    self.__set_properties(last_shape, node_text)
                    node_text = []
                    text_pos = None
                last_shape = shape
        if last_shape is not None:
            self.__set_properties(last_shape, node_text)
        if other_text:
            print('EXTRA TEXT:', other_text)

    def __set_properties(self, shape: Shape, text: list[str]):
    #=========================================================
#        id = self.__svg_shapes.get_shape_id(shape)

        if (name := make_name(text)) != '':
            shape.name = name
            properties = {
                'id': shape.id,
                'name': name,
                'stroke': shape.stroke
            }

#===============================================================================
#===============================================================================
