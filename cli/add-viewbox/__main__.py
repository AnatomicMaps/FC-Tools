#===============================================================================

import argparse
import re
from typing import Optional

#===============================================================================

import lxml.etree as ET

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

def length_as_pixels(length: Optional[str]) -> float:
#====================================================
    if length is None:
        raise ValueError('Missing `width` and/or `height` in SVG')
    match = re.search(r'(.*)(em|ex|px|in|cm|mm|pt|pc|%)', length)
    if match is None:
        return float(length)
    else:
        scaling = __unit_scaling[match.group(2)]
        if scaling is None:
            raise ValueError('Unsupported SVG units: {}'.format(length))
        return scaling*float(match.group(1))

#===============================================================================

def add_viewbox(svg_file):
    svg = ET.parse(svg_file)
    svg_root = svg.getroot()
    width = svg_root.attrib.pop('width', None)
    height = svg_root.attrib.pop('height', None)
    if 'viewBox' not in svg_root.attrib:
        try:
            svg_root.attrib['viewBox'] = f'0 0 {length_as_pixels(width)} {length_as_pixels(height)}'
        except ValueError as e:
            raise ValueError(f'{svg_file}: {str(e)}')
    print(f'Tidied {svg_file}')
    with open(svg_file, 'wb') as fp:
        svg.write(fp, encoding='utf-8', pretty_print=True, xml_declaration=True)

#===============================================================================

def main():
    parser = argparse.ArgumentParser(description='Tidy an SVG file, adding a `viewBox` if there is none, and removing any top-level `width` and `height`')
    parser.add_argument('svg_files', metavar='SVG_FILE(S)', nargs='+',
        help='SVG file to tidy. The file is updated in place')
    args = parser.parse_args()
    for svg_file in args.svg_files:
        add_viewbox(svg_file)

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
