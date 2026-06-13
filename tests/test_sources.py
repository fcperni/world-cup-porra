"""Tests offline de las fuentes de resultados (normalización y parseo)."""

import pytest

from porra.excel_loader import load_tournament
from porra.results_store import Results
from porra.sources.base import (ScrapedGame, build_name_resolver, map_live_matches,
                                 map_to_matches)
from porra.sources.espn import _parse_scoreboard
from porra.sources.wikipedia import parse_footballboxes


@pytest.fixture(scope="module")
def data():
    return load_tournament()


def test_name_resolver(data):
    resolve = build_name_resolver(data)
    assert resolve("South Korea") == "Corea del Sur"
    assert resolve("Czechia") == "República Checa"
    assert resolve("Netherlands") == "Países Bajos"
    assert resolve("Curaçao") == "Curazao"
    assert resolve("Saudi Arabia") == "Arabia Saudita"
    assert resolve("Türkiye") == "Turquía"
    assert resolve("México") == "México"   # nombre ya canónico
    assert resolve("Mexico") == "México"    # sin acento
    assert resolve("Narnia") is None


def test_map_to_matches_group_same_order(data):
    res = Results()
    # M1 = México vs Sudáfrica
    games = [ScrapedGame("Mexico", "South Africa", 2, 1, finished=True)]
    mapped = map_to_matches(data, res, games)
    assert 1 in mapped
    assert (mapped[1].home_goals, mapped[1].away_goals) == (2, 1)


def test_map_to_matches_reversed_order_orients_score(data):
    res = Results()
    # publican el partido con local/visitante invertidos respecto al calendario
    games = [ScrapedGame("South Africa", "Mexico", 1, 2, finished=True)]
    mapped = map_to_matches(data, res, games)
    # debe reorientarse a México(local) 2 - 1 Sudáfrica(visitante)
    assert (mapped[1].home_goals, mapped[1].away_goals) == (2, 1)


def test_map_ignores_unfinished_and_unknown(data):
    res = Results()
    games = [
        ScrapedGame("Mexico", "South Africa", None, None, finished=False),
        ScrapedGame("Narnia", "Mordor", 3, 0, finished=True),
    ]
    assert map_to_matches(data, res, games) == {}


def test_map_to_matches_ignores_in_progress(data):
    # un partido en juego (con goles ya marcados) NO debe contar como final
    res = Results()
    games = [ScrapedGame("Mexico", "South Africa", 1, 0, finished=False, state="in", clock="35'")]
    assert map_to_matches(data, res, games) == {}


def test_map_live_matches(data):
    res = Results()
    # M1 = México vs Sudáfrica, en juego 1-0 al minuto 35
    games = [ScrapedGame("Mexico", "South Africa", 1, 0, finished=False, state="in", clock="35'")]
    live = map_live_matches(data, res, games)
    assert 1 in live
    assert (live[1].home_goals, live[1].away_goals, live[1].clock) == (1, 0, "35'")


def test_map_live_orients_reversed_score(data):
    res = Results()
    # publican el directo con local/visitante invertidos respecto al calendario
    games = [ScrapedGame("South Africa", "Mexico", 0, 2, finished=False, state="in", clock="HT")]
    live = map_live_matches(data, res, games)
    # México (local del calendario) 2 - 0 Sudáfrica
    assert (live[1].home_goals, live[1].away_goals) == (2, 0)


def test_map_live_excludes_finished(data):
    res = Results()
    games = [ScrapedGame("Mexico", "South Africa", 2, 1, finished=True, state="post")]
    assert map_live_matches(data, res, games) == {}


def test_espn_parse_scoreboard():
    payload = {"events": [{
        "date": "2026-06-11T21:00Z",
        "status": {"type": {"completed": True}},
        "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"displayName": "Mexico"}, "score": "2", "winner": True},
            {"homeAway": "away", "team": {"displayName": "South Africa"}, "score": "1", "winner": False},
        ]}],
    }]}
    games = _parse_scoreboard(payload)
    assert len(games) == 1
    g = games[0]
    assert (g.home, g.away, g.home_goals, g.away_goals, g.finished) == \
        ("Mexico", "South Africa", 2, 1, True)
    assert g.winner == "home"


def test_espn_parse_in_progress():
    payload = {"events": [{
        "date": "2026-06-11T21:00Z",
        "status": {"type": {"completed": False, "state": "in", "shortDetail": "67'"}},
        "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"displayName": "Mexico"}, "score": "1"},
            {"homeAway": "away", "team": {"displayName": "South Africa"}, "score": "0"},
        ]}],
    }]}
    g = _parse_scoreboard(payload)[0]
    assert g.state == "in" and g.clock == "67'" and not g.finished
    assert g.in_progress is True


def test_wikipedia_parse_footballbox():
    html = """
    <div class="footballbox">
      <div class="fhome"><a title="Mexico national football team">Mexico</a></div>
      <div class="fscore">2–1</div>
      <div class="faway"><a title="South Africa national soccer team">South Africa</a></div>
    </div>
    """
    games = parse_footballboxes(html)
    assert len(games) == 1
    g = games[0]
    assert g.home_goals == 2 and g.away_goals == 1 and g.finished
    assert "Mexico" in g.home and "South Africa" in g.away
