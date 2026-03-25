 #===============================================================================

import json
from pathlib import Path
from typing import Optional

#===============================================================================

import lxml.etree as etree

#===============================================================================

from fmtools.bondgraph.labels import bg_annotation
from fmtools.shapes import PropertyDict
from fmtools.svg import SVGDiagram

#===============================================================================


EXCLUDED_FEATURE_NAMES = [
    '2',
    '2F',
    '3',
    '6',
    '36',
    'F'
]

def flatmap_features(features: dict[str, PropertyDict]) -> dict[str, PropertyDict]:
#==================================================================================
    map_features: dict[str, PropertyDict] = {}
    for id, feature in features.items():
        if (name := feature.get('name')) is not None and name not in EXCLUDED_FEATURE_NAMES:
            properties = feature
            properties.update(bg_annotation(str(name)))
            properties.pop('fill', None)
            properties.pop('stroke', None)
            map_features[id] = properties
    return map_features

#===============================================================================

def main():
#==========
    import argparse
    from fmtools.settings import settings

    parser = argparse.ArgumentParser(description='Extract BG information from an SVG and assign IDs to its shapes')
    parser.add_argument('svg_file', metavar='SVG_FILE', help='SVG file to process. The file is updated in place')
    args = parser.parse_args()

    ## To come from command line...
    settings['add-classes'] = True
    settings['debug-connections'] = False ##True

    diagram = SVGDiagram(args.svg_file)
    diagram.process()

    with open('features.json', 'w') as fp:
        json.dump({ 'features': diagram.features }, fp, indent=4)

    properties = flatmap_features(diagram.features)
    with open('properties.json', 'w') as fp:
        json.dump({ 'features': properties }, fp, indent=4)

#    classifier = ShapeClassifier()
#    classifier.classify(diagram, args.bgrdf)

## Get component/name of variables from CellML file(s)
## Reconcile with BG components

      ## This to do classification
    '''
    if args.bgrdf:
        bg_maker = BondgraphMaker(diagram)  ## This to extract BG from classified SVG

        ## File name to come from command line...
        ## If nothing else save these files in the source SVG's directory
        ##
        bg_maker.save_bondgraph('bvc-bg.ttl')

        ## File name to come from command line...
        with open('bvc-bg.json', 'w') as fp:
            json.dump(bg_maker.classified_shapes, fp, indent=4)

        ## Properties to come from classifier and augmented by BG classification??
        ## i.e. we have features even without having BG properties
        with open('properties.json', 'w') as fp:
            json.dump({ 'features': classifier.features }, fp, indent=4)
    '''

    ## Update SVG in place?? Or as a CLI option??
    diagram.save_svg('bvc-bg.svg')

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
#===============================================================================
