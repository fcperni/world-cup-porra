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


def _sf_session():
    """Sesión Snowpark activa si la app corre en Streamlit-in-Snowflake, o None."""
    try:
        from snowflake.snowpark.context import get_active_session
        return get_active_session()
    except Exception:
        return None


def get_results() -> Results:
    """Resultados en estado de sesión, con sincronización automática app-wide.

    Carga desde la tabla ``PORRA_RESULTS`` (Snowflake) o ``results.json`` (local/
    Cloud) y, al abrir **cualquier** página, incorpora los marcadores nuevos
    scrapeados (caché de 15 min), de modo que todas las secciones —incluido
    Calendario y Resultados— reflejan los marcadores sin intervención manual.
    """
    if "results" not in st.session_state:
        session = _sf_session()
        if session is not None:
            from porra.snowflake_store import load_results_sf
            st.session_state.results = load_results_sf(session)
        else:
            st.session_state.results = load_results()
    auto_sync(st.session_state.results)
    return st.session_state.results


@st.cache_data(ttl=900, show_spinner="Actualizando resultados desde ESPN y Wikipedia…")
def _fetch_games():
    """Descarga (cacheada 15 min) los partidos publicados por las fuentes."""
    from porra.sources.espn import ESPNSource
    from porra.sources.wikipedia import WikipediaSource

    data = get_data()
    games = []
    for source in (ESPNSource(), WikipediaSource()):
        try:
            games.extend(source.fetch(data))
        except Exception:  # noqa: BLE001 — una fuente caída no debe romper la app
            continue
    return games


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_live_games():
    """Descarga (cacheada 30 s) los partidos de ESPN para el seguimiento en directo.

    Solo ESPN: su API JSON es rápida e informa del estado del partido (en juego /
    finalizado) y del reloj, mientras que Wikipedia no da el directo de forma fiable.
    """
    from porra.sources.espn import ESPNSource

    try:
        return ESPNSource().fetch(get_data())
    except Exception:  # noqa: BLE001 — el directo es best-effort
        return []


def _combined_games():
    """Juegos para sincronizar finales: el directo (fresco, 30 s) tiene prioridad
    sobre la descarga combinada de 15 min ante un mismo enfrentamiento."""
    seen: set[tuple[str, str]] = set()
    out = []
    for g in list(_fetch_live_games()) + list(_fetch_games()):
        key = (g.home, g.away)
        if key not in seen:
            seen.add(key)
            out.append(g)
    return out


def get_live(results: Results) -> dict:
    """Marcadores en directo (``{nº: LiveMatch}``) de los partidos en juego.

    Provisional y **no** persistido: no toca ``results`` ni cuenta para los puntos,
    que solo se calculan cuando el partido finaliza y entra por :func:`auto_sync`.
    Excluye los que ya tienen resultado final almacenado.
    """
    from porra.sources.base import map_live_matches
    from porra.tournament import resolved_match_teams

    data = get_data()
    teams = resolved_match_teams(data, results)
    live = map_live_matches(data, results, _fetch_live_games(), teams)
    return {n: lm for n, lm in live.items() if not results.has(n)}


def auto_sync(results: Results) -> int:
    """Incorpora los resultados nuevos de las fuentes. Devuelve cuántos aplicó."""
    from porra.sources.base import map_to_matches
    from porra.tournament import resolved_match_teams

    data = get_data()
    try:
        games = _combined_games()
    except Exception:  # noqa: BLE001
        return 0
    applied = 0
    for _ in range(6):  # varias pasadas: al cerrar una ronda se resuelve la siguiente
        teams = resolved_match_teams(data, results)
        proposals = map_to_matches(data, results, games, teams)
        nuevos = {n: mr for n, mr in proposals.items()
                  if results.goals(n) != (mr.home_goals, mr.away_goals)}
        if not nuevos:
            break
        for n, mr in nuevos.items():
            results.set_match(n, mr.home_goals, mr.away_goals)
            if mr.winner and mr.home_goals == mr.away_goals:
                results.ko_winners[n] = mr.winner
            applied += 1
    if applied:
        persist(results)
    return applied


def force_resync() -> None:
    """Limpia la caché de scraping para forzar una actualización inmediata."""
    _fetch_games.clear()
    _fetch_live_games.clear()


def persist(results: Results) -> None:
    """Guarda los resultados en el backend adecuado.

    * Snowflake: tabla ``PORRA_RESULTS`` (Snowpark).
    * Streamlit Cloud / local: ``data/results.json`` y, si hay credenciales de
      GitHub en ``st.secrets``, commit al repositorio.
    """
    session = _sf_session()
    if session is not None:
        from porra.snowflake_store import save_results_sf
        save_results_sf(session, results)
        try:
            st.toast("Guardado en Snowflake ✅")
        except Exception:
            pass
        return

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
