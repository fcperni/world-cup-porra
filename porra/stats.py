"""KPIs y estadísticas agregadas de la porra.

Dos familias:
* **Predicción** (disponibles siempre): favoritos a campeón/finalista/bota, cómo
  ve la porra a una selección, consenso, etc.
* **Resultado** (cuando hay partidos jugados): selecciones y partidos mejor/peor
  pronosticados.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import KO_ORDER, Phase, TournamentData
from .results_store import Results
from .scoring import score_match


# --------------------------------------------------------------- predicción

def _votes(values) -> Counter:
    return Counter(v for v in values if v)


def champion_votes(data: TournamentData) -> Counter:
    return _votes(p.honor.get("campeon") for p in data.players)


def finalist_votes(data: TournamentData) -> Counter:
    c: Counter = Counter()
    for p in data.players:
        for team in p.qualified.get(Phase.FINAL, []):
            c[team] += 1
    return c


def golden_boot_votes(data: TournamentData) -> Counter:
    return _votes(p.honor.get("bota_oro") for p in data.players)


def qualified_votes(data: TournamentData, phase: Phase) -> Counter:
    c: Counter = Counter()
    for p in data.players:
        for team in p.qualified.get(phase, []):
            c[team] += 1
    return c


def team_group_position_avg(data: TournamentData, team: str) -> float | None:
    """Posición media (1-4) en la que la porra coloca a ``team`` en su grupo."""
    positions = []
    for p in data.players:
        for (_, pos), t in p.group_positions.items():
            if t == team:
                positions.append(pos)
                break
    return sum(positions) / len(positions) if positions else None


def pct_players(data: TournamentData, predicate) -> float:
    if not data.players:
        return 0.0
    return sum(1 for p in data.players if predicate(p)) / len(data.players)


def team_furthest_round_votes(data: TournamentData, team: str) -> dict[str, int]:
    """Reparto de hasta dónde llega ``team`` según cada jugador (ronda más lejana)."""
    order = {ph: i for i, ph in enumerate(KO_ORDER, start=1)}
    out: Counter = Counter()
    for p in data.players:
        best = 0
        for ph in KO_ORDER:
            if team in p.qualified.get(ph, []):
                best = max(best, order[ph])
        if p.honor.get("campeon") == team:
            best = len(order) + 1
        out[best] += 1
    return dict(out)


# --------------------------------------------------------------- resultado

def team_accuracy(data: TournamentData, results: Results) -> dict[str, tuple[float, int]]:
    """Por selección: (puntos medios por pronóstico, nº de pronósticos) en sus
    partidos de grupo ya jugados, agregando a los 19 jugadores."""
    agg: dict[str, list[float]] = {}
    for m in data.matches:
        if m.phase is not Phase.GROUPS or not results.has(m.number):
            continue
        ah, aa = results.goals(m.number)
        asign = results.sign(m.number)
        for p in data.players:
            pred = p.group_matches.get(m.number)
            if not pred or not pred.valid:
                continue
            pts = score_match(data.rules, Phase.GROUPS, m.bonus,
                              pred.sign, pred.home_goals, pred.away_goals, asign, ah, aa)
            for team in (m.home, m.away):
                agg.setdefault(team, [0.0, 0])
                agg[team][0] += pts
                agg[team][1] += 1
    return {t: (tot / n, n) for t, (tot, n) in agg.items() if n}


def match_accuracy(data: TournamentData, results: Results) -> dict[int, float]:
    """Por partido de grupo jugado: puntos medios obtenidos por los jugadores."""
    out: dict[int, float] = {}
    for m in data.matches:
        if m.phase is not Phase.GROUPS or not results.has(m.number):
            continue
        ah, aa = results.goals(m.number)
        asign = results.sign(m.number)
        pts = []
        for p in data.players:
            pred = p.group_matches.get(m.number)
            if pred and pred.valid:
                pts.append(score_match(data.rules, Phase.GROUPS, m.bonus,
                                       pred.sign, pred.home_goals, pred.away_goals, asign, ah, aa))
        if pts:
            out[m.number] = sum(pts) / len(pts)
    return out


def group_matches_played(data: TournamentData, results: Results) -> int:
    return sum(1 for m in data.matches if m.phase is Phase.GROUPS and results.has(m.number))


# --------------------------------------------------------------- curiosidades

SIGNS = ("1", "X", "2")  # local gana, empate, visitante gana


@dataclass
class MatchSplit:
    """Reparto de los pronósticos 1X2 de un partido de grupos entre los jugadores.

    * ``voters``: signo ("1"/"X"/"2") -> lista de nombres que lo eligieron, en el
      orden original de los jugadores.
    * ``counts``: signo -> nº de votos.
    * ``top_score``: ``((local, visitante), nº)`` del marcador exacto más repetido,
      o ``None`` si nadie pronosticó.
    * ``total``: nº de pronósticos válidos.
    """

    match_number: int
    voters: dict[str, list[str]]
    counts: dict[str, int]
    top_score: tuple[tuple[int, int], int] | None
    total: int

    @property
    def majority_sign(self) -> str | None:
        """Signo más votado (desempate por el orden 1, X, 2). None si no hay votos."""
        if not self.total:
            return None
        return max(SIGNS, key=lambda s: (self.counts[s], -SIGNS.index(s)))

    @property
    def is_unanimous(self) -> bool:
        return self.total > 0 and self.counts[self.majority_sign] == self.total

    @property
    def dissenters(self) -> int:
        """Cuántos jugadores se apartan del signo mayoritario."""
        return self.total - self.counts[self.majority_sign] if self.total else 0


def match_sign_splits(data: TournamentData) -> dict[int, MatchSplit]:
    """Reparto de pronósticos 1X2 por partido de **fase de grupos**.

    Solo grupos: en eliminatorias el jugador pronostica el *cruce* (qué dos
    selecciones se enfrentan), no un 1X2 sobre equipos fijos, así que el consenso
    no es comparable.
    """
    out: dict[int, MatchSplit] = {}
    for m in data.matches:
        if m.phase is not Phase.GROUPS:
            continue
        voters: dict[str, list[str]] = {s: [] for s in SIGNS}
        scores: Counter = Counter()
        for p in data.players:
            pred = p.group_matches.get(m.number)
            if not pred or not pred.valid or pred.sign not in voters:
                continue
            voters[pred.sign].append(p.name)
            scores[(pred.home_goals, pred.away_goals)] += 1
        counts = {s: len(v) for s, v in voters.items()}
        total = sum(counts.values())
        top = scores.most_common(1)[0] if scores else None
        out[m.number] = MatchSplit(m.number, voters, counts, top, total)
    return out
