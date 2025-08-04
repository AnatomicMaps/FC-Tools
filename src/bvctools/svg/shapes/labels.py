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

from functools import partial
import re

#===============================================================================

from .bondgraph import BG_ELEMENT_PREFIXES

#===============================================================================

BLOOD_VESSELS = {
    'AA': 'ascending aorta',
    'ac': 'arterial circulation',
    'AV': 'aortic valve',
    'cc': 'capillary circulation',
    'CCA': 'common carotid artery',
    'IVC': 'inferior vena cava',
    'LA': 'left atrium',
    'lv': 'left ventricle',
    'LV': 'left ventricle',
    'MV': 'mitral valve',
    'PV': 'pulmonary valve',
    'RA': 'right atrium',
    'RV': 'right ventricle',
    'SVC': 'superior vena cava',
    'TV': 'tricuspid valve',
    'pulm': 'pulmonary',
    'vc': 'venous circulation',
}

def blood_vessel(element: str, location: str) -> str:
#====================================================
    def make_name(name: str) -> str:
        if (full_name := BLOOD_VESSELS.get(name)) is not None:
            return full_name
        # prepend space to embedded uppercase chars
        # single uppercase chars stay upper, else to lowercase
        return ' '.join([n.lower() if len(n) > 1 else n
                            for n in re.split(r'([A-Z][^A-Z]*)', name) if n != ''])
    description = []
    if element == 'q':
        description.append('amount of blood in')
    elif element == 'u':
        description.append('blood pressure in')
    elif element == 'v':
        description.append('blood flow through')

    if location[1].isupper:
        if location[0] == 'l':
            description.append('left')
            location = location[1:]
        elif location[0] == 'r':
            description.append('right')
            location = location[1:]

    if (name := BLOOD_VESSELS.get(location)) is not None:
        description.append(name)
    elif location[-1] == 'A':
        description.append(make_name(location[:-1]))
        description.append('artery')
    elif location[-1] == 'C':
        description.append(make_name(location[:-1]))
        description.append('capillary bed')
    elif location[-1] == 'V':
        description.append(make_name(location[:-1]))
        description.append('vein')
    else:
        description.append(location)
    return ' '.join(description)

#===============================================================================

LOCATIONS = {
    'ac': 'arterial circulation',
    'b': 'blood',
    'cc': 'capillary circulation',
    'cvs': 'cardiovascular system',
    'epi': 'epithelial cell',
    'gi': 'gastro-intestinal tract',
    'git': 'gastro-intestinal tract',
    'gl': 'glomeruli of the kidney',
    'lv': 'left ventricle',
    'pt': 'proximal tubule of the kidney',
    'vc': 'venous circulation',
}

def get_location(location: str) -> str:
#======================================
    result = []
    locations = location.split('.')
    if len(locations) > 1 and locations[-1] == 'epi':
        locations = reversed(locations)     # Older SVGs have `pt.epi` and not `epi.pt`, etc
    for loc in locations:
        result.append(LOCATIONS.get(loc, loc))
    return ' of '.join(result)

#===============================================================================

# We want 'flow of XXX in/out of YYY'
# Which means we need to know location of other end of connection

SOURCE_SINK = {
    'in': 'in',
    'out': 'out',
    'out1': 'out (1)',
    'out2': 'out (2)',
}

def chemical_species(species: str, element: str, location: str) -> str:
#======================================================================
    description = []
    if element == 'q':
        description.append(f'amount of {species} in')
        description.append(get_location(location))
    elif element == 'u':
        description.append(f'chemical potential of {species} in')
        description.append(get_location(location))
    elif element == 'v':
        description.append(f'flow of {species}')
        if (source_sink := SOURCE_SINK.get(location)) is not None:
            description.append(source_sink)
        else:
            description.append('in')
            description.append(get_location(location))
    else:
        description.append(element)
        description.append(species)
        description.append(get_location(location))
    return ' '.join(description)

#===============================================================================

def osmosis(element: str, location: str) -> str:
    description = []
    if element == 'q':
        description.append(f'amount of water in')
        description.append(get_location(location))
    elif element == 'u':
        description.append(f'osmotic pressure in')
        description.append(get_location(location))
    elif element == 'v':
        description.append('osmotic flow in')
        description.append(get_location(location))
    else:
        description.append(element)
        description.append(get_location(location))
    return ' '.join(description)

#===============================================
#===============================================================================

SPECIFIC_NAMES = {
    'b': blood_vessel,
    'ADP': partial(chemical_species, 'ADP'),
    'ATP': partial(chemical_species, 'ATP'),
    'CO2': partial(chemical_species, 'carbon dioxide'),
    'Glc': partial(chemical_species, 'glucose'),
    'H2O': partial(chemical_species, 'water'),
    'H2O': partial(chemical_species, 'water'),
    'Na+': partial(chemical_species, 'sodium'),
    'NKE': partial(chemical_species, 'sodium through NKE ATPase'),
    'O2': partial(chemical_species, 'oxygen'),
    'osmotic': osmosis,
}

#===============================================================================

# Performed in order
TEXT_SUBSTITUTIONS = {
    '_._': '.',
    'H_2_O': 'H2O',
    'Na_+': 'Na+',
    'CO_2': 'CO2',
    'O_2': 'O2',    # NB. After CO_2
    'k_idney': 'kidney',
}

def make_name(text: list[str]) -> str:
#=====================================
    name = re.sub(r'__+', '_', '_'.join(text))
    for s, r in TEXT_SUBSTITUTIONS.items():
        name = name.replace(s, r)
    return name

def make_label(name: str) -> str:
#================================
    if name.startswith('FTU: '):
        pass
    elif BG_ELEMENT_PREFIXES.match(name):
        parts = name.split('_', 2)
        if (name_function := SPECIFIC_NAMES.get(parts[2])) is not None:
            label = name_function(parts[0], parts[1])
            if len(label):
                label = label[0].upper() + label[1:]
            return label
    return name

def make_labels(name: str) -> str:
#=================================
    return '\n'.join([make_label(n) for n in name.split('_,_')])

#===============================================================================
#===============================================================================
