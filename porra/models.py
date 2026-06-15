"""Modelos de dominio de la porra del Mundial 2026.

Todos los datos se extraen de ``docs/ADMIN.xlsx`` (ver :mod:`porra.excel_loader`).
Las predicciones se reimplementan en Python porque ``openpyxl`` no recalcula
las fórmulas de Excel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Phase(str, Enum):
    """Fases del torneo. El valor coincide con las etiquetas internas del Excel."""

    GROUPS = "grupos"
    R32 = "1/16"
    R16 = "1/8"
    QF = "1/4"
    SF = "1/2"
    THIRD = "3-4"
    FINAL = "final"

    @property
    def is_knockout(self) -> bool:
        return self is not Phase.GROUPS


# Orden de avance de las eliminatorias (de qué fase salen los clasificados a la siguiente).
KO_ORDER = [Phase.R32, Phase.R16, Phase.QF, Phase.SF, Phase.THIRD, Phase.FINAL]


@dataclass(frozen=True)
class Team:
    """Selección participante. ``rank`` es el ranking FIFA usado como desempate final."""

    num: int
    name: str
    group: str
    rank: int


@dataclass
class Match:
    """Un partido del torneo.

    Para la fase de grupos ``home``/``away`` son nombres reales de selección.
    Para eliminatorias son *placeholders* (``"1E"``, ``"2A"``, ``"3ABCDF"``,
    ``"W74"``, ``"L101"``) que :mod:`porra.tournament` resuelve a selecciones
    reales conforme se introducen resultados.
    """

    number: int                     # nº oficial de partido (1-104, columna AH de WORLDCUP)
    phase: Phase
    matchday: Optional[str] = None  # "J1"/"J2"/"J3" en grupos; None en KO
    group: Optional[str] = None     # "A".."L" en grupos; None en KO
    home: str = ""
    away: str = ""
    date: Optional[datetime] = None
    bonus: int = 1                  # multiplicador de puntos (columna I de ADMIN)
    admin_row: Optional[int] = None # fila de ADMIN con las predicciones de este partido

    @property
    def is_placeholder(self) -> bool:
        """True si los equipos aún son referencias sin resolver (eliminatorias)."""
        return self.phase.is_knockout


@dataclass
class GroupSlotPrediction:
    """Predicción de qué selección queda en una posición de un grupo (1º-4º)."""

    group: str
    position: int  # 1..4
    team: Optional[str] = None


@dataclass
class KnockoutPrediction:
    """Predicción de un partido de eliminatoria.

    Codificación en Excel: ``"<Local>-<Visitante>·<signo>|<local>-<visitante>"``
    (p.ej. ``"Sudáfrica-Suiza·2|1-2"``). El jugador predice **ambas** selecciones
    del cruce y el resultado.
    """

    match_number: int
    raw: str
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    sign: Optional[str] = None
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None

    @property
    def teams(self) -> tuple[Optional[str], Optional[str]]:
        return self.home_team, self.away_team


@dataclass
class Prediction:
    """Predicción de un partido de fase de grupos.

    Codificación en Excel: ``"<signo>|<local>-<visitante>"`` (p.ej. ``"1|3-1"``).
    """

    match_number: int
    raw: str
    sign: Optional[str] = None        # "1" | "X" | "2"
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None

    @property
    def valid(self) -> bool:
        return self.sign is not None and self.home_goals is not None


@dataclass
class Player:
    """Un participante de la porra y todas sus predicciones."""

    name: str
    column: int  # índice de columna en la hoja ADMIN (1-based) de la predicción
    # match_number -> Prediction (grupos)
    group_matches: dict[int, Prediction] = field(default_factory=dict)
    # (grupo, posición) -> nombre de selección
    group_positions: dict[tuple[str, int], Optional[str]] = field(default_factory=dict)
    # fase KO -> lista de selecciones que predice clasificadas a la SIGUIENTE ronda
    qualified: dict[Phase, list[str]] = field(default_factory=dict)
    # match_number -> KnockoutPrediction (eliminatorias)
    ko_matches: dict[int, KnockoutPrediction] = field(default_factory=dict)
    # cuadro de honor: clave -> valor (campeon, subcampeon, tercero, botas, balones)
    honor: dict[str, Optional[str]] = field(default_factory=dict)


@dataclass
class ScoringRules:
    """Tabla de puntos por categoría y fase (columna D de la hoja ADMIN).

    Las claves de ``points`` son tuplas ``(fase, categoria)`` donde categoria ∈
    {"signo", "diferencia", "exacto", "clasificado"}; para posiciones de grupo y
    cuadro de honor se usan claves dedicadas.
    """

    points: dict = field(default_factory=dict)
    # factor de ajuste del crédito parcial por diferencia de goles (D50 = 0.1)
    diff_adjust: float = 0.1


@dataclass
class TournamentData:
    """Todo lo extraído de ADMIN.xlsx, listo para alimentar el motor."""

    teams: list[Team]
    matches: list[Match]
    players: list[Player]
    rules: ScoringRules
    # nº de partido KO -> (ref_local, ref_visitante) con los placeholders crudos
    bracket: dict[int, tuple[str, str]] = field(default_factory=dict)
    # tabla de mejores terceros (hoja Combinaciones3):
    #   combinación de grupos clasificados (p.ej. "EFGHIJKL") ->
    #   {ranura del primero ("1A".."1L"): letra de grupo del tercero ("E"..)}
    thirds_table: dict[str, dict[str, str]] = field(default_factory=dict)

    def team_by_name(self, name: str) -> Optional[Team]:
        return next((t for t in self.teams if t.name == name), None)

    def match_by_number(self, number: int) -> Optional[Match]:
        return next((m for m in self.matches if m.number == number), None)
