"""Lógica del torneo: clasificación de grupos con desempates.

La resolución del cuadro de eliminatorias (mejores terceros, propagación
``W##``/``L##``) se implementa en la Fase 3 sobre esta base.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from .models import Match, Phase, Team, TournamentData
from .results_store import Results


@dataclass
class GroupRow:
    """Fila de la tabla de un grupo."""

    team: Team
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    gf: int = 0
    ga: int = 0

    @property
    def gd(self) -> int:
        return self.gf - self.ga

    @property
    def points(self) -> int:
        return self.won * 3 + self.drawn


def _accumulate(rows: dict[str, GroupRow], home: str, away: str, hg: int, ag: int) -> None:
    rh, ra = rows[home], rows[away]
    rh.played += 1
    ra.played += 1
    rh.gf += hg
    rh.ga += ag
    ra.gf += ag
    ra.ga += hg
    if hg > ag:
        rh.won += 1
        ra.lost += 1
    elif hg < ag:
        ra.won += 1
        rh.lost += 1
    else:
        rh.drawn += 1
        ra.drawn += 1


def _head_to_head(tied: list[GroupRow], group_matches: list[Match], results: Results) -> dict[str, tuple]:
    """Mini-clasificación (puntos, DG, GF) solo con los partidos entre los empatados."""
    names = {r.team.name for r in tied}
    mini = {r.team.name: GroupRow(team=r.team) for r in tied}
    for m in group_matches:
        if m.home in names and m.away in names and results.has(m.number):
            hg, ag = results.goals(m.number)
            _accumulate(mini, m.home, m.away, hg, ag)
    return {n: (row.points, row.gd, row.gf) for n, row in mini.items()}


def compute_group_standings(data: TournamentData, results: Results) -> dict[str, list[GroupRow]]:
    """Devuelve, por grupo, la lista de :class:`GroupRow` ordenada (1º…4º).

    Criterios de desempate (cascada del Excel): puntos → diferencia de goles →
    goles a favor → enfrentamiento directo (puntos/DG/GF entre los empatados) →
    ranking FIFA (``Team.rank``, menor es mejor; desempate determinista final).
    """
    group_matches = [m for m in data.matches if m.phase is Phase.GROUPS]
    standings: dict[str, list[GroupRow]] = {}

    for group in sorted({t.group for t in data.teams}):
        rows = {t.name: GroupRow(team=t) for t in data.teams if t.group == group}
        for m in group_matches:
            if m.group == group and results.has(m.number):
                hg, ag = results.goals(m.number)
                _accumulate(rows, m.home, m.away, hg, ag)

        ranked = _rank_group(list(rows.values()), group_matches, results)
        standings[group] = ranked
    return standings


def _rank_group(rows: list[GroupRow], group_matches: list[Match], results: Results) -> list[GroupRow]:
    # 1ª pasada: puntos, DG, GF
    rows.sort(key=lambda r: (r.points, r.gd, r.gf), reverse=True)

    # resolver empates (mismo puntos/DG/GF) por enfrentamiento directo y ranking FIFA
    result: list[GroupRow] = []
    i = 0
    while i < len(rows):
        j = i + 1
        base = (rows[i].points, rows[i].gd, rows[i].gf)
        while j < len(rows) and (rows[j].points, rows[j].gd, rows[j].gf) == base:
            j += 1
        block = rows[i:j]
        if len(block) > 1:
            h2h = _head_to_head(block, group_matches, results)
            block.sort(key=lambda r: (h2h[r.team.name][0], h2h[r.team.name][1],
                                       h2h[r.team.name][2], -r.team.rank), reverse=True)
        result.extend(block)
        i = j
    return result


def group_positions(data: TournamentData, results: Results) -> dict[tuple[str, int], Team]:
    """{(grupo, posición 1-4): Team} según la clasificación actual."""
    out: dict[tuple[str, int], Team] = {}
    for group, ranked in compute_group_standings(data, results).items():
        for pos, row in enumerate(ranked, start=1):
            out[(group, pos)] = row.team
    return out


def group_phase_complete(data: TournamentData, results: Results) -> bool:
    """True si los 72 partidos de grupos tienen resultado."""
    return all(results.has(m.number) for m in data.matches if m.phase is Phase.GROUPS)


def _complete_groups(data: TournamentData, results: Results) -> set[str]:
    played: dict[str, int] = {}
    for m in data.matches:
        if m.phase is Phase.GROUPS and results.has(m.number):
            played[m.group] = played.get(m.group, 0) + 1
    return {g for g, n in played.items() if n == 6}


def third_place_ranking(standings: dict[str, list[GroupRow]]) -> list[tuple[str, GroupRow]]:
    """Los 12 terceros ordenados de mejor a peor (puntos, DG, GF, ranking FIFA)."""
    thirds = [(g, ranked[2]) for g, ranked in standings.items() if len(ranked) >= 3]
    thirds.sort(key=lambda gr: (gr[1].points, gr[1].gd, gr[1].gf, -gr[1].team.rank), reverse=True)
    return thirds


def qualified_thirds_groups(standings: dict[str, list[GroupRow]]) -> list[str]:
    """Letras de los 8 grupos cuyos terceros se clasifican, ordenadas alfabéticamente."""
    best8 = third_place_ranking(standings)[:8]
    return sorted(g for g, _ in best8)


def clinched_knockout(data: TournamentData, results: Results,
                      standings: dict[str, list[GroupRow]] | None = None) -> set[str]:
    """Nombres de selecciones con la clasificación a dieciseisavos **asegurada**.

    Es una condición *suficiente* (nunca da falsos positivos): incluye a quien
    tiene garantizado el **top-2** de su grupo sea cual sea el resultado de los
    partidos que faltan, y —cuando los 12 grupos están completos— a los **8
    mejores terceros**. No intenta anticipar terceros con grupos incompletos
    (exigiría resolver las 12 tablas a la vez), así que ahí puede quedarse corta,
    nunca pasarse.

    Top-2 garantizado: para cada selección ``T`` se toma su peor caso (pierde todo
    lo que le queda, lo que además da 3 puntos a sus rivales) y se enumeran los
    resultados (1/X/2) de los demás partidos del grupo. Si en **algún** escenario
    dos o más rivales alcanzan los puntos de ``T`` (un empate a puntos podría
    dejarla 3ª por desempate), no está asegurada.
    """
    if standings is None:
        standings = compute_group_standings(data, results)
    group_matches = [m for m in data.matches if m.phase is Phase.GROUPS]
    complete = _complete_groups(data, results)
    clinched: set[str] = set()

    for group, ranked in standings.items():
        names = [r.team.name for r in ranked]
        current = {r.team.name: r.points for r in ranked}
        remaining = [m for m in group_matches
                     if m.group == group and not results.has(m.number)]
        if not remaining:  # grupo completo: los dos primeros están dentro
            clinched.update(names[:2])
            continue

        for team in names:
            own = [m for m in remaining if team in (m.home, m.away)]
            others = [m for m in remaining if team not in (m.home, m.away)]
            base = dict(current)
            for m in own:  # peor caso para 'team': pierde y el rival suma 3
                base[m.away if m.home == team else m.home] += 3

            safe = True
            for combo in product(("home", "draw", "away"), repeat=len(others)):
                pts = dict(base)
                for m, outcome in zip(others, combo):
                    if outcome == "home":
                        pts[m.home] += 3
                    elif outcome == "away":
                        pts[m.away] += 3
                    else:
                        pts[m.home] += 1
                        pts[m.away] += 1
                threats = sum(1 for n in names if n != team and pts[n] >= pts[team])
                if threats >= 2:  # dos rivales podrían quedar por delante -> 3ª o peor
                    safe = False
                    break
            if safe:
                clinched.add(team)

    if len(complete) == 12:  # terceros decididos solo con todos los grupos jugados
        for g in qualified_thirds_groups(standings):
            if len(standings.get(g, [])) >= 3:
                clinched.add(standings[g][2].team.name)

    return clinched


def resolve_bracket(data: TournamentData, results: Results,
                    standings: dict[str, list[GroupRow]] | None = None) -> dict[str, Team]:
    """Resuelve los placeholders del cuadro (``1A``, ``3ABCDF``, ``W74``…) a selecciones.

    Solo rellena lo que los resultados actuales permiten determinar; el resto
    queda sin resolver (no aparece en el dict).
    """
    if standings is None:
        standings = compute_group_standings(data, results)
    complete = _complete_groups(data, results)
    resolved: dict[str, Team] = {}

    # posiciones de grupo (definitivas cuando el grupo está completo)
    for g, ranked in standings.items():
        if g in complete:
            for pos, row in enumerate(ranked, 1):
                resolved[f"{pos}{g}"] = row.team

    # mejores terceros (requiere los 12 grupos completos)
    if len(complete) == 12 and data.thirds_table:
        combo = "".join(qualified_thirds_groups(standings))
        slot_to_group = data.thirds_table.get(combo, {})
        for n, (home, away) in data.bracket.items():
            if n > 88:
                continue
            for token, winner_slot in ((home, away), (away, home)):
                if token.startswith("3") and len(token) > 2:
                    grp = slot_to_group.get(winner_slot)
                    if grp and len(standings.get(grp, [])) >= 3:
                        resolved[token] = standings[grp][2].team

    # propagación W##/L## (recursiva, en orden de partido)
    def resolve_token(token: str) -> Team | None:
        if token in resolved:
            return resolved[token]
        if (token.startswith("W") or token.startswith("L")) and token[1:].isdigit():
            n = int(token[1:])
            side = results.winner_side(n)
            if side is None or n not in data.bracket:
                return None
            h_tok, a_tok = data.bracket[n]
            ht, at = resolve_token(h_tok), resolve_token(a_tok)
            if ht is None or at is None:
                return None
            resolved[f"W{n}"] = ht if side == "home" else at
            resolved[f"L{n}"] = at if side == "home" else ht
            return resolved.get(token)
        return None

    for n in sorted(data.bracket):
        h, a = data.bracket[n]
        resolve_token(h)
        resolve_token(a)
        resolve_token(f"W{n}")
        resolve_token(f"L{n}")
    return resolved


def resolved_match_teams(data: TournamentData, results: Results,
                         standings: dict[str, list[GroupRow]] | None = None,
                         ) -> dict[int, tuple[Team | None, Team | None]]:
    """Para cada partido KO, las selecciones reales (o None si no determinadas)."""
    resolved = resolve_bracket(data, results, standings)
    out: dict[int, tuple[Team | None, Team | None]] = {}
    for n, (home, away) in data.bracket.items():
        out[n] = (resolved.get(home), resolved.get(away))
    return out
