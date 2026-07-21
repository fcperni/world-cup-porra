"""Calendario y Resultados — consulta sencilla de todos los partidos y sus resultados.

Los resultados se actualizan AUTOMÁTICAMENTE desde ESPN (Wikipedia de reserva) al
abrir cualquier página (ver ``ui_common.get_results``); no hay que introducir nada
a mano.
"""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    from datetime import date

    import analytics
    from porra.euro2028 import prettify
    from porra.flags import flag_img
    from porra.models import Phase
    from porra.tournament import resolved_match_teams
    from ui_common import PHASE_LABELS, configure_page, get_data, get_live, get_results

    configure_page()
    analytics.track("Calendario y Resultados")
    st.title("📅 Calendario y Resultados")

    data = get_data()

    _WD = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    _MO = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
           7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}

    def fmt_day(d: date) -> str:
        return f"{_WD[d.weekday()]} {d.day} {_MO[d.month]}"

    def tag(m) -> str:
        if m.phase is Phase.GROUPS:
            return f"Grupo {m.group} · {m.matchday}"
        return PHASE_LABELS[m.phase]

    def names(m, teams):
        """(nombre_local, nombre_visitante, es_placeholder) para el partido."""
        if m.phase is Phase.GROUPS:
            # en grupos son selecciones reales; en un torneo sin sorteo (Euro 2028)
            # son ranuras ("A1") que tratamos como placeholder (sin bandera).
            ph = data.team_by_name(m.home) is None
            return m.home, m.away, ph
        ht, at = teams[m.number]
        h = ht.name if ht else data.bracket.get(m.number, (m.home, m.away))[0]
        a = at.name if at else data.bracket.get(m.number, (m.home, m.away))[1]
        return h, a, (ht is None or at is None)

    def team_html(name: str, side: str, placeholder: bool) -> str:
        cls = f"fx-team {side}" + (" ph" if placeholder else "")
        fl = "" if placeholder else flag_img(name, height=15)
        chip = f'<span class="fl">{fl}</span>' if fl else ""
        heart = " 💜" if name == "Portugal" else ""
        label = prettify(name) if placeholder else name
        nm = f'<span class="nm">{label}{heart}</span>'
        inner = f"{nm} {chip}" if side == "home" else f"{chip} {nm}"
        return f'<div class="{cls}">{inner}</div>'

    def score_html(m, results, live, teams) -> str:
        lm = live.get(m.number)
        if lm is not None:  # partido en juego: marcador provisional, no puntúa
            clk = f'<span class="clk">{lm.clock}</span>' if lm.clock else ""
            return (f'<div class="fx-score live"><span class="sc-now">'
                    f'<span class="livedot"></span>{lm.home_goals}-{lm.away_goals}</span>'
                    f'{clk}</div>')
        g = results.goals(m.number)
        if g is None:
            when = m.date.strftime("%H:%M") if m.date else "vs"
            return f'<div class="fx-score pending">{when}</div>'
        extra = ""
        if m.phase.is_knockout and g[0] == g[1] and m.number in results.ko_winners:
            side = results.ko_winners[m.number]
            h, a, _ = names(m, teams)
            extra = f'<span class="pen">pen {flag_img(h if side=="home" else a, height=9)}</span>'
        return f'<div class="fx-score played">{g[0]}-{g[1]}{extra}</div>'

    # ----------------------------------------------------------------- filtros
    c1, c2 = st.columns([3, 1])
    choice = c1.radio("Fase", ["Todas", "Grupos", "Eliminatorias"], horizontal=True, label_visibility="collapsed")
    estado = c2.radio("Estado", ["Todos", "Solo jugados", "Solo por jugar"],
                      horizontal=False, label_visibility="collapsed")

    # Si hay partidos en juego al cargar, el bloque de partidos se autorrefresca.
    live_at_load = get_live(get_results())
    refresh_every = 30 if live_at_load else None

    @st.fragment(run_every=refresh_every)
    def render_matches():
        results = get_results()            # re-sincroniza (incorpora marcadores finales)
        teams = resolved_match_teams(data, results)
        live = get_live(results)           # marcadores en directo, frescos (caché 30 s)

        if live:
            n = len(live)
            st.markdown(
                f'<div class="live-banner"><span class="livedot"></span>'
                f'<b>{n}</b> partido{"s" if n > 1 else ""} en juego · marcador en directo · '
                f'los puntos se calcularán al finalizar</div>',
                unsafe_allow_html=True,
            )

        matches = sorted(data.matches, key=lambda m: ((m.date.timestamp() if m.date else 0), m.number))
        if choice == "Grupos":
            matches = [m for m in matches if m.phase is Phase.GROUPS]
        elif choice == "Eliminatorias":
            matches = [m for m in matches if m.phase.is_knockout]
        if estado == "Solo jugados":
            matches = [m for m in matches if results.has(m.number)]
        elif estado == "Solo por jugar":
            matches = [m for m in matches if not results.has(m.number)]

        if not matches:
            st.info("No hay partidos que mostrar con este filtro.")
            return

        html = ['<div class="fx">']
        current_day = None
        for m in matches:
            d = m.date.date() if m.date else None
            if d != current_day:
                current_day = d
                html.append(f'<div class="fx-day">{fmt_day(d) if d else "Por determinar"}</div>')
            h, a, ph = names(m, teams)
            esp = " esp" if "España" in (h, a) else ""
            liv = " live" if m.number in live else ""
            city, stadium = m.city, m.stadium
            venue = ""
            if city and stadium:
                venue = f'<div class="fx-venue">📍 {city} · {stadium}</div>'
            html.append(
                f'<a class="fx-row{esp}{liv}" href="Predicciones_del_partido?match={m.number}" '
                f'target="_self" title="Ver las predicciones de este partido">'
                f'<div class="fx-tag">{tag(m)}</div>'
                f'{team_html(h, "home", ph)}'
                f'{score_html(m, results, live, teams)}'
                f'{team_html(a, "away", ph)}'
                f'{venue}'
                "</a>"
            )
        html.append("</div>")
        st.markdown("".join(html), unsafe_allow_html=True)

        played = sum(1 for m in matches if results.has(m.number))
        nota = " · se actualiza solo cada 30 s" if live else ""
        extra = (" Pincha en cualquier partido para ver todas las predicciones."
                 if data.players else "")
        st.caption(f"{played} de {len(matches)} partidos jugados{nota}.{extra}")

    render_matches()
