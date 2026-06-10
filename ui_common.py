"""Utilidades compartidas por las páginas Streamlit de "Pa porra la mía".

Mantiene el paquete ``porra`` libre de dependencias de Streamlit: aquí viven
los envoltorios cacheados y el estado de sesión.
"""

from __future__ import annotations

import streamlit as st

from porra.excel_loader import load_tournament
from porra.github_sync import commit_file
from porra.models import Phase, TournamentData
from porra.results_store import DEFAULT_RESULTS, Results, load_results, save_results, to_dict

import json

APP_TITLE = "Pa porra la mía"
# No existe un emoji fiel a la porra del as de bastos (la maza nudosa de la baraja
# española), así que usamos la berenjena como pidió el usuario.
APP_ICON = "🍆"

PHASE_LABELS = {
    Phase.GROUPS: "Fase de grupos",
    Phase.R32: "Dieciseisavos",
    Phase.R16: "Octavos",
    Phase.QF: "Cuartos",
    Phase.SF: "Semifinales",
    Phase.THIRD: "3er y 4º puesto",
    Phase.FINAL: "Final",
}

# Etiquetas legibles del cuadro de honor (clave interna -> texto a mostrar).
HONOR_LABELS = {
    "campeon": "Campeón", "subcampeon": "Subcampeón", "tercero": "3er puesto",
    "bota_oro": "Bota de Oro", "bota_plata": "Bota de Plata", "bota_bronce": "Bota de Bronce",
    "balon_oro": "Balón de Oro", "balon_plata": "Balón de Plata", "balon_bronce": "Balón de Bronce",
}


@st.cache_data(show_spinner="Leyendo ADMIN.xlsx…")
def get_data() -> TournamentData:
    """Carga (cacheada) los datos del Excel. Inmutable durante la sesión."""
    return load_tournament()


def get_results() -> Results:
    """Resultados en estado de sesión (se cargan una vez desde disco)."""
    if "results" not in st.session_state:
        st.session_state.results = load_results()
    return st.session_state.results


def persist(results: Results) -> None:
    """Guarda en disco y, si hay credenciales de GitHub en ``st.secrets``,
    commitea ``results.json`` al repositorio (necesario en Streamlit Cloud)."""
    save_results(results)
    gh = _github_secrets()
    if not gh:
        return
    content = json.dumps(to_dict(results), ensure_ascii=False, indent=2)
    outcome = commit_file(
        token=gh["token"], repo=gh["repo"],
        path=gh.get("path", "data/results.json"),
        content=content, branch=gh.get("branch", "main"),
    )
    (st.toast if outcome.ok else st.warning)(outcome.message)


def _github_secrets() -> dict | None:
    try:
        gh = st.secrets["github"]
    except Exception:
        return None
    if "token" in gh and "repo" in gh:
        return dict(gh)
    return None


def configure_page() -> None:
    try:
        st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
    except Exception:
        pass  # ya configurada (p.ej. al re-ejecutar)
    from theme import inject_theme
    inject_theme()


def fmt(value: float) -> str:
    """Formatea puntos: entero si no tiene decimales, si no con un decimal."""
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def proper_name(name: str) -> str:
    """Nombre de jugador en formato Proper para mostrar (PACO -> Paco).

    Solo afecta a la presentación; los datos internos conservan el original.
    """
    return str(name).title()
