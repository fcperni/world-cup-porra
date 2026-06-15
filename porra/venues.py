"""Sedes (ciudad + estadio) de cada partido del Mundial 2026.

El Excel ``ADMIN.xlsx`` **no** contiene la sede de los partidos, así que la
mantenemos aquí como dato estático: el calendario oficial de la FIFA asigna a
cada **número de partido** (1-104) un estadio fijo, con independencia de qué
selecciones acaben jugándolo. La numeración de la porra coincide con la oficial
de la FIFA (verificado: p.ej. el grupo K son los partidos 23, 24, 47, 48, 71 y
72, igual que en el calendario oficial; el 1 es la inauguración y el 104 la final).

Nombres de estadio en su forma comúnmente conocida (con patrocinador) y ciudad
en español. :func:`porra.excel_loader.load_tournament` rellena ``Match.city`` y
``Match.stadium`` a partir de esta tabla.
"""

from __future__ import annotations

from typing import Optional

# nº de partido (1-104) -> (ciudad, estadio)
MATCH_VENUES: dict[int, tuple[str, str]] = {
    1: ("Ciudad de México", "Estadio Azteca"),
    2: ("Guadalajara", "Estadio Akron"),
    3: ("Toronto", "BMO Field"),
    4: ("Los Ángeles", "SoFi Stadium"),
    5: ("Boston", "Gillette Stadium"),
    6: ("Vancouver", "BC Place"),
    7: ("Nueva York/Nueva Jersey", "MetLife Stadium"),
    8: ("San Francisco", "Levi's Stadium"),
    9: ("Filadelfia", "Lincoln Financial Field"),
    10: ("Houston", "NRG Stadium"),
    11: ("Dallas", "AT&T Stadium"),
    12: ("Monterrey", "Estadio BBVA"),
    13: ("Miami", "Hard Rock Stadium"),
    14: ("Atlanta", "Mercedes-Benz Stadium"),
    15: ("Los Ángeles", "SoFi Stadium"),
    16: ("Seattle", "Lumen Field"),
    17: ("Nueva York/Nueva Jersey", "MetLife Stadium"),
    18: ("Boston", "Gillette Stadium"),
    19: ("Kansas City", "Arrowhead Stadium"),
    20: ("San Francisco", "Levi's Stadium"),
    21: ("Toronto", "BMO Field"),
    22: ("Dallas", "AT&T Stadium"),
    23: ("Houston", "NRG Stadium"),
    24: ("Ciudad de México", "Estadio Azteca"),
    25: ("Atlanta", "Mercedes-Benz Stadium"),
    26: ("Los Ángeles", "SoFi Stadium"),
    27: ("Vancouver", "BC Place"),
    28: ("Guadalajara", "Estadio Akron"),
    29: ("Filadelfia", "Lincoln Financial Field"),
    30: ("Boston", "Gillette Stadium"),
    31: ("San Francisco", "Levi's Stadium"),
    32: ("Seattle", "Lumen Field"),
    33: ("Toronto", "BMO Field"),
    34: ("Kansas City", "Arrowhead Stadium"),
    35: ("Houston", "NRG Stadium"),
    36: ("Monterrey", "Estadio BBVA"),
    37: ("Miami", "Hard Rock Stadium"),
    38: ("Atlanta", "Mercedes-Benz Stadium"),
    39: ("Los Ángeles", "SoFi Stadium"),
    40: ("Vancouver", "BC Place"),
    41: ("Nueva York/Nueva Jersey", "MetLife Stadium"),
    42: ("Filadelfia", "Lincoln Financial Field"),
    43: ("Dallas", "AT&T Stadium"),
    44: ("San Francisco", "Levi's Stadium"),
    45: ("Boston", "Gillette Stadium"),
    46: ("Toronto", "BMO Field"),
    47: ("Houston", "NRG Stadium"),
    48: ("Guadalajara", "Estadio Akron"),
    49: ("Miami", "Hard Rock Stadium"),
    50: ("Atlanta", "Mercedes-Benz Stadium"),
    51: ("Vancouver", "BC Place"),
    52: ("Seattle", "Lumen Field"),
    53: ("Ciudad de México", "Estadio Azteca"),
    54: ("Monterrey", "Estadio BBVA"),
    55: ("Filadelfia", "Lincoln Financial Field"),
    56: ("Nueva York/Nueva Jersey", "MetLife Stadium"),
    57: ("Dallas", "AT&T Stadium"),
    58: ("Kansas City", "Arrowhead Stadium"),
    59: ("Los Ángeles", "SoFi Stadium"),
    60: ("San Francisco", "Levi's Stadium"),
    61: ("Boston", "Gillette Stadium"),
    62: ("Toronto", "BMO Field"),
    63: ("Seattle", "Lumen Field"),
    64: ("Vancouver", "BC Place"),
    65: ("Houston", "NRG Stadium"),
    66: ("Guadalajara", "Estadio Akron"),
    67: ("Nueva York/Nueva Jersey", "MetLife Stadium"),
    68: ("Filadelfia", "Lincoln Financial Field"),
    69: ("Kansas City", "Arrowhead Stadium"),
    70: ("Dallas", "AT&T Stadium"),
    71: ("Miami", "Hard Rock Stadium"),
    72: ("Atlanta", "Mercedes-Benz Stadium"),
    73: ("Los Ángeles", "SoFi Stadium"),
    74: ("Boston", "Gillette Stadium"),
    75: ("Monterrey", "Estadio BBVA"),
    76: ("Houston", "NRG Stadium"),
    77: ("Nueva York/Nueva Jersey", "MetLife Stadium"),
    78: ("Dallas", "AT&T Stadium"),
    79: ("Ciudad de México", "Estadio Azteca"),
    80: ("Atlanta", "Mercedes-Benz Stadium"),
    81: ("San Francisco", "Levi's Stadium"),
    82: ("Seattle", "Lumen Field"),
    83: ("Toronto", "BMO Field"),
    84: ("Los Ángeles", "SoFi Stadium"),
    85: ("Vancouver", "BC Place"),
    86: ("Miami", "Hard Rock Stadium"),
    87: ("Kansas City", "Arrowhead Stadium"),
    88: ("Dallas", "AT&T Stadium"),
    89: ("Filadelfia", "Lincoln Financial Field"),
    90: ("Houston", "NRG Stadium"),
    91: ("Nueva York/Nueva Jersey", "MetLife Stadium"),
    92: ("Ciudad de México", "Estadio Azteca"),
    93: ("Dallas", "AT&T Stadium"),
    94: ("Seattle", "Lumen Field"),
    95: ("Atlanta", "Mercedes-Benz Stadium"),
    96: ("Vancouver", "BC Place"),
    97: ("Boston", "Gillette Stadium"),
    98: ("Los Ángeles", "SoFi Stadium"),
    99: ("Miami", "Hard Rock Stadium"),
    100: ("Kansas City", "Arrowhead Stadium"),
    101: ("Dallas", "AT&T Stadium"),
    102: ("Atlanta", "Mercedes-Benz Stadium"),
    103: ("Miami", "Hard Rock Stadium"),
    104: ("Nueva York/Nueva Jersey", "MetLife Stadium"),
}


def venue_for(match_number: int) -> tuple[Optional[str], Optional[str]]:
    """(ciudad, estadio) del partido, o (None, None) si no se conoce."""
    return MATCH_VENUES.get(match_number, (None, None))
