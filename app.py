"""Pa porra la mía — porra del Mundial 2026.

App Streamlit que analiza la porra de ``docs/ADMIN.xlsx`` reproduciendo la
puntuación del Excel en Python, y actualiza automáticamente los resultados de los
partidos por scraping (ESPN, con Wikipedia de reserva).

Ejecutar con:  ``streamlit run app.py``
"""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    import random

    import analytics
    from porra.models import Phase
    from porra.scoring import scoreboard
    from porra.tournament import group_phase_complete
    from ui_common import configure_page, fmt, get_data, get_results, proper_name

    configure_page()
    analytics.track("Inicio")

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

        # ------------------------------------------------------------- farolillos rojos
        ranked = [s for s in sb if s.total > 0]
        n = len(ranked)
        if n > 5:
            bottom = ranked[-5:]
            start = n - len(bottom) + 1
            st.markdown('<div class="section-label">Farolillos rojos</div>', unsafe_allow_html=True)
            # Avatar "inventado" del último: al hacer hover sobre su farolillo 🏮 sale
            # una estampa graciosa y emblemática (emoji grande + pulla), aleatoria por carga.
            LANTERN_AVATARS = [
                ("🐢", "Llegando a meta… el año que viene"),
                ("🦤", "Oficialmente extinto en la tabla"),
                ("🥄", "Cuchara de palo, premio al farolillo"),
                ("🤡", "El espectáculo está asegurado"),
                ("🐌", "Compitiendo a su propio ritmo"),
                ("💩", "Pleno de fallos, sin despeinarse"),
                ("🧂", "Le echa sal a cada pronóstico"),
                ("🪦", "Aquí yacen sus predicciones"),
                ("🫠", "Derritiéndose en el fondo de la tabla"),
                ("🚑", "Necesita rescate clasificatorio urgente"),
                ("🦨", "Apesta a porra… pero con cariño"),
                ("🐔", "Se le escapó hasta el gol cantado"),
            ]
            brows = []
            for j, s in enumerate(bottom):
                pos = start + j
                pct = max(6, round(s.total / maxpts * 100))
                last = " last" if pos == n else ""
                lantern = ""
                if pos == n:
                    emoji, cap = random.choice(LANTERN_AVATARS)
                    lantern = (
                        '<span class="lantern" title="El farolillo rojo">🏮'
                        '<span class="avatar-pop">'
                        f'<span class="av-emoji">{emoji}</span>'
                        f'<span class="av-cap">{cap}</span></span></span>'
                    )
                brows.append(
                    f'<div class="board-row{last}" style="animation-delay:{j*70}ms">'
                    f'<div class="rank">{pos}</div>'
                    f'<div class="meta"><div class="who">{proper_name(s.name)}{lantern}</div>'
                    f'<div class="barwrap"><span class="bar" style="width:{pct}%"></span></div></div>'
                    f'<div class="pts">{fmt(s.total)}<small>PTS</small></div>'
                    f"</div>"
                )
            st.markdown('<div class="board cold">' + "".join(brows) + "</div>", unsafe_allow_html=True)
            st.caption("Los 5 con menos puntos. ¡Aún hay torneo por delante!")
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
        ("pages/1_Calendario_y_Resultados.py", "📅 Calendario y Resultados",
         "Todos los partidos y sus marcadores, actualizados automáticamente desde ESPN y Wikipedia."),
        ("pages/2_Predicciones_del_partido.py", "🎯 Predicciones del partido",
         "Las predicciones de los 19 para un mismo partido, de un vistazo."),
        ("pages/3_Clasificación.py", "🏆 Clasificación",
         "Ranking de los 19 con desglose por categoría."),
        ("pages/4_Jugador.py", "👤 Jugador",
         "Predicciones, aciertos y puntos de cada participante."),
        ("pages/5_Grupos_y_Brackets.py", "📊 Grupos y Brackets",
         "Tablas de grupo y el cuadro de eliminatorias en vivo."),
        ("pages/6_Curiosidades.py", "🔮 Curiosidades",
         "El reparto de pronósticos partido a partido: consensos y rebeldes."),
        ("pages/7_Estadísticas.py", "📈 Estadísticas",
         "Favoritos, aciertos por selección y otros KPIs de la porra."),
    ]
    nav_cols = st.columns(3)
    for i, (path, label, desc) in enumerate(NAV):
        with nav_cols[i % 3]:
            st.page_link(path, label=label, width="stretch")
            st.caption(desc)
