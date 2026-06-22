"""Tests de la lógica del torneo: clasificación, desempates y cuadro."""

import pytest

from porra.excel_loader import load_tournament
from porra.models import Phase
from porra.results_store import Results
from porra.tournament import (
    clinched_knockout,
    compute_group_standings,
    qualified_thirds_groups,
    resolve_bracket,
    resolved_match_teams,
)


@pytest.fixture(scope="module")
def data():
    return load_tournament()


def _fill_groups(data, results, draw_every=9):
    """Rellena los 72 partidos de grupos: gana el de mejor ranking FIFA."""
    rank = {t.name: t.rank for t in data.teams}
    for m in data.matches:
        if m.phase is Phase.GROUPS:
            if m.number % draw_every == 0:
                results.set_match(m.number, 1, 1)
            elif rank[m.home] < rank[m.away]:
                results.set_match(m.number, 2, 0)
            else:
                results.set_match(m.number, 0, 1)


def test_group_standings_points_and_order(data):
    res = Results()
    _fill_groups(data, res)
    st = compute_group_standings(data, res)
    assert set(st) == set("ABCDEFGHIJKL")
    for group, ranked in st.items():
        assert len(ranked) == 4
        # ordenado por (puntos, DG, GF) de forma no creciente
        keys = [(r.points, r.gd, r.gf) for r in ranked]
        assert keys == sorted(keys, reverse=True)
        # cada equipo jugó 3 partidos
        assert all(r.played == 3 for r in ranked)


def test_tiebreaker_by_fifa_rank(data):
    """Dos equipos idénticos en pts/DG/GF se ordenan por ranking FIFA (menor mejor)."""
    res = Results()
    _fill_groups(data, res)
    st = compute_group_standings(data, res)
    for ranked in st.values():
        for a, b in zip(ranked, ranked[1:]):
            if (a.points, a.gd, a.gf) == (b.points, b.gd, b.gf):
                # sin enfrentamiento directo decisivo, el mejor ranking va antes
                assert a.team.rank <= b.team.rank


def test_best_eight_thirds(data):
    res = Results()
    _fill_groups(data, res)
    st = compute_group_standings(data, res)
    groups = qualified_thirds_groups(st)
    assert len(groups) == 8
    assert all(g in "ABCDEFGHIJKL" for g in groups)
    assert groups == sorted(groups)


def test_full_bracket_resolves(data):
    res = Results()
    _fill_groups(data, res)
    st = compute_group_standings(data, res)
    # R32 totalmente resuelto al acabar los grupos
    teams = resolved_match_teams(data, res, st)
    for n in range(73, 89):
        h, a = teams[n]
        assert h is not None and a is not None, f"R32 m{n} sin resolver"
    # 32 selecciones distintas en R32
    r32_teams = {teams[n][0].name for n in range(73, 89)} | {teams[n][1].name for n in range(73, 89)}
    assert len(r32_teams) == 32


def test_bracket_propagates_to_final(data):
    res = Results()
    _fill_groups(data, res)
    st = compute_group_standings(data, res)
    # jugar todas las eliminatorias (gana el local)
    for _ in range(6):
        teams = resolved_match_teams(data, res, st)
        for n in range(73, 105):
            if not res.has(n) and teams[n][0] and teams[n][1]:
                res.set_match(n, 2, 1)
    teams = resolved_match_teams(data, res, st)
    assert teams[104][0] and teams[104][1]  # final con dos selecciones
    assert teams[103][0] and teams[103][1]  # 3er puesto


def test_third_slot_comes_from_listed_group(data):
    """El tercero asignado a un cruce pertenece a uno de los grupos del código."""
    res = Results()
    _fill_groups(data, res)
    st = compute_group_standings(data, res)
    resolved = resolve_bracket(data, res, st)
    for n, (home, away) in data.bracket.items():
        for token in (home, away):
            if token.startswith("3") and len(token) > 2 and token in resolved:
                allowed = set(token[1:])  # letras del código, p.ej. {A,B,C,D,F}
                assert resolved[token].group in allowed


def test_clinched_empty_without_results(data):
    assert clinched_knockout(data, Results()) == set()


def test_clinched_full_groups_are_the_32(data):
    res = Results()
    _fill_groups(data, res)
    st = compute_group_standings(data, res)
    expected = {r.team.name for ranked in st.values() for r in ranked[:2]}
    expected |= {st[g][2].team.name for g in qualified_thirds_groups(st)}
    clinched = clinched_knockout(data, res, st)
    assert len(expected) == 32
    assert clinched == expected


def test_clinched_top2_when_two_rivals_cannot_both_catch(data):
    """México gana J1 y J2 (6 pts) y, en J3, ningún rival puede alcanzarlo."""
    res = Results()
    res.set_match(1, 2, 0)   # México 2-0 Sudáfrica
    res.set_match(28, 2, 0)  # México 2-0 Corea del Sur  -> México 6 pts
    res.set_match(2, 0, 0)   # Corea 0-0 Chequia
    res.set_match(25, 0, 0)  # Chequia 0-0 Sudáfrica
    # restan #53 Chequia-México y #54 Sudáfrica-Corea; nadie llega a 6
    clinched = clinched_knockout(data, res)
    assert clinched == {"México"}


def test_not_clinched_when_two_rivals_can_both_catch(data):
    """Mismo líder a 6, pero dos rivales pueden llegar a 6 en J3: no asegurado."""
    res = Results()
    res.set_match(1, 2, 0)   # México 2-0 Sudáfrica
    res.set_match(28, 2, 0)  # México 2-0 Corea del Sur  -> México 6 pts
    res.set_match(2, 1, 0)   # Corea 1-0 Chequia  -> Corea 3
    res.set_match(25, 1, 0)  # Chequia 1-0 Sudáfrica -> Chequia 3
    # #53 Chequia-México y #54 Sudáfrica-Corea: Corea y Chequia podrían llegar a 6
    assert clinched_knockout(data, res) == set()


def test_ko_winner_by_penalties(data):
    res = Results()
    res.set_match(73, 1, 1)
    assert res.winner_side(73) is None  # empate sin penaltis
    res.ko_winners[73] = "away"
    assert res.winner_side(73) == "away"
