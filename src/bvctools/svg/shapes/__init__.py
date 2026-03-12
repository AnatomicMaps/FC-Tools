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

from enum import Enum
import re
from typing import Any, Optional

#===============================================================================

import lxml.etree as etree
from shapely.geometry.base import BaseGeometry

#===============================================================================

BG_ELEMENT_PREFIXES = re.compile(r'q_|v_|u_|K_|TF_|FTU: ')

#===============================================================================

class SHAPE_TYPE(str, Enum):
    ANNOTATION = 'annotation'
    BOUNDARY   = 'boundary'
    COMPONENT  = 'component'
    CONNECTION = 'connection'
    CONTAINER  = 'container'
    GROUP      = 'group'
    IMAGE      = 'image'
    TEXT       = 'text'
    UNKNOWN    = 'unknown'

#===============================================================================

class Shape:
    def __init__(self, element: etree.Element, geometry: BaseGeometry, properties: Optional[dict]=None, **kwds):
        self.__element = element
        self.__geometry = geometry
        self.__properties = {}
        if properties is not None:
            self.__properties.update(properties)
        for key, value in kwds.items():
            self.__setattr__(key, value)
        if self.shape_type is None:
            self.shape_type = SHAPE_TYPE.UNKNOWN
        if (id := element.attrib.get('id')) is not None:
            self.__properties['id'] = id

    def __getattr__(self, key: str) -> Any:
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        else:
            return self.__properties.get(key.replace('_', '-'))

    def __setattr__(self, key: str, value: Any=None):
        if key.startswith('_'):
            object.__setattr__(self, key, value)
        else:
            self.__properties[key.replace('_', '-')] = value

    @property
    def element(self) -> etree.Element:
        return self.__element

    @property
    def geometry(self):
        return self.__geometry

    @property
    def id(self) -> Optional[str]:
        return self.__properties.get('id')

    @property
    def properties(self):
        return self.__properties

#===============================================================================
#===============================================================================
