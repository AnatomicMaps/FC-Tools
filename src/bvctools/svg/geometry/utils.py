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

import logging
import math
import re
from typing import Optional

#===============================================================================

# https://simoncozens.github.io/beziers.py/index.html
from beziers.cubicbezier import CubicBezier
from beziers.line import Line as BezierLine
from beziers.path import BezierPath
from beziers.point import Point as BezierPoint
from beziers.quadraticbezier import QuadraticBezier

import shapely.geometry
from shapely.geometry.base import BaseGeometry

#===============================================================================

from .arc_to_bezier import bezier_segments_from_arc_endpoints, tuple2
from .transform import Transform

#===============================================================================

CM_PER_INCH = 2.54
MM_PER_INCH = 10*CM_PER_INCH

PICAS_PER_INCH = 6
POINTS_PER_INCH = 72

PIXELS_PER_INCH = 96

#===============================================================================

__unit_scaling = {
    'px': 1,
    'in': PIXELS_PER_INCH,
    'cm': PIXELS_PER_INCH/CM_PER_INCH,
    'mm': PIXELS_PER_INCH/MM_PER_INCH,
    'pt': PIXELS_PER_INCH/POINTS_PER_INCH,
    'pc': PIXELS_PER_INCH/PICAS_PER_INCH,
    '%' : None,      # 1/100.0 of viewport dimension
    'em': None,      # em/pt depends on current font size
    'ex': None,      # ex/pt depends on current font size
    }

def length_as_pixels(length: Optional[str|float], default: Optional[float]=None) -> Optional[float]:
#===================================================================================================
    if length is None:
        return default
    elif not isinstance(length, str):
        return length
    match = re.search(r'(.*)(em|ex|px|in|cm|mm|pt|pc|%)', length)
    if match is None:
        return float(length)
    else:
        scaling = __unit_scaling[match.group(2)]
        if scaling is None:
            raise ValueError('Unsupported SVG units: {}'.format(length))
        return scaling*float(match.group(1))

def length_as_points(length: str | float) -> float:
#==================================================
    if not isinstance(length, str):
        return length
    match = re.search(r'(.*)(em|ex|px|in|cm|mm|pt|pc|%)', length)
    if match is None:
        return float(length)
    else:
        return length_as_pixels(length)/__unit_scaling['px']

def percentage_dimension(percentage: Optional[str], max_size: float) -> float:
#=============================================================================
    if percentage is None:
        return max_size
    elif percentage.endswith('%'):
        return float(percentage[0:-1])*max_size/100
    else:
        return float(max_size)

#===============================================================================

# From https://codereview.stackexchange.com/questions/28502/svg-path-parsing

COMMANDS = set('MmZzLlHhVvCcSsQqTtAa')
COMMAND_RE = re.compile("([MmZzLlHhVvCcSsQqTtAa])")
FLOAT_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?")

def parse_svg_path(path):
    for x in COMMAND_RE.split(path):
        if x in COMMANDS:
            yield x
        for token in FLOAT_RE.findall(x):
            if token.upper().startswith('E'):
                token = '1' + token
            yield token

#===============================================================================

def bezier_sample(bz, num_points=100):
#=====================================
    return [(pt.x, pt.y) for pt in bz.sample(num_points)]

def circle_from_bounds(bounds):
#==============================
    centre = shapely.geometry.Point((bounds[0] + bounds[2])/2.0,
                                    (bounds[1] + bounds[3])/2.0)
    return centre.buffer(math.sqrt(abs((bounds[2] - bounds[0])*(bounds[3] - bounds[1])))/2.0)

def reflect_point(point, centre):
#================================
    return (2.0*centre[0] - point[0], 2.0*centre[1] - point[1])

#===============================================================================

