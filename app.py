"""Pa porra la mía — porra del Mundial 2026.

App Streamlit que analiza la porra de ``docs/ADMIN.xlsx`` reproduciendo la
puntuación del Excel en Python, y permite introducir los resultados de los
partidos (manualmente o, más adelante, por scraping de ESPN/Wikipedia).

Ejecutar con:  ``streamlit run app.py``
"""

from __future__ import annotations

import streamlit as st

from porra.models import Phase
from porra.scoring import scoreboard
from porra.tournament import group_phase_complete
from ui_common import APP_ICON, APP_TITLE, configure_page, fmt, get_data, get_results

configure_page()

st.title(f"{APP_ICON} {APP_TITLE}")
st.caption("Porra del Mundial 2026 · 48 selecciones · 19 participantes")

data = get_data()
results = get_results()

played = sum(1 for m in data.matches if m.phase is Phase.GROUPS and results.has(m.number))
total_ko = sum(1 for m in data.matches if m.phase.is_knockout and results.has(m.number))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Participantes", len(data.players))
col2.metric("Partidos de grupos jugados", f"{played}/72")
col3.metric("Partidos KO jugados", f"{total_ko}/32")
col4.metric("Fase de grupos", "Completa" if group_phase_complete(data, results) else "En curso")

st.divider()

# Vista rápida del liderato
sb = scoreboard(data, results)
if sb and sb[0].total > 0:
    st.subheader("🏆 Líder actual")
    leader = sb[0]
    st.metric(leader.name, f"{fmt(leader.total)} pts")
else:
    st.info(
        "Aún no hay resultados. Ve a **📝 Resultados** para empezar a introducir "
        "los marcadores de los partidos."
    )

st.divider()
st.markdown(
    """
    ### Cómo usar la app
    - **📝 Resultados** — introduce los goles de cada partido (y el cuadro de honor).
    - **🏆 Clasificación** — ranking de los 19 jugadores con desglose por categoría.
    - **👤 Jugador** — predicciones, aciertos y puntos de un participante.
    - **📊 Grupos y Brackets** — clasificación de cada grupo y cuadro de eliminatorias.

    La puntuación reproduce **exactamente** las reglas de la plantilla Excel
    (`ADMIN.xlsx`): signo 1X2, crédito parcial por diferencia de goles, resultado
    exacto, posiciones de grupo, clasificados por ronda y cuadro de honor, con sus
    multiplicadores de bonus.
    """
)
