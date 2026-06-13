"""Smoke test: cada página de Streamlit se ejecuta sin lanzar excepciones."""

import pytest

from streamlit.testing.v1 import AppTest

PAGES = [
    "app.py",
    "pages/1_Calendario_y_Resultados.py",
    "pages/2_Predicciones_del_partido.py",
    "pages/3_Clasificación.py",
    "pages/4_Jugador.py",
    "pages/5_Grupos_y_Brackets.py",
    "pages/6_Curiosidades.py",
    "pages/7_Estadísticas.py",
    "pages/8_Admin.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_without_exception(page):
    at = AppTest.from_file(page, default_timeout=30).run()
    assert not at.exception, f"{page} lanzó excepción: {at.exception}"
