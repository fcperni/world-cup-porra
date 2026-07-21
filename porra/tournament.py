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

    Criterios de desempate (**reglas FIFA 2026**, Art. 13 — el enfrentamiento
    directo va ahora ANTES que la diferencia de goles general): puntos →
    enfrentamiento directo (puntos → DG → GF entre las empatadas) → DG general →
    GF general → *fair play* (sin datos, se omite) → ranking FIFA (``Team.rank``,
    menor es mejor; desempate determinista final).
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


def _overall_order(block: list[GroupRow]) -> list[GroupRow]:
    """Criterios generales (5-7): DG general → GF general → ranking FIFA."""
    block.sort(key=lambda r: (r.gd, r.gf, -r.team.rank), reverse=True)
    return block


def _break_tie(block: list[GroupRow], group_matches: list[Match], results: Results) -> list[GroupRow]:
    """Ordena un bloque empatado a puntos según las reglas FIFA 2026.

    Aplica primero el enfrentamiento directo (puntos → DG → GF entre las
    empatadas); si separa el bloque en subgrupos, **reaplica** el directo a cada
    subgrupo (la mini-tabla cambia al quitar equipos); lo que el directo no
    desempata pasa a los criterios generales (DG/GF general, ranking).
    """
    if len(block) == 1:
        return block
    h2h = _head_to_head(block, group_matches, results)
    block.sort(key=lambda r: h2h[r.team.name], reverse=True)

    subgroups: list[list[GroupRow]] = []
    i = 0
    while i < len(block):
        j = i + 1
        while j < len(block) and h2h[block[j].team.name] == h2h[block[i].team.name]:
            j += 1
        subgroups.append(block[i:j])
        i = j

    if len(subgroups) == 1:  # el directo no separó a nadie -> criterios generales
        return _overall_order(block)

    result: list[GroupRow] = []
    for sub in subgroups:  # cada subgrupo es estrictamente menor -> recursión finita
        result.extend(_break_tie(sub, group_matches, results) if len(sub) > 1 else sub)
    return result


def _rank_group(rows: list[GroupRow], group_matches: list[Match], results: Results) -> list[GroupRow]:
    rows.sort(key=lambda r: r.points, reverse=True)  # 1er criterio: puntos
    result: list[GroupRow] = []
    i = 0
    while i < len(rows):
        j = i + 1
        while j < len(rows) and rows[j].points == rows[i].points:
            j += 1
        block = rows[i:j]
        result.extend(_break_tie(block, group_matches, results) if len(block) > 1 else block)
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
    per_group = data.format.matches_per_group
    played: dict[str, int] = {}
    for m in data.matches:
        if m.phase is Phase.GROUPS and results.has(m.number):
            played[m.group] = played.get(m.group, 0) + 1
    return {g for g, n in played.items() if n == per_group}


def third_place_ranking(standings: dict[str, list[GroupRow]]) -> list[tuple[str, GroupRow]]:
    """Los terceros de cada grupo ordenados de mejor a peor (puntos, DG, GF, ranking FIFA)."""
    thirds = [(g, ranked[2]) for g, ranked in standings.items() if len(ranked) >= 3]
    thirds.sort(key=lambda gr: (gr[1].points, gr[1].gd, gr[1].gf, -gr[1].team.rank), reverse=True)
    return thirds


def qualified_thirds_groups(standings: dict[str, list[GroupRow]], n_thirds: int = 8) -> list[str]:
    """Letras de los ``n_thirds`` grupos cuyos terceros se clasifican, ordenadas alfabéticamente.

    El default 8 es el del Mundial; el motor pasa ``data.format.thirds_qualify``.
    """
    best = third_place_ranking(standings)[:n_thirds]
    return sorted(g for g, _ in best)


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

    if len(complete) == data.format.n_groups:  # terceros decididos solo con todos los grupos jugados
        for g in qualified_thirds_groups(standings, data.format.thirds_qualify):
            if len(standings.get(g, [])) >= 3:
                clinched.add(standings[g][2].team.name)

    return clinched


