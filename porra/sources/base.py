"""Interfaz de fuentes de resultados y emparejamiento con el calendario.

Una fuente (ESPN, Wikipedia) devuelve una lista de :class:`ScrapedGame` con los
nombres de los equipos tal como los publica. :func:`map_to_matches` los empareja
con los partidos del torneo (por la **pareja** de selecciones, normalizando los
nombres) y produce ``{nº de partido: MatchResult}``.
"""

from __future__ import annotations

import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..models import Phase, TournamentData
from ..results_store import Results


@dataclass
class ScrapedGame:
    """Un partido tal como lo publica una fuente externa."""

    home: str
    away: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    finished: bool = False
    when: Optional[date] = None
    # ganador en KO si lo informa la fuente ("home"/"away"); útil en empates+penaltis
    winner: Optional[str] = None


@dataclass
class MatchResult:
    """Resultado ya emparejado con un partido del torneo."""

    number: int
    home_goals: int
    away_goals: int
    winner: Optional[str] = None  # "home"/"away" en KO con empate


class ResultsSource(ABC):
    """Fuente de resultados enchufable."""

    name: str = "fuente"

    @abstractmethod
    def fetch(self, data: TournamentData) -> list[ScrapedGame]:
        """Devuelve los partidos con resultado conocidos por la fuente."""


# --------------------------------------------------------------------------- nombres

def _norm(s: str) -> str:
    """Normaliza un nombre: sin acentos, minúsculas, solo alfanuméricos."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return "".join(ch for ch in s.lower() if ch.isalnum())


# Alias (inglés y variantes) -> nombre canónico en español del Excel.
_ALIASES = {
    "southkorea": "Corea del Sur", "korearepublic": "Corea del Sur", "korea": "Corea del Sur",
    "czechia": "República Checa", "czechrepublic": "República Checa",
    "ivorycoast": "Costa de Marfil", "cotedivoire": "Costa de Marfil",
    "netherlands": "Países Bajos", "holland": "Países Bajos",
    "curacao": "Curazao",
    "capeverde": "Cabo Verde", "caboverde": "Cabo Verde",
    "saudiarabia": "Arabia Saudita",
    "drcongo": "RD Congo", "congodr": "RD Congo", "democraticrepublicofthecongo": "RD Congo",
    "turkiye": "Turquía", "turkey": "Turquía",
    "qatar": "Catar",
    "uzbekistan": "Uzbekistán",
    "germany": "Alemania", "spain": "España", "france": "Francia", "england": "Inglaterra",
    "brazil": "Brasil", "argentina": "Argentina", "portugal": "Portugal", "belgium": "Bélgica",
    "switzerland": "Suiza", "croatia": "Croacia", "morocco": "Marruecos", "japan": "Japón",
    "mexico": "México", "unitedstates": "Estados Unidos", "usa": "Estados Unidos", "us": "Estados Unidos",
    "canada": "Canadá", "australia": "Australia", "ecuador": "Ecuador", "uruguay": "Uruguay",
    "colombia": "Colombia", "paraguay": "Paraguay", "panama": "Panamá", "haiti": "Haití",
    "scotland": "Escocia", "norway": "Noruega", "senegal": "Senegal", "iran": "Irán",
    "iraq": "Irak", "egypt": "Egipto", "ghana": "Ghana", "tunisia": "Túnez", "sweden": "Suecia",
    "newzealand": "Nueva Zelanda", "southafrica": "Sudáfrica", "austria": "Austria",
    "algeria": "Argelia", "jordan": "Jordania", "bosniaandherzegovina": "Bosnia y Herzegovina",
    "bosniaherzegovina": "Bosnia y Herzegovina", "bosnia": "Bosnia y Herzegovina",
}


def build_name_resolver(data: TournamentData):
    """Devuelve una función nombre_externo -> nombre del Excel (o None)."""
    canonical = {_norm(t.name): t.name for t in data.teams}
    alias_norm = {_norm(k): v for k, v in _ALIASES.items()}

    def resolve(name: str) -> Optional[str]:
        n = _norm(name)
        if n in canonical:
            return canonical[n]
        if n in alias_norm:
            return alias_norm[n]
        return None

    return resolve


# --------------------------------------------------------------------------- emparejado

def map_to_matches(data: TournamentData, results: Results,
                   games: list[ScrapedGame],
                   resolved_teams: Optional[dict] = None) -> dict[int, MatchResult]:
    """Empareja partidos scrapeados con los del torneo por la pareja de selecciones.

    Los partidos de grupos se emparejan por su pareja fija; los de eliminatorias,
    por las selecciones ya resueltas (requiere haber introducido rondas previas).
    """
    if resolved_teams is None:
        from ..tournament import resolved_match_teams
        resolved_teams = resolved_match_teams(data, results)
    resolve = build_name_resolver(data)

    # índice pareja(frozenset) -> (nº, nombre_local) para orientar local/visitante
    pair_index: dict[frozenset, tuple[int, str]] = {}
    for m in data.matches:
        if m.phase is Phase.GROUPS:
            home, away = m.home, m.away
        else:
            ht, at = resolved_teams.get(m.number, (None, None))
            if not ht or not at:
                continue
            home, away = ht.name, at.name
        pair_index[frozenset((home, away))] = (m.number, home)

    out: dict[int, MatchResult] = {}
    for g in games:
        if not g.finished or g.home_goals is None or g.away_goals is None:
            continue
        h, a = resolve(g.home), resolve(g.away)
        if not h or not a or h == a:
            continue
        entry = pair_index.get(frozenset((h, a)))
        if not entry:
            continue
        number, canonical_home = entry
        # orientar el marcador al orden local/visitante del calendario
        if h == canonical_home:
            hg, ag = g.home_goals, g.away_goals
            winner = g.winner
        else:
            hg, ag = g.away_goals, g.home_goals
            winner = {"home": "away", "away": "home"}.get(g.winner) if g.winner else None
        out[number] = MatchResult(number=number, home_goals=hg, away_goals=ag, winner=winner)
    return out


def sync_results(data: TournamentData, results: Results,
                 sources: list[ResultsSource],
                 resolved_teams: Optional[dict] = None) -> dict[int, MatchResult]:
    """Combina las fuentes en orden de prioridad (la 1ª gana ante conflicto).

    Devuelve los resultados propuestos; **no** modifica ``results`` (el usuario
    confirma en la UI).
    """
    proposals: dict[int, MatchResult] = {}
    for source in sources:
        try:
            games = source.fetch(data)
        except Exception:  # noqa: BLE001 — una fuente caída no debe romper la sincronización
            continue
        mapped = map_to_matches(data, results, games, resolved_teams)
        for num, mr in mapped.items():
            proposals.setdefault(num, mr)  # la fuente de mayor prioridad ya colocada
    return proposals
