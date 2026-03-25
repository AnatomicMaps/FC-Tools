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

from collections import defaultdict
import logging
from pathlib import Path
import re
from typing import Optional
import unicodedata

#===============================================================================

from cssselect2 import ElementWrapper
import lxml.etree as etree
from shapely.geometry.base import BaseGeometry
import shapely.ops
import skia

#===============================================================================

from ..shapes import PropertyDict, Shape, SHAPE_TYPE

from .definitions import DefinitionStore, ObjectStore
from .geometry.transform import SVGTransform, Transform
from .geometry.utils import circle_from_bounds, geometry_from_svg_path, length_as_pixels
from .geometry.utils import length_as_points, parse_svg_path
from .styling import StyleMatcher, wrap_element

#===============================================================================

SVG_NS = 'http://www.w3.org/2000/svg'

def SVG_TAG(tag):        # An SVG namespaced lxml.etree tag
    return f'{{{SVG_NS}}}{tag}'

# These SVG tags are not used to determine shape geometry
IGNORED_SVG_TAGS = [
    SVG_TAG('font'),
    SVG_TAG('linearGradient'),
    SVG_TAG('radialGradient'),
    SVG_TAG('style'),
    SVG_TAG('title'),
]

# These SVG tags determine shape geometry
SVG_GEOMETRIC_ELEMENTS = [
    SVG_TAG('circle'),
    SVG_TAG('ellipse'),
    SVG_TAG('line'),
    SVG_TAG('path'),
    SVG_TAG('polyline'),
    SVG_TAG('polygon'),
    SVG_TAG('rect')
]

#===============================================================================

# Self assigned IDs have this prefix
ID_PREFIX = 'ID-'

#===============================================================================

