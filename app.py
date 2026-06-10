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
      <h1 class="hero-title">Pa porra<br><span class="acc">la mía</span></h1>
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
c2.metric("Grupos jugados", f"{played}/72")
c3.metric("Eliminatorias", f"{total_ko}/32")
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
          <div class="sub">Introduce los primeros resultados en <b>Resultados</b> y la
          clasificación cobrará vida. El Mundial arranca el 11 de junio de 2026.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------- navegación
st.markdown('<div class="section-label">Explora la porra</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="navgrid">
      <div class="navcard"><div class="ico">📝</div><div class="t">Resultados</div>
        <div class="d">Introduce goles, sincroniza con ESPN y fija el cuadro de honor.</div></div>
      <div class="navcard"><div class="ico">📅</div><div class="t">Calendario</div>
        <div class="d">Consulta de un vistazo todos los partidos y sus marcadores.</div></div>
      <div class="navcard"><div class="ico">🏆</div><div class="t">Clasificación</div>
        <div class="d">Ranking de los 19 con desglose por categoría.</div></div>
      <div class="navcard"><div class="ico">👤</div><div class="t">Jugador</div>
        <div class="d">Predicciones, aciertos y puntos de cada participante.</div></div>
      <div class="navcard"><div class="ico">📊</div><div class="t">Grupos y Brackets</div>
        <div class="d">Tablas de grupo y el cuadro de eliminatorias en vivo.</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)
