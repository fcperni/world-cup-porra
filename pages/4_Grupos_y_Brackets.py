"""Clasificación de cada grupo y (próximamente) cuadro de eliminatorias."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from porra.models import KO_ORDER
from porra.tournament import compute_group_standings, resolved_match_teams
from ui_common import PHASE_LABELS, configure_page, get_data, get_results

configure_page()
st.title("📊 Grupos y Brackets")

data = get_data()
results = get_results()

tab_grupos, tab_brackets = st.tabs(["Clasificación de grupos", "Eliminatorias"])

with tab_grupos:
    standings = compute_group_standings(data, results)
    cols = st.columns(3)
    for i, (group, ranked) in enumerate(standings.items()):
        with cols[i % 3]:
            st.markdown(f"**Grupo {group}**")
            df = pd.DataFrame([{
                "": pos,
                "Selección": r.team.name,
                "Pts": r.points,
                "J": r.played,
                "GF": r.gf,
                "GC": r.ga,
                "DG": r.gd,
            } for pos, r in enumerate(ranked, 1)])
            st.dataframe(df, hide_index=True, use_container_width=True)

with tab_brackets:
    st.caption(
        "Los cruces se rellenan con las selecciones reales (mejores terceros y "
        "ganadores) conforme avanzan las rondas. Lo aún no determinado se muestra "
        "como su referencia (p.ej. `W74`, `3ABCDF`)."
    )
    teams = resolved_match_teams(data, results)

    def slot_name(number: int, side: int) -> str:
        t = teams[number][side]
        if t is not None:
            return t.name
        return data.bracket[number][side]  # placeholder crudo

    for phase in KO_ORDER:
        matches = sorted([m for m in data.matches if m.phase is phase], key=lambda m: m.number)
        rows = []
        for m in matches:
            g = results.goals(m.number)
            marcador = f"{g[0]}-{g[1]}" if g else "—"
            if g and g[0] == g[1] and m.number in results.ko_winners:
                side = results.ko_winners[m.number]
                marcador += f" (pasa {slot_name(m.number, 0 if side == 'home' else 1)})"
            rows.append({"Nº": m.number, "Local": slot_name(m.number, 0),
                         "Marcador": marcador, "Visitante": slot_name(m.number, 1)})
        st.markdown(f"**{PHASE_LABELS[phase]}**")
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
