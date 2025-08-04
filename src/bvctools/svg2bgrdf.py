#===============================================================================

import json
from pathlib import Path
from typing import Optional

#===============================================================================

import lxml.etree as etree

#===============================================================================

from svg import SVGBondgraph, ShapeClassifier, SVG_TAG

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
#===============================================================================

def main():
#==========
    from svg.settings import settings
    settings['add-classes'] = True
    settings['debug-connections'] = True

    import sys

    svg_bg = SVGBondgraph(sys.argv[1])
    svg_bg.process()

    classifier = ShapeClassifier(svg_bg)
    classifier.classify()

    classifier.save('bvc-bg.json')
    with open('properties.json', 'w') as fp:
        json.dump({
            'features': classifier.features
            }, fp, indent=4)
    svg_bg.save_svg('bvc-bg.svg', add_stylesheet=True)

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
#===============================================================================