class SVGDiagram:
    def __init__(self, svg_source: str | Path):
        source_path = Path(svg_source)
        self.__id = source_path.stem.replace(' ', '_')
        self.__svg = etree.parse(source_path).getroot()
        self.__transform = Transform.Identity()
        self.__style_matcher = StyleMatcher(self.__svg.find(f'.//{SVG_TAG('style')}'))
        self.__definitions = DefinitionStore()
        self.__clip_geometries = ObjectStore()
        self.__shapes: list[Shape] = []
        self.__features:  dict[str, PropertyDict] = {}
        self.__init_element_id()

    @property
    def id(self) -> str:
        return self.__id

    @property
    def features(self) -> dict[str, PropertyDict]:
        return self.__features

    def process(self):
    #=================
        self.__extract_shapes()
        self.__extract_features()

    def __extract_features(self):
    #============================
        last_shape = None
        node_text = []
        other_text = defaultdict(list)
        for shape in self.__shapes:
            if shape.shape_type == SHAPE_TYPE.TEXT:
                if shape.text.strip() != '':
                    text_pos = (shape.left, shape.baseline)
                    if last_shape is not None and shapely.contains_xy(last_shape.geometry, *text_pos):
                        node_text.append(shape.text)
                    else:
                        other_text[shape.id].append(shape.text)
            else:
                if last_shape is not None:
                    self.__add_feature(last_shape, node_text)
                    node_text = []
                    text_pos = None
                last_shape = shape
        if last_shape is not None:
            self.__add_feature(last_shape, node_text)
        if other_text:
            print('EXTRA TEXT:', other_text)

    def __add_feature(self, shape: Shape, text: list[str]):
    #=========================================================
        if (name := re.sub(r'__+', '_', '_'.join(text)).replace('_._', '.')) != '':
            shape.name = name
            id = self.__get_shape_id(shape)
            self.__features[id] = {
                'name': name,
                'fill': shape.fill,
                'stroke': shape.stroke
            }

    def __extract_shapes(self):
    #==========================
        self.__process_element_list(wrap_element(self.__svg), self.__transform)

    def save_svg(self, svg_output: str | Path):
    #==========================================
        svg = etree.ElementTree(self.__svg)
        with open(svg_output, 'wb') as fp:
            svg.write(fp, encoding='utf-8', pretty_print=True, xml_declaration=True)

    def __get_shape_id(self, shape: Shape) -> str:
    #=============================================
        if (id := shape.id) is None:
            id = self.__next_element_id()
            shape.element.attrib['id'] = id
            shape.properties['id'] = id
        return id

    def __next_element_id(self) -> str:
    #==================================
        self.__last_id += 1
        print('get id', self.__last_id)
        return f'{ID_PREFIX}{self.__last_id:07}'

    def __init_element_id(self):
    #===========================
        max_id = -1
        for xml_element in self.__svg.findall('.//*[@id]'):
            id = xml_element.attrib['id']
            if id.startswith(ID_PREFIX):
                if (id := int(id[len(ID_PREFIX):])) > max_id:
                    max_id = id
        self.__last_id = max_id + 1

    def __get_transform(self, wrapped_element) -> Transform:
    #=======================================================
        element_style = self.__style_matcher.element_style(wrapped_element)
        T = SVGTransform(element_style.get(
            'transform', wrapped_element.etree_element.attrib.get('transform')))
        transform_origin = element_style.get(
            'transform-origin', wrapped_element.etree_element.attrib.get('transform-origin'))
        transform_box = element_style.get(
            'transform-box', wrapped_element.etree_element.attrib.get('transform-box'))
        if transform_box is not None:
            raise ValueError('Unsupported `transform-box` attribute -- please normalise SVG source')
        if transform_origin is None:
            return T
        try:
            translation = [pixels for l in transform_origin.split()
                                if (pixels := length_as_pixels(l)) is not None]
            return (SVGTransform(f'translate({translation[0]}, {translation[1]})')
                   @T
                   @SVGTransform(f'translate({-translation[0]}, {-translation[1]})'))
        except ValueError:
            raise ValueError('Unsupported `transform-origin` units -- please normalise SVG source')

    def __process_group(self, wrapped_group: ElementWrapper, transform):
    #===================================================================
        group = wrapped_group.etree_element
        if len(group) == 0:
            return None
        group_transform = self.__get_transform(wrapped_group)
        self.__process_element_list(wrapped_group, transform@group_transform)

    def __process_element_list(self, elements: ElementWrapper, transform):
    #=====================================================================
        children = list(elements.iter_children())
        for wrapped_element in children:
            element = wrapped_element.etree_element
            if (element.tag is etree.Comment
             or element.tag is etree.PI
             or element.tag in IGNORED_SVG_TAGS):
                continue
            elif element.tag == SVG_TAG('defs'):
                self.__add_definitions(element, transform)
                continue
            elif element.tag == SVG_TAG('use'):
                element = self.__definitions.use(element)
                wrapped_element = wrap_element(element)
            if element is not None and element.tag == SVG_TAG('clipPath'):
                self.__add_clip_geometry(element, transform)
            else:
                self.__process_element(wrapped_element, transform)

    def __add_definitions(self, defs_element, transform):
    #====================================================
        for element in defs_element:
            if element.tag == SVG_TAG('clipPath'):
                self.__add_clip_geometry(element, transform)
            else:
                self.__definitions.add_definition(element)

    def __add_clip_geometry(self, clip_path_element, transform):
    #===========================================================
        if ((clip_id := clip_path_element.attrib.get('id')) is not None
        and (geometry := self.__get_clip_geometry(clip_path_element, transform)) is not None):
            self.__clip_geometries.add(clip_id, geometry)

    def __get_clip_geometry(self, clip_path_element, transform) -> Optional[BaseGeometry]:
    #====================================================================================
        geometries = []
        for element in clip_path_element:
            if element.tag == SVG_TAG('use'):
                element = self.__definitions.use(element)
            if element is not None and element.tag in SVG_GEOMETRIC_ELEMENTS:
                properties = {}
                geometry = self.__get_geometry(element, properties, transform)
                if geometry is not None:
                    geometries.append(geometry)
        return shapely.ops.unary_union(geometries) if len(geometries) else None

    def __process_element(self, wrapped_element: ElementWrapper, transform):
    #=======================================================================
        element = wrapped_element.etree_element
        element_style = self.__style_matcher.element_style(wrapped_element)
        properties = {}
        if element.tag in SVG_GEOMETRIC_ELEMENTS:
            #if element.attrib.get('id') == 'ID-0000551':
            #    breakpoint()
            geometry = self.__get_geometry(element, properties, transform)
            if geometry is None:
                return
            # Ignore element if fill is none and no stroke is specified
            elif (element_style.get('fill', '#FFF') == 'none'
            and element_style.get('stroke', 'none') == 'none'
            and 'id' not in properties):
                return
            else:
                properties['fill'] = element_style.get('fill', 'none')
                properties['stroke'] = element_style.get('stroke', 'none')
                self.__shapes.append(Shape(element, geometry, properties))
        elif element.tag == SVG_TAG('image'):
            geometry = None
            clip_path_url = element_style.pop('clip-path', None)
            if clip_path_url is not None:
                if ((geometry := self.__clip_geometries.get_by_url(clip_path_url)) is None
                and (clip_path_element := self.__definitions.get_by_url(clip_path_url)) is not None):
                    T = transform@self.__get_transform(wrapped_element)
                    geometry = self.__get_clip_geometry(clip_path_element, T)
                if geometry is not None:
                    self.__shapes.append(Shape(element, geometry, properties, shape_type=SHAPE_TYPE.IMAGE))
        elif element.tag == SVG_TAG('g'):
            self.__process_group(wrapped_element, transform)
        elif element.tag == SVG_TAG('text'):
            geometry = self.__process_text(element, properties, transform)
            if geometry is not None:
                self.__shapes.append(Shape(element, geometry, properties, shape_type=SHAPE_TYPE.TEXT))
        else:
            logging.warning(f'SVG element {element.tag} not processed...')

    def __get_geometry(self, element, properties, transform) -> Optional[BaseGeometry]:
    #==================================================================================
    ##
    ## Returns path element as a `shapely` object.
    ##
        path_tokens = []
        if element.tag == SVG_TAG('path'):
            path_tokens = list(parse_svg_path(element.attrib.get('d', '')))

        elif element.tag in [SVG_TAG('rect'), SVG_TAG('image')]:
            x: float = length_as_pixels(element.attrib.get('x'), 0)  # type: ignore
            y: float = length_as_pixels(element.attrib.get('y'), 0)  # type: ignore

            width = length_as_pixels(element.attrib.get('width'))
            height = length_as_pixels(element.attrib.get('height'))
            if width is None or height is None:
                return None

            rx = length_as_pixels(element.attrib.get('rx'))
            ry = length_as_pixels(element.attrib.get('ry'))
            if rx is None and ry is None:
                rx = ry = 0
            elif ry is None:
                ry = rx
            elif rx is None:
                rx = ry

            rx = min(rx, width/2)   # type: ignore
            ry = min(ry, height/2)  # type: ignore
            if rx == 0 and ry == 0:
                path_tokens = ['M', x, y,
                               'H', x+width,
                               'V', y+height,
                               'H', x,
                               'V', y,
                               'Z']
            else:
                path_tokens = ['M', x+rx, y,
                               'H', x+width-rx,
                               'A', rx, ry, 0, 0, 1, x+width, y+ry,
                               'V', y+height-ry,
                               'A', rx, ry, 0, 0, 1, x+width-rx, y+height,
                               'H', x+rx,
                               'A', rx, ry, 0, 0, 1, x, y+height-ry,
                               'V', y+ry,
                               'A', rx, ry, 0, 0, 1, x+rx, y,
                               'Z']

        elif element.tag == SVG_TAG('line'):
            x1 = length_as_pixels(element.attrib.get('x1', 0))
            y1 = length_as_pixels(element.attrib.get('y1', 0))
            x2 = length_as_pixels(element.attrib.get('x2', 0))
            y2 = length_as_pixels(element.attrib.get('y2', 0))
            path_tokens = ['M', x1, y1, x2, y2]

        elif element.tag == SVG_TAG('polyline'):
            points = element.attrib.get('points', '').replace(',', ' ').split()
            path_tokens = ['M'] + points

        elif element.tag == SVG_TAG('polygon'):
            points = element.attrib.get('points', '').replace(',', ' ').split()
            path_tokens = ['M'] + points + ['Z']

        elif element.tag == SVG_TAG('circle'):
            cx: float = length_as_pixels(element.attrib.get('cx'), 0)  # type: ignore
            cy: float = length_as_pixels(element.attrib.get('cy'), 0)  # type: ignore
            r = length_as_pixels(element.attrib.get('r'))
            if r is None:
                return None
            path_tokens = ['M', cx+r, cy,
                           'A', r, r, 0, 0, 0, cx, cy-r,
                           'A', r, r, 0, 0, 0, cx-r, cy,
                           'A', r, r, 0, 0, 0, cx, cy+r,
                           'A', r, r, 0, 0, 0, cx+r, cy,
                           'Z']

        elif element.tag == SVG_TAG('ellipse'):
            cx: float = length_as_pixels(element.attrib.get('cx'), 0)   # type: ignore
            cy: float = length_as_pixels(element.attrib.get('cy'), 0)   # type: ignore
            rx = length_as_pixels(element.attrib.get('rx'))
            ry = length_as_pixels(element.attrib.get('ry'))
            if rx is None or ry is None:
                return None
            path_tokens = ['M', cx+rx, cy,
                           'A', rx, ry, 0, 0, 0, cx, cy-ry,
                           'A', rx, ry, 0, 0, 0, cx-rx, cy,
                           'A', rx, ry, 0, 0, 0, cx, cy+ry,
                           'A', rx, ry, 0, 0, 0, cx+rx, cy,
                           'Z']

        if properties.get('node', False):
            must_close = True
        elif properties.get('centreline', False):
            must_close = False
        else:
            must_close = properties.get('closed', None)
        try:
            wrapped_element = wrap_element(element)
            geometry = geometry_from_svg_path(path_tokens,
                transform@self.__get_transform(wrapped_element), must_close)
            if geometry is not None and properties.get('node', False):
                # All centeline nodes become circles
                geometry = circle_from_bounds(geometry.bounds)
            return geometry
        except ValueError as err:
            logging.warning(f"{err}: {properties.get('markup')}")

    def __process_text(self, element, properties, transform: Transform) -> Optional[BaseGeometry]:
    #=============================================================================================
        attribs = element.attrib
        style_rules = dict(attribs)
        if 'style' in attribs:
            styling = attribs.pop('style')
            style_rules.update(dict([rule.split(':', 1) for rule in [rule.strip()
                                                for rule in styling[:-1].split(';')]]))
        font_style = skia.FontStyle(int(style_rules.get('font-weight', skia.FontStyle.kNormal_Weight)),
                                    skia.FontStyle.kNormal_Width,
                                    skia.FontStyle.kUpright_Slant)
        type_face = None
        element_text = ' '.join(' '.join([t.replace('\u200b', '') for t in element.itertext()]).split())
        if element_text == '':
            element_text = ' '
        font_manager = skia.FontMgr()
        for font_family in style_rules.get('font-family', 'Calibri').split(','):
            type_face = font_manager.matchFamilyStyle(font_family, font_style)
            if type_face is not None:
                break
        if type_face is None:
            type_face = font_manager.matchFamilyStyle(None, font_style)
        font = skia.Font(type_face, length_as_points(style_rules.get('font-size', 10)))
        bounds = skia.Rect()
        width = font.measureText(element_text, skia.TextEncoding.kUTF8, bounds)
        height = font.getSpacing()
        halign = attribs.get('text-anchor')  # end, middle, start
        [x, y] = [float(attribs.get('x', 0)), float(attribs.get('y', 0))]
        if halign == 'middle':
            x -= width/2
        elif halign == 'end':
            x -= width
        valign = attribs.get('dominant-baseline')  # auto, middle
        if valign == 'middle':
            y += height/2
        metrics = font.getMetrics()
        bds = bounds.asScalars()
        if (top := bds[1]) == 0:
            top = metrics.fXHeight
        if (right := bds[2]) == 0:
            right = width
        path_tokens = ['M', x+bds[0], y+top,
                       'H', x+right,
                       'V', y+bds[3],
                       'H', x+bds[0],
                       'V', y+top,
                       'Z']
        wrapped_element = wrap_element(element)
        T = transform@self.__get_transform(wrapped_element)
        geometry = geometry_from_svg_path(path_tokens, T, True)
        bounds = shapely.bounds(geometry)
        properties['left'] = bounds[0]
        properties['right'] = bounds[2]
        properties['baseline'] = T.transform_point((x, y))[1]
        properties['text'] = unicodedata.normalize('NFKD', element_text).replace('\u2212', '-')  ## minus-sign --> minus
        properties['font-family'] = font.getTypeface().getFamilyName()

        return geometry             # type: ignore

#===============================================================================
#===============================================================================
