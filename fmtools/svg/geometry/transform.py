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

from math import acos, cos, pi as PI, radians, sin, tan
from typing import Optional

#===============================================================================

import numpy as np
import transforms3d

#===============================================================================
#===============================================================================

class Transform(object):
    def __init__(self, matrix):
        self.__matrix = np.array(matrix)
        self.__shapely_matrix = np.concatenate((self.__matrix[0, 0:2],
                                                self.__matrix[1, 0:2],
                                                self.__matrix[0:2, 2]), axis=None).tolist()

    def __matmul__(self, transform):
        if isinstance(transform, Transform):
            return Transform(self.__matrix@np.array(transform.__matrix))
        else:
            return Transform(self.__matrix@np.array(transform))

    def __str__(self):
        return str(self.__matrix)

    @classmethod
    def Identity(cls):
        return cls(np.identity(3))

    @classmethod
    def scale(cls, scale: float):
        return cls([[scale, 0, 0], [0, scale, 0], [0, 0, 1]])

    @classmethod
    def translate(cls, tx: float, ty: float):
        return cls([[1, 0, tx], [0, 1, ty], [0, 0, 1]])

    @property
    def matrix(self):
        return self.__matrix

    @property
    def svg_matrix(self):
        return np.array([self.__matrix[0, 0], self.__matrix[1, 0],
                         self.__matrix[0, 1], self.__matrix[1, 1],
                         self.__matrix[0, 2], self.__matrix[1, 2]])

    def flatten(self):
    #=================
        return self.__matrix.flatten()

    def inverse(self):
    #=================
        return Transform(np.linalg.inv(self.__matrix))

    def rotate_angle(self, angle):
    #==============================
        rotation = transforms3d.affines.decompose(self.__matrix)[1]
        theta = acos(rotation[0, 0])
        if rotation[0, 1] >= 0:
            theta = 2*PI - theta
        angle = angle + theta
        while angle >= 2*PI:
            angle -= 2*PI
        return angle

    def scale_length(self, length):
    #==============================
        scaling = transforms3d.affines.decompose(self.__matrix)[2]
        return (abs(scaling[0]*length[0]), abs(scaling[1]*length[1]))

    def transform_point(self, point) -> tuple[float, float]:
    #=======================================================
        return tuple(self.__matrix@[point[0], point[1], 1.0])[:2]

#===============================================================================
#===============================================================================

class SVGTransform(Transform):
    def __init__(self, transform: Optional[str]):
        T = np.identity(3)
        if transform is not None:
            # A simple parser, assuming well-formed SVG
            tokens = transform.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
            pos = 0
            while pos < len(tokens):
                xfm = tokens[pos]
                pos += 1
                if xfm == 'matrix':
                    params = tuple(float(x) for x in tokens[pos:pos+6])
                    pos += 6
                    T = T@np.array([[params[0], params[2], params[4]],
                                    [params[1], params[3], params[5]],
                                    [        0,         0,         1]])
                elif xfm == 'translate':
                    x = float(tokens[pos])
                    pos += 1
                    if pos >= len(tokens) or tokens[pos].isalpha():
                        y = 0
                    else:
                        y = float(tokens[pos])
                        pos += 1
                    T = T@np.array([[1, 0, x],
                                    [0, 1, y],
                                    [0, 0, 1]])
                elif xfm == 'scale':
                    sx = float(tokens[pos])
                    pos += 1
                    if pos >= len(tokens) or tokens[pos].isalpha():
                        sy = sx
                    else:
                        sy = float(tokens[pos])
                        pos += 1
                    T = T@np.array([[sx,  0, 0],
                                    [ 0, sy, 0],
                                    [ 0,  0, 1]])
                elif xfm == 'rotate':
                    a = radians(float(tokens[pos]))
                    pos += 1
                    if pos >= len(tokens) or tokens[pos].isalpha():
                        T = T@np.array([[cos(a), -sin(a), 0],
                                        [sin(a),  cos(a), 0],
                                        [     0,       0, 1]])
                    else:
                        (cx, cy) = tuple(float(x) for x in tokens[pos:pos+2])
                        pos += 2
                        T = T@np.array([[cos(a), -sin(a), -cx*cos(a) + cy*sin(a) + cx],
                                        [sin(a),  cos(a), -cx*sin(a) - cy*cos(a) + cy],
                                        [     0,       0,                           1]])
                elif xfm == 'skewX':
                    a = float(tokens[pos])
                    pos += 1
                    T = T@np.array([[1, tan(a), 0],
                                    [0,      1, 0],
                                    [0,      0, 1]])
                elif xfm == 'skewY':
                    a = float(tokens[pos])
                    pos += 1
                    T = T@np.array([[     1, 0, 0],
                                    [tan(a), 1, 0],
                                    [     0, 0, 1]])
                else:
                    raise ValueError('Invalid SVG transform: {}'.format(transform))
        super().__init__(T)

#===============================================================================
#===============================================================================
