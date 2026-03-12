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

from typing import Optional

#===============================================================================

from shapely.geometry.base import BaseGeometry
import lxml.etree as etree

#===============================================================================

from ..settings import settings
from ..source import SVG_NS

#===============================================================================

def add_class(element: etree.Element, cls: str):
#===============================================
    if settings.add_classes:
        classes = element.attrib.get('class', '').split()
        if cls not in classes:
            classes.append(cls)
            element.attrib['class'] = ' '.join(classes)

def svg_element(geometry: BaseGeometry, classes: Optional[str]=None) -> etree.Element:
#=====================================================================================
    svg = geometry.svg().split()
    svg.insert(1, f'xmlns="{SVG_NS}"')
    element = etree.fromstring(' '.join(svg))
    if classes is not None:
        element.attrib['class'] = classes
    return element

#===============================================================================
#===============================================================================
