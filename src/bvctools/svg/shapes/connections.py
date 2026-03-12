#===============================================================================
#
#  Flatmap viewer and annotation tools
#
#  Copyright (c) 2018 - 2025  David Brooks
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

from typing import Iterable, Optional

#===============================================================================

from shapely import LineString, Point
import shapely.strtree

#===============================================================================

from . import Shape, SHAPE_TYPE

#===============================================================================

MAX_CONNECTION_GAP = 100

#===============================================================================

class ConnectionEndFinder:
    def __init__(self, shapes: Iterable[Shape]):
        self.__geometries = []
        self.__shapes_by_geometry = {}
        for shape in shapes:
            self.__shapes_by_geometry[id(shape.geometry)] = shape
            self.__geometries.append(shape.geometry)
        self.__index = shapely.strtree.STRtree(self.__geometries)

    def get_ends(self, connection: LineString) -> tuple[Optional[Shape], Optional[Shape]]:
    #=====================================================================================
        coords = connection.coords    ## Assume a LineString
        return (self.__nearest_geometry(coords[0]), self.__nearest_geometry(coords[-1]))

    def __nearest_geometry(self, point: tuple) -> Optional[Shape]:
    #=============================================================
        pt = Point(point)
        index = self.__index.nearest(pt)
        closest_geometry = self.__geometries[index]
        if closest_geometry.distance(pt) < MAX_CONNECTION_GAP:
            return self.__shapes_by_geometry[id(closest_geometry)]
        else:
            print('distance:', closest_geometry.distance(pt))

#===============================================================================
#===============================================================================
