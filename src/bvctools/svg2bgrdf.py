#===============================================================================

import json
from pathlib import Path
import sys
from typing import Optional

#===============================================================================

import lxml.etree as etree

#===============================================================================

from bvctools.bondgraph import BondgraphMaker
from bvctools.svg import SVGBondgraph, SVG_TAG

#===============================================================================

class SVGOutput:
    def __init__(self, attribs: Optional[dict]=None):
        self.__svg = etree.Element(SVG_TAG('svg'))
        if attribs is not None:
            for key, value in attribs.items():
                self.__svg.attrib[key] = value

    def append(self, element: etree.Element):
    #========================================
        self.__svg.append(element)

    def save(self, svg_output: str | Path):
    #======================================
        svg = etree.ElementTree(self.__svg)
        with open(svg_output, 'wb') as fp:
            svg.write(fp, encoding='utf-8', pretty_print=True, xml_declaration=True)

#===============================================================================

def main():
#==========
    # use argparse...
    #
    from bvctools.svg.settings import settings
    settings['add-classes'] = True
    settings['debug-connections'] = True

    svg_bg = SVGBondgraph(sys.argv[1])
    svg_bg.process()

    bg_maker = BondgraphMaker(svg_bg)
    bg_maker.save_bondgraph('bvc-bg.ttl')

    with open('bvc-bg.json', 'w') as fp:
        json.dump(bg_maker.classified_shapes, fp, indent=4)
    with open('properties.json', 'w') as fp:
        json.dump({ 'features': bg_maker.features }, fp, indent=4)
    svg_bg.save_svg('bvc-bg.svg', add_stylesheet=True)

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
#===============================================================================
