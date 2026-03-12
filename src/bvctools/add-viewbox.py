#===============================================================================

import argparse

#===============================================================================

import lxml.etree as ET

#===============================================================================

from svg.geometry.utils import length_as_pixels

#===============================================================================

def add_viewbox(svg_file):
    svg = ET.parse(svg_file)
    svg_root = svg.getroot()
    width = svg_root.attrib.pop('width', None)
    height = svg_root.attrib.pop('height', None)
    if 'viewBox' not in svg_root.attrib:
        if width is None or height is None:
            raise ValueError(f'{svg_file}: Missing `width` and/or `height` in SVG')
        svg_root.attrib['viewBox'] = f'0 0 {length_as_pixels(width)} {length_as_pixels(height)}'
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