def locked_group_positions(data: TournamentData, results: Results,
                           standings: dict[str, list[GroupRow]] | None = None,
                           ) -> dict[tuple[str, int], Team]:
    """``{(grupo, posición 1-4): Team}`` solo para las posiciones ya **aseguradas**.

    Una posición está asegurada cuando la selección la ocupa en **cualquier**
    combinación de resultados (1/X/2) de los partidos que faltan del grupo. La
    decisión usa solo los criterios que no dependen de los goles que aún se pueden
    marcar: **puntos** y **enfrentamiento directo a puntos** (reglas FIFA 2026,
    donde el directo va antes que la DG). Lo que quedaría por desempatar por DG/GF
    se considera abierto —los goles restantes podrían cambiarlo—, así que la
    función puede quedarse corta, nunca pasarse (sin falsos positivos).
    """
    if standings is None:
        standings = compute_group_standings(data, results)
    complete = _complete_groups(data, results)
    locked: dict[tuple[str, int], Team] = {}

    for group, ranked in standings.items():
        team_by_name = {r.team.name: r.team for r in ranked}
        names = list(team_by_name)
        if group in complete:  # grupo cerrado: las cuatro posiciones son definitivas
            for pos, r in enumerate(ranked, 1):
                locked[(group, pos)] = r.team
            continue

        grp_matches = [m for m in data.matches if m.phase is Phase.GROUPS and m.group == group]
        played = [m for m in grp_matches if results.has(m.number)]
        remaining = [m for m in grp_matches if not results.has(m.number)]
        base_pts = {r.team.name: r.points for r in ranked}

        # rango de posición (mejor, peor) de cada selección sobre todos los escenarios
        best = {n: len(names) for n in names}
        worst = {n: 1 for n in names}
        for combo in product(("home", "draw", "away"), repeat=len(remaining)):
            outcome: dict[int, str] = {}
            for m in played:
                hg, ag = results.goals(m.number)
                outcome[m.number] = "home" if hg > ag else "away" if hg < ag else "draw"
            pts = dict(base_pts)
            for m, o in zip(remaining, combo):
                outcome[m.number] = o
                if o == "home":
                    pts[m.home] += 3
                elif o == "away":
                    pts[m.away] += 3
                else:
                    pts[m.home] += 1
                    pts[m.away] += 1

            for team in names:
                block = [n for n in names if pts[n] == pts[team]]  # empatadas a puntos (incl. team)
                above = sum(1 for n in names if pts[n] > pts[team])
                if len(block) > 1:  # desempate a puntos en el enfrentamiento directo
                    h2h = {n: 0 for n in block}
                    for m in grp_matches:
                        if m.home in block and m.away in block and m.number in outcome:
                            o = outcome[m.number]
                            if o == "home":
                                h2h[m.home] += 3
                            elif o == "away":
                                h2h[m.away] += 3
                            else:
                                h2h[m.home] += 1
                                h2h[m.away] += 1
                    above += sum(1 for n in block if n != team and h2h[n] > h2h[team])
                    # empatadas también en el directo a puntos: orden abierto (depende de la DG)
                    undecided = sum(1 for n in block if h2h[n] == h2h[team])
                else:
                    undecided = 1
                best[team] = min(best[team], above + 1)
                worst[team] = max(worst[team], above + undecided)

        for team in names:
            if best[team] == worst[team]:
                locked[(group, best[team])] = team_by_name[team]

    return locked


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

    # posiciones de grupo ya aseguradas (con el grupo cerrado, las cuatro; antes,
    # las que sean matemáticamente definitivas — p.ej. el 1º si ganó el directo)
    for (g, pos), team in locked_group_positions(data, results, standings).items():
        resolved[f"{pos}{g}"] = team

    # mejores terceros (requiere todos los grupos completos); solo alimentan la
    # primera ronda eliminatoria del formato (R32 en el Mundial, R16 en la Euro)
    if len(complete) == data.format.n_groups and data.thirds_table:
        combo = "".join(qualified_thirds_groups(standings, data.format.thirds_qualify))
        slot_to_group = data.thirds_table.get(combo, {})
        for n, (home, away) in data.bracket.items():
            if data.format.phase_for_number(n) is not data.format.first_ko_phase:
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


def eliminated_teams(data: TournamentData, results: Results,
                     standings: dict[str, list[GroupRow]] | None = None) -> set[str]:
    """Nombres de selecciones ya **eliminadas** del torneo.

    Condición *suficiente* (sin falsos positivos): una selección eliminada no
    volverá a aparecer en ninguna ronda a la que todavía no haya llegado, así que
    sus apariciones en el cuadro de un jugador para rondas posteriores son fallos
    seguros. Incluye:

    * El **perdedor** de cualquier cruce KO con ganador ya decidido (el perdedor
      de semifinal juega el 3er/4º puesto, pero ya no puede llegar a la final).
    * El **4º** de un grupo cerrado (nunca clasifica).
    * El **3º** de un grupo cerrado cuando los 12 grupos están completos y no
      entra entre los 8 mejores terceros (antes su suerte aún no está decidida).
    """
    if standings is None:
        standings = compute_group_standings(data, results)
    out: set[str] = set()

    resolved = resolved_match_teams(data, results, standings)
    for n, (ht, at) in resolved.items():
        side = results.winner_side(n)
        if side and ht and at:
            out.add(at.name if side == "home" else ht.name)

    complete = _complete_groups(data, results)
    all_done = len(complete) == data.format.n_groups
    best_thirds = (set(qualified_thirds_groups(standings, data.format.thirds_qualify))
                   if all_done else set())
    for g in complete:
        ranked = standings.get(g, [])
        if len(ranked) >= 4:
            out.add(ranked[3].team.name)  # 4º: nunca clasifica
        if all_done and len(ranked) >= 3 and g not in best_thirds:
            out.add(ranked[2].team.name)  # 3º que no entra entre los mejores
    return out
