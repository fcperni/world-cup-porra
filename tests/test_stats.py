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


def test_match_sign_splits_only_group_matches(data):
    splits = stats.match_sign_splits(data)
    group_numbers = {m.number for m in data.matches if m.phase is Phase.GROUPS}
    assert set(splits) == group_numbers
    for s in splits.values():
        assert s.total <= len(data.players)
        assert sum(s.counts.values()) == s.total
        if s.total:
            assert s.counts[s.majority_sign] == max(s.counts.values())
            assert s.dissenters == s.total - s.counts[s.majority_sign]


def test_opening_match_consensus(data):
    """El partido inaugural (M1): 17 dan local, BONERA empate, PACO visitante."""
    s = stats.match_sign_splits(data)[1]
    assert s.majority_sign == "1"
    assert s.voters["X"] == ["BONERA"]
    assert s.voters["2"] == ["PACO"]
    assert s.dissenters == 2
    assert not s.is_unanimous


def test_player_dissent_range(data):
    d = stats.player_dissent(data)
    # un valor por jugador, no negativo y acotado por el nº de partidos de grupos
    assert set(d) == {p.name for p in data.players}
    n_group = sum(1 for m in data.matches if m.phase is Phase.GROUPS)
    assert all(0 <= v <= n_group for v in d.values())


def test_popular_scorelines_and_profile_consistent(data):
    sc = stats.popular_scorelines(data)
    prof = stats.prediction_profile(data)
    # el total del perfil coincide con la suma de todos los marcadores contados
    assert sum(sc.values()) == prof["total"]
    assert 0.0 <= prof["pct_draws"] <= 1.0
    assert prof["avg_goals"] >= 0.0
    # las claves son pares (local, visitante) de enteros no negativos
    for (h, a), v in sc.items():
        assert isinstance(h, int) and isinstance(a, int) and h >= 0 and a >= 0 and v >= 1


def test_team_splits_only_knockout(data):
    splits = stats.match_team_splits(data)
    ko_numbers = {m.number for m in data.matches if m.phase.is_knockout}
    assert set(splits) == ko_numbers
    for kt in splits.values():
        assert kt.total <= len(data.players)
        # cada jugador mete como mucho 2 selecciones en el cruce
        assert sum(kt.counts.values()) <= 2 * kt.total
        if kt.counts:
            assert kt.counts[kt.top_team] == max(kt.counts.values())
