"""Tests de la arquitectura multi-competición y del stub de la Eurocopa 2028."""

import pytest

from streamlit.testing.v1 import AppTest

from porra.competitions import COMPETITIONS, DEFAULT_ID, get_competition
from porra.euro2028 import _SKELETON, _rows_to_matches, load_euro2028, prettify
from porra.models import EURO2028_FORMAT, Phase, WC2026_FORMAT
from porra.results_store import Results
from porra.scoring import categories_for, scoreboard
from porra.tournament import compute_group_standings, resolved_match_teams


# --------------------------------------------------------------------------- registro

def test_registry_has_both_competitions():
    assert set(COMPETITIONS) == {"wc2026", "euro2028"}
    assert DEFAULT_ID == "wc2026"
    assert get_competition(None).id == "wc2026"
    assert get_competition("desconocida").id == "wc2026"  # fallback


def test_formats_are_coherent():
    assert WC2026_FORMAT.n_groups == 12 and WC2026_FORMAT.thirds_qualify == 8
    assert WC2026_FORMAT.has_third_place is True
    assert WC2026_FORMAT.total_matches == 104
    assert WC2026_FORMAT.first_ko_phase is Phase.R32
    assert WC2026_FORMAT.third_place_match_number == 103

    assert EURO2028_FORMAT.n_groups == 6 and EURO2028_FORMAT.thirds_qualify == 4
    assert EURO2028_FORMAT.has_third_place is False
    assert EURO2028_FORMAT.total_matches == 51
    assert EURO2028_FORMAT.first_ko_phase is Phase.R16
    assert EURO2028_FORMAT.third_place_match_number is None
    # la Euro no tiene ni 1/16 ni 3er/4º puesto en su escalera KO
    assert Phase.R32 not in EURO2028_FORMAT.ko_order
    assert Phase.THIRD not in EURO2028_FORMAT.ko_order
    assert EURO2028_FORMAT.matches_per_group == 6


def test_phase_for_number_boundaries():
    f = EURO2028_FORMAT
    assert f.phase_for_number(1) is Phase.GROUPS
    assert f.phase_for_number(36) is Phase.GROUPS
    assert f.phase_for_number(37) is Phase.R16
    assert f.phase_for_number(44) is Phase.R16
    assert f.phase_for_number(45) is Phase.QF
    assert f.phase_for_number(49) is Phase.SF
    assert f.phase_for_number(51) is Phase.FINAL


# --------------------------------------------------------------------------- calendario Euro

def test_euro_skeleton_is_complete_and_well_formed():
    matches = _rows_to_matches(_SKELETON)
    assert len(matches) == 51
    by_phase = {}
    for m in matches:
        by_phase[m.phase] = by_phase.get(m.phase, 0) + 1
    assert by_phase == {Phase.GROUPS: 36, Phase.R16: 8, Phase.QF: 4, Phase.SF: 2, Phase.FINAL: 1}
    assert sorted({m.group for m in matches if m.group}) == list("ABCDEF")
    # todos con fecha y sede
    assert all(m.date and m.city and m.stadium for m in matches)
    # numeración correlativa 1..51
    assert [m.number for m in matches] == list(range(1, 52))


def test_euro_loader_builds_tournament_data():
    data = load_euro2028()  # scraping en vivo con fallback al esqueleto
    assert data.competition_id == "euro2028"
    assert data.format is EURO2028_FORMAT
    assert len(data.matches) == 51
    assert data.teams == [] and data.players == []
    # el bracket son los 15 partidos KO
    assert len(data.bracket) == 15


def test_prettify_placeholders():
    assert prettify("Winner Group A") == "1.º Grupo A"
    assert prettify("Runner-up Group C") == "2.º Grupo C"
    assert prettify("3rd Group A/D/E/F") == "3.º (A/D/E/F)"
    assert prettify("Winner Match 39") == "Ganador M39"
    assert prettify("A1") == "A1"          # ranura de grupo: intacta
    assert prettify("1E") == "1E"          # token del Mundial: intacto


# --------------------------------------------------------------------------- motor genérico

def test_engine_no_crash_on_empty_competition():
    data = load_euro2028()
    results = Results()
    assert scoreboard(data, results) == []           # sin jugadores
    assert compute_group_standings(data, results) == {}  # sin equipos
    resolved = resolved_match_teams(data, results)
    assert len(resolved) == 15
    assert all(h is None and a is None for h, a in resolved.values())


def test_euro_categories_exclude_wc_only_rounds():
    cats = categories_for(EURO2028_FORMAT)
    assert "Equipos 1/16" not in cats and "Partidos 1/16" not in cats  # no R32
    assert "Equipos 3-4" not in cats and "Partidos 3-4" not in cats    # no 3er puesto
    assert "Equipos 1/8" in cats and "Partido Final" in cats


# --------------------------------------------------------------------------- UI (ruta Euro)

@pytest.mark.parametrize("page", [
    "app.py",
    "pages/1_Calendario_y_Resultados.py",
    "pages/3_Clasificación.py",
    "pages/5_Grupos_y_Brackets.py",
])
def test_euro_pages_run_without_exception(page):
    at = AppTest.from_file(page, default_timeout=60)
    at.session_state["competition_id"] = "euro2028"
    at.run()
    assert not at.exception, f"{page} (Euro) lanzó excepción: {at.exception}"
