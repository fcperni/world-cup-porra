"""Pa porra la mía — porra multi-competición (Mundiales y Eurocopas).

App Streamlit que analiza la porra de una competición reproduciendo su puntuación
en Python y actualiza automáticamente los resultados por scraping (ESPN, con
Wikipedia de reserva). La página de inicio es un **selector de competición**;
el resto de páginas trabajan sobre la elegida.

Ejecutar con:  ``streamlit run app.py``
"""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    import random

    import analytics
    from porra.competitions import COMPETITION_ORDER, get_competition
    from porra.models import Phase
    from porra.scoring import scoreboard
    from porra.tournament import group_phase_complete
    from ui_common import (
        STATUS_LABELS, active_competition, configure_page, fmt, get_data, get_results,
        has_selection, proper_name, set_competition,
    )

    configure_page()

    # ================================================================= PORTADA
    # Sin competición elegida: tarjetas de selección (Mundiales y Eurocopas).
    if not has_selection():
        analytics.track("Portada")
        st.markdown(
            """
            <div class="hero">
              <div class="hero-kicker">Porra multi-competición</div>
              <h1 class="hero-title">Pa porra <span class="acc">la mía</span></h1>
              <div class="hero-sub">Elige una competición para ver su porra: puntuación al
              milímetro, calendario, grupos, brackets y cuadro de honor.</div>
              <div class="hero-rule"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="section-label">Competiciones</div>', unsafe_allow_html=True)

        cols = st.columns(len(COMPETITION_ORDER))
        for col, comp_id in zip(cols, COMPETITION_ORDER):
            comp = get_competition(comp_id)
            with col:
                with st.container(border=True):
                    st.markdown(
                        f"<div style='font-size:2.6rem;line-height:1'>{comp.emoji}</div>"
                        f"<h3 style='margin:.3rem 0 .1rem'>{comp.name}</h3>"
                        f"<div style='opacity:.7;font-size:.85rem'>{comp.host_label}</div>"
                        f"<div style='margin:.5rem 0;font-size:.8rem;text-transform:uppercase;"
                        f"letter-spacing:.08em;opacity:.85'>· {STATUS_LABELS.get(comp.status, '')} ·</div>",
                        unsafe_allow_html=True,
                    )
                    cta = "Ver la porra" if comp.is_open else "Ver el calendario"
                    if st.button(cta, key=f"pick_{comp_id}", width="stretch"):
                        set_competition(comp_id)
                        st.rerun()
        st.caption("Podrás cambiar de competición en cualquier momento desde la barra lateral.")
        st.stop()

    # =============================================================== DASHBOARD
    comp = active_competition()
    analytics.track("Inicio", comp.id)

    data = get_data()
    results = get_results()

    fmt_ = data.format
    n_group_matches = fmt_.n_groups * fmt_.matches_per_group
    n_ko_matches = fmt_.total_matches - n_group_matches

    played = sum(1 for m in data.matches if m.phase is Phase.GROUPS and results.has(m.number))
    total_ko = sum(1 for m in data.matches if m.phase.is_knockout and results.has(m.number))
    complete = group_phase_complete(data, results)

    # ----------------------------------------------------------------- hero
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">{comp.hero_kicker}</div>
          <h1 class="hero-title">Pa porra <span class="acc">la mía</span></h1>
          <div class="hero-sub">La porra al milímetro, calcada de la plantilla original:
          1X2, diferencia, resultado exacto, posiciones, brackets y cuadro de honor.</div>
          <div class="hero-rule"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ----------------------------------------------------- competición sin porra aún
    if not data.players:
        st.markdown(
            f"""
            <div class="empty-card">
              <div class="big">La porra de la {comp.name} está en camino</div>
              <div class="sub">Todavía no hay equipos sorteados ni participantes. De momento
              puedes explorar el <b>calendario y las sedes</b> y el <b>cuadro</b> del torneo.
              La {comp.name} arranca el {comp.start_label}.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Equipos", fmt_.n_groups * fmt_.teams_per_group)
        c2.metric("Grupos", fmt_.n_groups)
        c3.metric("Partidos", fmt_.total_matches)
        st.markdown('<div class="section-label">Explora el torneo</div>', unsafe_allow_html=True)
        nav_cols = st.columns(2)
        with nav_cols[0]:
            st.page_link("pages/1_Calendario_y_Resultados.py",
                         label="📅 Calendario y sedes", width="stretch")
            st.caption("Fechas, sedes y cruces del torneo.")
        with nav_cols[1]:
            st.page_link("pages/5_Grupos_y_Brackets.py",
                         label="📊 Grupos y Brackets", width="stretch")
            st.caption("Los grupos y el cuadro de eliminatorias.")
        st.stop()

    # ----------------------------------------------------------------- marcador de estado
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Participantes", len(data.players))
    c2.metric("Partidos Fase de Grupos", f"{played} / {n_group_matches}")
    c3.metric("Eliminatorias", f"{total_ko} / {n_ko_matches}")
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
            f"""
            <div class="empty-card">
              <div class="big">El balón aún no rueda</div>
              <div class="sub">Los resultados se cargan <b>automáticamente</b> desde ESPN y
              Wikipedia; la clasificación cobrará vida en cuanto se juegue el primer partido.
              La {comp.name} arranca el {comp.start_label}.</div>
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
         "Las predicciones de los participantes para un mismo partido, de un vistazo."),
        ("pages/3_Clasificación.py", "🏆 Clasificación",
         "Ranking de participantes con desglose por categoría."),
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
