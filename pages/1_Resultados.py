"""Resultados — se actualizan AUTOMÁTICAMENTE desde ESPN (Wikipedia de reserva).

No hay entrada ni sincronización manual: al abrir esta página se consultan las
fuentes (con caché para no saturarlas) y se incorporan los marcadores de los
partidos ya disputados. El ganador en eliminatorias con empate se toma del dato
de la fuente.
"""

from __future__ import annotations

import streamlit as st

from porra.sources.base import map_to_matches
from porra.sources.espn import ESPNSource
from porra.sources.wikipedia import WikipediaSource
from porra.tournament import resolved_match_teams
from ui_common import configure_page, get_data, get_results, persist

configure_page()
st.title("📝 Resultados")


@st.cache_data(ttl=900, show_spinner="Actualizando resultados desde ESPN y Wikipedia…")
def _fetch_games():
    """Descarga (cacheada 15 min) los partidos publicados por las fuentes."""
    data = get_data()
    games = []
    for source in (ESPNSource(), WikipediaSource()):
        try:
            games.extend(source.fetch(data))
        except Exception:  # noqa: BLE001 — una fuente caída no debe romper la página
            continue
    return games


def _auto_update(data, results) -> int:
    """Incorpora los resultados nuevos de las fuentes. Devuelve cuántos aplicó."""
    games = _fetch_games()
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


data = get_data()
results = get_results()
nuevos = _auto_update(data, results)

played = sum(1 for m in data.matches if results.has(m.number))
c1, c2 = st.columns(2)
c1.metric("Partidos con resultado", f"{played} / 104")
c2.metric("Pendientes", 104 - played)

st.caption(
    "Los resultados se actualizan **automáticamente** desde ESPN (y Wikipedia como "
    "reserva) cada vez que abres esta página. No hay que introducir ni sincronizar "
    "nada a mano."
)

if nuevos:
    st.success(f"Se han incorporado {nuevos} resultado(s) nuevo(s).")
elif played:
    st.info("Todo al día: no hay resultados nuevos desde la última consulta.", icon="✅")
else:
    st.info("Aún no hay partidos disputados. Esta página los recogerá en cuanto se jueguen.",
            icon="🗓️")

st.caption("Consulta el detalle de todos los partidos en **Calendario** y la tabla en "
           "**Clasificación**.")