def geometry_from_svg_path(path_tokens: list[str|float], transform: Transform,
                           must_close: Optional[bool]=None) -> Optional[BaseGeometry]:
    geometries = []
    coordinates = []
    moved = False
    first_point = None
    current_point = []

    pt = []
    pos = 0
    cmd = None
    second_cubic_control = None
    second_quad_control = None
    while pos < len(path_tokens):
        if isinstance(path_tokens[pos], str) and path_tokens[pos].isalpha():    # type: ignore
            cmd = path_tokens[pos]
            pos += 1
        # Else repeat previous command with new coordinates
        # with `moveTo` becoming `lineTo`
        elif cmd == 'M':
            cmd = 'L'
        elif cmd == 'm':
            cmd = 'l'

        if cmd not in ['s', 'S']:
            second_cubic_control = None
        if cmd not in ['t', 'T']:
            second_quad_control = None

        if cmd in ['a', 'A']:
            params = [float(x) for x in path_tokens[pos:pos+7]]
            pos += 7
            pt = params[5:7]
            if cmd == 'a':
                pt[0] += current_point[0]
                pt[1] += current_point[1]
            phi = math.radians(params[2])
            segs = bezier_segments_from_arc_endpoints(tuple2(*params[0:2]), phi, params[3], params[4],
                                                      tuple2(*current_point), tuple2(*pt), transform)
            coordinates.extend(bezier_sample(BezierPath.fromSegments(segs)))
            current_point = pt

        elif cmd in ['c', 'C', 's', 'S']:
            coords = [BezierPoint(*transform.transform_point(current_point))]
            if cmd in ['c', 'C']:
                n_params = 6
            else:
                n_params = 4
                if second_cubic_control is None:
                    coords.append(BezierPoint(*transform.transform_point(current_point)))
                else:
                    coords.append(BezierPoint(*transform.transform_point(
                        reflect_point(second_cubic_control, current_point))))
            params = [float(x) for x in path_tokens[pos:pos+n_params]]
            pos += n_params
            for n in range(0, n_params, 2):
                pt = params[n:n+2]
                if cmd.islower():
                    pt[0] += current_point[0]
                    pt[1] += current_point[1]
                if n == (n_params - 4):
                    second_cubic_control = pt
                coords.append(BezierPoint(*transform.transform_point(pt)))
            bz = CubicBezier(*coords)
            coordinates.extend(bezier_sample(bz))
            current_point = pt

        elif cmd in ['l', 'L', 'h', 'H', 'v', 'V']:
            if cmd in ['l', 'L']:
                params = [float(x) for x in path_tokens[pos:pos+2]]
                pos += 2
                pt = params[0:2]
                if cmd == 'l':
                    pt[0] += current_point[0]
                    pt[1] += current_point[1]
            else:
                param = float(path_tokens[pos])
                pos += 1
                if cmd == 'h':
                    param += current_point[0]
                elif cmd == 'v':
                    param += current_point[1]
                if cmd in ['h', 'H']:
                    pt = [param, current_point[1]]
                else:
                    pt = [current_point[0], param]
            if moved:
                coordinates.append(transform.transform_point(current_point))
                moved = False
            coordinates.append(transform.transform_point(pt))
            current_point = pt

        elif cmd in ['m', 'M']:
            params = [float(x) for x in path_tokens[pos:pos+2]]
            pos += 2
            pt = params[0:2]
            if first_point is None:
                # First `m` in a path is treated as `M`
                first_point = pt
            else:
                if cmd == 'm':
                    pt[0] += current_point[0]
                    pt[1] += current_point[1]
            current_point = pt
            moved = True

        elif cmd in ['q', 'Q', 't', 'T']:
            coords = [BezierPoint(*transform.transform_point(current_point))]
            if cmd in ['q', 'Q']:
                n_params = 4
            else:
                n_params = 2
                if second_quad_control is None:
                    coords.append(BezierPoint(*transform.transform_point(current_point)))
                else:
                    coords.append(BezierPoint(*transform.transform_point(
                        reflect_point(second_quad_control, current_point))))
            params = [float(x) for x in path_tokens[pos:pos+n_params]]
            pos += n_params
            for n in range(0, n_params, 2):
                pt = params[n:n+2]
                if cmd.islower():
                    pt[0] += current_point[0]
                    pt[1] += current_point[1]
                if n == (n_params - 4):
                    second_quad_control = pt
                coords.append(BezierPoint(*transform.transform_point(pt)))
            bz = QuadraticBezier(*coords)
            coordinates.extend(bezier_sample(bz))
            current_point = pt

        elif cmd in ['z', 'Z']:
            if first_point is not None and current_point != first_point:
                coordinates.append(transform.transform_point(first_point))
            if len(coordinates) < 3:
                raise ValueError("A closed shape must have at least three coordinates")
            geometries.append(shapely.geometry.Polygon(coordinates).buffer(0))
            coordinates = []
            closed = False
            moved = False
            first_point = None
            current_point = []

        else:
            logging.warning(f'Unknown SVG path command: {cmd}')

    if must_close == False and len(geometries):
        raise ValueError("Shape can't have closed geometries")
    elif must_close == True and len(geometries) == 0:
        raise ValueError("Shape must have closed geometries")

    if must_close == True and len(coordinates) >= 3:
        # Return a polygon if flagged as `closed`
        coordinates.append(coordinates[0])
        geometries.append(shapely.geometry.Polygon(coordinates).buffer(0))

    if len(geometries):
        if len(geometries) == 1:
            geometry = geometries[0]
        else:
            geometry = shapely.unary_union(geometries)
    elif len(coordinates) >= 2:
        ## Warn if start and end point are ``close`` wrt to the length of the line as shape
        ## may be intended to be closed... (test with ``cardio_8-1``)
        geometry = shapely.geometry.LineString(coordinates)
    else:
        geometry = None

    if geometry is not None and not geometry.is_valid:
        if geometry.geom_type == 'Polygon':
            # Try smoothing out boundary irregularities
            geometry = geometry.buffer(20)
        if not geometry.is_valid:
            raise ValueError(f'{geometry.geom_type} geometry is invalid')

    return geometry

#===============================================================================
#===============================================================================
