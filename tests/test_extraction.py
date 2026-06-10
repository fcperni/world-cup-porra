"""Invariantes de la extracción de ADMIN.xlsx (porra.excel_loader)."""

import pytest

from porra.excel_loader import load_tournament, parse_score, parse_ko_prediction
from porra.models import Phase


@pytest.fixture(scope="module")
def data():
    return load_tournament()


def test_48_teams_in_12_groups(data):
    assert len(data.teams) == 48
    groups = sorted({t.group for t in data.teams})
    assert groups == list("ABCDEFGHIJKL")
    for g in groups:
        assert sum(1 for t in data.teams if t.group == g) == 4


def test_104_matches_by_phase(data):
    assert len(data.matches) == 104
    counts = {}
    for m in data.matches:
        counts[m.phase] = counts.get(m.phase, 0) + 1
    assert counts == {
        Phase.GROUPS: 72, Phase.R32: 16, Phase.R16: 8,
        Phase.QF: 4, Phase.SF: 2, Phase.THIRD: 1, Phase.FINAL: 1,
    }


def test_all_matches_linked_to_admin_rows(data):
    assert all(m.admin_row for m in data.matches)


def test_bracket_has_32_knockout_crosses(data):
    assert len(data.bracket) == 32
    # los placeholders de octavos referencian ganadores de 1/16
    assert data.bracket[89] == ("W74", "W77")
    assert data.bracket[104] == ("W101", "W102")  # final
    assert data.bracket[103] == ("L101", "L102")  # 3er puesto


def test_19_players_with_predictions(data):
    assert len(data.players) == 19
    paco = next(p for p in data.players if p.name == "PACO")
    assert len(paco.group_matches) == 72
    assert len(paco.ko_matches) == 32
    assert len(paco.group_positions) == 48
    assert len(paco.qualified[Phase.R32]) == 32
    assert paco.honor["campeon"]  # tiene cuadro de honor relleno


def test_scoring_rules_complete(data):
    p = data.rules.points
    assert p[(Phase.GROUPS, "signo")] == 1
    assert p[(Phase.GROUPS, "diferencia")] == 3
    assert p[(Phase.GROUPS, "exacto")] == 3
    assert p[(Phase.FINAL, "exacto")] == 50
    assert p[(Phase.R32, "clasificado")] == 10
    assert p[(Phase.FINAL, "clasificado")] == 50
    assert all(p[("group_position", i)] == 5 for i in range(1, 5))
    assert p[("honor", "campeon")] == 100
    assert data.rules.diff_adjust == 0.1


@pytest.mark.parametrize("raw,expected", [
    ("1|3-1", ("1", 3, 1)),
    ("X|1-1", ("X", 1, 1)),
    ("2|0-2", ("2", 0, 2)),
    ("", (None, None, None)),
    ("-", (None, None, None)),
    ("3|1-0", (None, None, None)),  # signo inválido
])
def test_parse_score(raw, expected):
    assert parse_score(raw) == expected


def test_parse_ko_prediction_two_teams():
    ko = parse_ko_prediction(73, "Sudáfrica-Suiza·2|1-2")
    assert ko.home_team == "Sudáfrica"
    assert ko.away_team == "Suiza"
    assert (ko.sign, ko.home_goals, ko.away_goals) == ("2", 1, 2)
