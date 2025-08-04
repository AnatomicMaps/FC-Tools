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

import re

#===============================================================================

BG_ELEMENT_PREFIXES = re.compile(r'q_|v_|u_|K_|TF_|FTU: ')

#===============================================================================

BONDGRAPH_NODES = {   ## border (stroke) colour
    'bgf:ResistanceNode': '#00b050',   # 'v'        "v_epi.bl_NKE",  "v_epi.bl_GLUT2"
    'bgf:StorageNode':    '#ff0000',   # 'q', 'u'   "q_epi_H2O"
    # 'K'
    # 'TF'      "TF_NTS_f.br"
    # 'FTU:'    "FTU: Cardiomyocyte"
}

#===============================================================================
#===============================================================================
