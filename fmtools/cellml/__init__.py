#===============================================================================
#
#  Flatmap viewer and annotation tools
#
#  Copyright (c) 2020 - 2026  David Brooks
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
from typing import Optional

#===============================================================================

import lxml.etree as etree

#===============================================================================

CELLML_SUFFIX = "http://www.cellml.org/cellml/"

#===============================================================================

CHEMICAL_SPECIES_TO_VAR = {
    'H2O': 'W',
    'Na+': 'Na'
}

#===============================================================================

class CellMLFile:
    def __init__(self, name: str):
        self.__xml = etree.parse(name).getroot()
        start_tag = self.__xml.tag
        if start_tag.startswith(f'{{{CELLML_SUFFIX}') and start_tag.endswith('#}model'):
            self.__ns = start_tag[0:-len('model')]
        else:
            exit(f'{name} is not a valid CellML file...')
        self.__variables: list[str] = []
        self.__components_by_variable = defaultdict(list)
        for component in self.__xml.findall(f'.//{self.__ns}component[@name]'):
            component_name = component.attrib['name']
            for variable in component.findall(f'.//{self.__ns}variable[@name]'):
                var_name = variable.attrib['name']
                self.__variables.append(f'{component_name}/{var_name}')
                self.__components_by_variable[var_name].append(component_name)

    @property
    def variables(self) -> list[str]:
    #================================
        return self.__variables

    def get_variable(self, properties: dict) -> Optional[str]:
    #=========================================================
        if ((symbol := properties.get('symbol')) is not None
         and (location := properties.get('location')) is not None):
            name = f'{symbol}_{location}'
            if (components := self.__components_by_variable.get(name)) is None:
                if (species := properties.get('species')) is not None:
                    species = CHEMICAL_SPECIES_TO_VAR.get(species, species)
                    name = f'{name}_{species}'
                    components = self.__components_by_variable.get(name)
            if components is not None:
                if len(components) > 1:
                    logging.warning('Variable `{name}` in multiple components: {components}')
                return f'{components[0]}/{name}'

# 'main/v_out2_W',
# "name": "v_out2_H2O",

#===============================================================================

if __name__ == '__main__':
#=========================
    import sys
    from pprint import pprint
    if len(sys.argv) < 2:
        exit(f'Usage: {sys.argv[0]} CELLML_FILE')
    c = CellMLFile(sys.argv[1])
    pprint(sorted(c.variables))

#===============================================================================
#===============================================================================
