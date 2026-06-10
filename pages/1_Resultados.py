"""Resultados — sincronización automática desde ESPN (Wikipedia de reserva).

Los marcadores NO se editan a mano: se obtienen scrapeando las webs indicadas.
El ganador en eliminatorias con empate se toma del propio dato de la fuente.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from porra.sources.base import sync_results
from porra.sources.espn import ESPNSource
from porra.sources.wikipedia import WikipediaSource
from porra.tournament import resolved_match_teams
from ui_common import configure_page, get_data, get_results, persist

configure_page()
st.title("📝 Resultados")

data = get_data()
results = get_results()

played = sum(1 for m in data.matches if results.has(m.number))
c1, c2 = st.columns(2)
c1.metric("Partidos con resultado", f"{played}/104")
c2.metric("Pendientes", 104 - played)

st.caption(
    "Los resultados se obtienen **automáticamente** de ESPN (y Wikipedia como "
    "reserva); no se editan a mano. Pulsa **Sincronizar** para traer los marcadores "
    "de los partidos ya disputados. Revisa los cambios antes de aplicarlos."
)

if st.button("🔄 Sincronizar resultados", type="primary"):
    with st.spinner("Consultando ESPN y Wikipedia…"):
        teams_now = resolved_match_teams(data, results)
        st.session_state.proposals = sync_results(
            data, results, [ESPNSource(), WikipediaSource()], teams_now)

proposals = st.session_state.get("proposals")
if proposals is not None:
    changes = []
    for num, mr in sorted(proposals.items()):
        m = data.match_by_number(num)
        current = results.goals(num)
        new = (mr.home_goals, mr.away_goals)
        if current != new:
            changes.append({
                "Nº": num,
                "Partido": f"{m.home} - {m.away}" if m else str(num),
                "Actual": f"{current[0]}-{current[1]}" if current else "—",
                "Nuevo": f"{new[0]}-{new[1]}",
            })
    if not changes:
        st.success("Todo al día: la fuente no trae resultados nuevos.")
    else:
        st.dataframe(pd.DataFrame(changes), hide_index=True, use_container_width=True)
        if st.button(f"✅ Aplicar {len(changes)} cambios", type="primary"):
            for num, mr in proposals.items():
                results.set_match(num, mr.home_goals, mr.away_goals)
                if mr.winner and mr.home_goals == mr.away_goals:
                    results.ko_winners[num] = mr.winner
            persist(results)
            del st.session_state.proposals
            st.success(f"{len(changes)} resultados aplicados.")
            st.rerun()
else:
    st.info("Pulsa **Sincronizar resultados** para empezar.", icon="🔄")
