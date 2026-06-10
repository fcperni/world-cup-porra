"""Tests de las estadísticas agregadas (porra.stats)."""

import pytest

from porra import stats
from porra.excel_loader import load_tournament
from porra.models import Phase
from porra.results_store import Results


@pytest.fixture(scope="module")
def data():
    return load_tournament()


def test_champion_votes(data):
    c = stats.champion_votes(data)
    assert sum(c.values()) <= len(data.players)
    assert all(v >= 1 for v in c.values())


def test_finalist_votes_two_per_player(data):
    c = stats.finalist_votes(data)
    # cada jugador vota 2 finalistas
    assert sum(c.values()) == 2 * len(data.players)


def test_spain_group_position_avg_in_range(data):
    avg = stats.team_group_position_avg(data, "España")
    assert avg is None or 1.0 <= avg <= 4.0


def test_team_accuracy_with_results(data):
    res = Results()
    # un partido de grupo jugado
    m = next(m for m in data.matches if m.phase is Phase.GROUPS)
    res.set_match(m.number, 2, 0)
    acc = stats.team_accuracy(data, res)
    assert m.home in acc and m.away in acc
    avg, n = acc[m.home]
    assert n == len(data.players)
    assert avg >= 0


def test_match_accuracy_empty_without_results(data):
    assert stats.match_accuracy(data, Results()) == {}
