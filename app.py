"""Pa porra la mía — porra del Mundial 2026.

App Streamlit que analiza la porra de ``docs/ADMIN.xlsx`` reproduciendo la
puntuación del Excel en Python, y actualiza automáticamente los resultados de los
partidos por scraping (ESPN, con Wikipedia de reserva).

Ejecutar con:  ``streamlit run app.py``
"""

from __future__ import annotations

import streamlit as st

from porra.models import Phase
from porra.scoring import scoreboard
from porra.tournament import group_phase_complete
from ui_common import configure_page, fmt, get_data, get_results, proper_name

configure_page()

data = get_data()
results = get_results()

played = sum(1 for m in data.matches if m.phase is Phase.GROUPS and results.has(m.number))
total_ko = sum(1 for m in data.matches if m.phase.is_knockout and results.has(m.number))
complete = group_phase_complete(data, results)

# ----------------------------------------------------------------- hero
st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">Copa Mundial · 2026 · USA · México · Canadá</div>
      <h1 class="hero-title">Pa porra <span class="acc">la mía</span></h1>
      <div class="hero-sub">La porra de los 19. Puntuación al milímetro, calcada de la
      plantilla original: 1X2, diferencia, resultado exacto, posiciones, brackets y cuadro de honor.</div>
      <div class="hero-rule"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------- marcador de estado
c1, c2, c3, c4 = st.columns(4)
c1.metric("Participantes", len(data.players))
c2.metric("Partidos Fase de Grupos", f"{played} / 72")
c3.metric("Eliminatorias", f"{total_ko} / 32")
c4.metric("Fase de grupos", "Completa" if complete else "En curso")

# ----------------------------------------------------------------- líderes
sb = scoreboard(data, results)
st.markdown('<div class="section-label">Clasificación general</div>', unsafe_allow_html=True)

if sb and sb[0].total > 0:
    top = [s for s in sb if s.total > 0][:5]
    maxpts = top[0].total or 1
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    rows = []
    for i, s in enumerate(top, 1):
        pct = max(6, round(s.total / maxpts * 100))
        medal = f'<span class="medal">{medals[i]}</span>' if i in medals else ""
        rows.append(
            f'<div class="board-row r{i}" style="animation-delay:{(i-1)*70}ms">'
            f'<div class="rank">{i}</div>'
            f'<div class="meta"><div class="who">{medal} {proper_name(s.name)}</div>'
            f'<div class="barwrap"><span class="bar" style="width:{pct}%"></span></div></div>'
            f'<div class="pts">{fmt(s.total)}<small>PTS</small></div>'
            f"</div>"
        )
    st.markdown('<div class="board">' + "".join(rows) + "</div>", unsafe_allow_html=True)
    st.caption("Clasificación completa y desglose por categoría en la página **Clasificación**.")
else:
    st.markdown(
        """
        <div class="empty-card">
          <div class="big">El balón aún no rueda</div>
          <div class="sub">Los resultados se cargan <b>automáticamente</b> desde ESPN y
          Wikipedia; la clasificación cobrará vida en cuanto se juegue el primer partido.
          El Mundial arranca el 11 de junio de 2026.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------- navegación
st.markdown('<div class="section-label">Explora la porra</div>', unsafe_allow_html=True)
NAV = [
    ("pages/1_Resultados.py", "📝 Resultados",
     "Marcadores actualizados automáticamente desde ESPN y Wikipedia."),
    ("pages/5_Calendario.py", "📅 Calendario",
     "Todos los partidos y sus marcadores de un vistazo."),
    ("pages/2_Clasificación.py", "🏆 Clasificación",
     "Ranking de los 19 con desglose por categoría."),
    ("pages/3_Jugador.py", "👤 Jugador",
     "Predicciones, aciertos y puntos de cada participante."),
    ("pages/4_Grupos_y_Brackets.py", "📊 Grupos y Brackets",
     "Tablas de grupo y el cuadro de eliminatorias en vivo."),
    ("pages/6_Estadísticas.py", "📈 Estadísticas",
     "Favoritos, aciertos por selección y otros KPIs de la porra."),
]
nav_cols = st.columns(3)
for i, (path, label, desc) in enumerate(NAV):
    with nav_cols[i % 3]:
        st.page_link(path, label=label, use_container_width=True)
        st.caption(desc)
