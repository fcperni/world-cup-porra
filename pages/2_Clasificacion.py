"""Clasificación general de los 19 participantes."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from porra.scoring import CATEGORIES, scoreboard
from ui_common import configure_page, get_data, get_results

configure_page()
st.title("🏆 Clasificación")

data = get_data()
results = get_results()
sb = scoreboard(data, results)

if all(s.total == 0 for s in sb):
    st.info("Todavía no hay puntos. Introduce resultados en **📝 Resultados**.")
    st.stop()

# Tabla principal: posición, jugador, total
main = pd.DataFrame({
    "Pos": range(1, len(sb) + 1),
    "Jugador": [s.name for s in sb],
    "Puntos": [round(s.total, 1) for s in sb],
})
st.subheader("Ranking")
st.dataframe(
    main,
    hide_index=True,
    use_container_width=True,
    column_config={"Puntos": st.column_config.NumberColumn(format="%.1f")},
)

# Desglose por categoría (solo columnas con algún punto)
st.subheader("Desglose por categoría")
active = [c for c in CATEGORIES if any(s.categories[c] for s in sb)]
if not active:
    st.caption("Sin categorías con puntos todavía.")
else:
    detail = pd.DataFrame(
        [{"Jugador": s.name, **{c: round(s.categories[c], 1) for c in active},
          "Total": round(s.total, 1)} for s in sb]
    )
    st.dataframe(
        detail,
        hide_index=True,
        use_container_width=True,
        column_config={c: st.column_config.NumberColumn(format="%.1f")
                       for c in active + ["Total"]},
    )
    st.bar_chart(detail.set_index("Jugador")["Total"], horizontal=True)
