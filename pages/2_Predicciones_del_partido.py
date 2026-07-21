"""Predicciones del partido — todas las predicciones de los 19 para un mismo partido.

Pensada para consultarse mientras se disputa un partido (varios mirando a la vez):
se llega pinchando un partido en **Calendario y Resultados** (que pasa el nº de
partido por la URL, ``?match=N``) o eligiéndolo en el desplegable. Muestra el
pronóstico de cada participante y, si el partido ya se jugó, los puntos logrados.
"""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    from datetime import date

    import analytics
    from porra import stats
    from porra.flags import flag_img
    from porra.models import Phase
    from porra.scoring import score_match
    from porra.tournament import resolved_match_teams
    from ui_common import (PHASE_LABELS, configure_page, fmt, get_data, get_live,
                           get_results, proper_name)

    configure_page()
    st.title("🎯 Predicciones del partido")

    data = get_data()
    results = get_results()

    _WD = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    _MO = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
           7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}
    _SCLASS = {"1": "s1", "X": "sx", "2": "s2"}

    def sign_chip(sign: str) -> str:
        return f'<span class="sgn {_SCLASS[sign]}">{sign}</span>'

    def m_names(m, teams):
        """(local, visitante) reales o, en KO sin resolver, los placeholders."""
        if m.phase is Phase.GROUPS:
            return m.home, m.away
        ht, at = teams[m.number]
        h = ht.name if ht else data.bracket.get(m.number, (m.home, m.away))[0]
        a = at.name if at else data.bracket.get(m.number, (m.home, m.away))[1]
        return h, a

    def m_tag(m) -> str:
        if m.phase is Phase.GROUPS:
            return f"Grupo {m.group} · {m.matchday}"
        return PHASE_LABELS[m.phase]

    def long_day(m) -> str:
        if not m.date:
            return "fecha por determinar"
        d = m.date
        return f"{_WD[d.weekday()]} {d.day} {_MO[d.month]} · {d:%H:%M}"

    def short_day(m) -> str:
        if not m.date:
            return "s/f"
        return f"{m.date.day} {_MO[m.date.month]}"

    # ----------------------------------------------------------- selección de partido
    matches = sorted(data.matches, key=lambda m: ((m.date.timestamp() if m.date else 0), m.number))
    by_num = {m.number: m for m in matches}
    options = [m.number for m in matches]
    teams_for_label = resolved_match_teams(data, results)
    live_at_load = get_live(results)

    def label(num: int) -> str:
        m = by_num[num]
        h, a = m_names(m, teams_for_label)
        flag = " 🔴" if num in live_at_load else ""
        return f"{m_tag(m)} · {h} – {a} · {short_day(m)}{flag}"

    # Partido por defecto: el que viene en la URL (al pinchar en el calendario); si no,
    # uno en juego ahora mismo; si no, el próximo sin resultado, o el último.
    raw = st.query_params.get("match")
    default_num = int(raw) if raw and raw.isdigit() and int(raw) in by_num else None
    if default_num is None:
        if live_at_load:
            default_num = sorted(live_at_load)[0]
        else:
            upcoming = [m.number for m in matches if not results.has(m.number)]
            default_num = upcoming[0] if upcoming else options[-1]

    selected = st.selectbox("Partido", options, index=options.index(default_num),
                            format_func=label, placeholder="Escribe para buscar…")
    # Mantén la URL en sincronía (así el enlace es compartible y persiste al recargar).
    if str(selected) != st.query_params.get("match"):
        st.query_params["match"] = str(selected)

    analytics.track("Predicciones del partido", str(selected))

    # El detalle se autorrefresca solo si el partido elegido está en juego al cargar.
    refresh_every = 30 if selected in live_at_load else None

    @st.fragment(run_every=refresh_every)
    def render_detail():
        results = get_results()            # re-sincroniza (incorpora el marcador final)
        teams = resolved_match_teams(data, results)
        live = get_live(results)

        m = by_num[selected]
        home, away = m_names(m, teams)
        esp = " esp" if "España" in (home, away) else ""
        lm = live.get(m.number)            # marcador en directo (no puntúa)
        g = results.goals(m.number)
        played = g is not None

        # ------------------------------------------------------- cabecera del partido
        extra_html = ""
        if lm is not None:  # en juego: marcador provisional + aviso de que no puntúa aún
            sc_html = (f'<span class="prd-sc live"><span class="livedot"></span>'
                       f'{lm.home_goals}-{lm.away_goals}</span>')
            clk = f" · {lm.clock}" if lm.clock else ""
            extra_html = (f'<div class="prd-live"><span class="livedot"></span>'
                          f'EN JUEGO{clk} · los puntos se calcularán al finalizar</div>')
        elif played:
            sc_html = f'<span class="prd-sc played">{g[0]}-{g[1]}</span>'
            if m.phase.is_knockout and g[0] == g[1] and m.number in results.ko_winners:
                side = results.ko_winners[m.number]
                winner = home if side == "home" else away
                extra_html = (f'<div class="prd-pen">Pasa en los penaltis: '
                              f'{flag_img(winner, 12)} {winner}</div>')
        else:
            when = m.date.strftime("%H:%M") if m.date else "vs"
            sc_html = f'<span class="prd-sc pending">{when}</span>'

        city, stadium = m.city, m.stadium
        venue_html = ""
        if city and stadium:
            venue_html = f'<div class="prd-venue">📍 {city} · {stadium}</div>'

        st.markdown(
            f'<div class="prd-hd{esp}">'
            f'<div class="prd-tag">{m_tag(m)} · {long_day(m)}</div>'
            f'<div class="prd-match">'
            f'<span class="t home"><span class="nm">{home}</span>{flag_img(home, 22)}</span>'
            f'{sc_html}'
            f'<span class="t away">{flag_img(away, 22)}<span class="nm">{away}</span></span>'
            f'</div>{venue_html}{extra_html}</div>',
            unsafe_allow_html=True,
        )

        # =========================================================== fase de grupos
        if m.phase is Phase.GROUPS:
            split = stats.match_sign_splits(data)[m.number]
            if split.total:
                segs = "".join(
                    f'<span class="seg {_SCLASS[sg]}" '
                    f'style="width:{split.counts[sg] / split.total * 100:.4f}%"></span>'
                    for sg in stats.SIGNS if split.counts[sg])
                outc = {"1": f"gana {home}", "X": "empate", "2": f"gana {away}"}
                leg = " · ".join(f'{sign_chip(sg)} {outc[sg]} ({split.counts[sg]})'
                                 for sg in stats.SIGNS if split.counts[sg])
                st.markdown(f'<div class="cz-bar">{segs}</div>'
                            f'<div class="prd-legend">{leg}</div>', unsafe_allow_html=True)

            def grp_pts(pred):
                if not (played and pred and pred.valid):
                    return None
                return score_match(data.rules, Phase.GROUPS, m.bonus, pred.sign, pred.home_goals,
                                   pred.away_goals, results.sign(m.number), g[0], g[1])

            items = []
            for p in data.players:
                pred = p.group_matches.get(m.number)
                items.append((p.name, pred, grp_pts(pred)))

            if played:
                items.sort(key=lambda it: (-(it[2] or 0), proper_name(it[0]).lower()))
            else:
                # 1X2 → resultado (marcador pronosticado) → alfabético
                def grp_key(it):
                    name, pred, _ = it
                    if pred and pred.valid:
                        return (stats.SIGNS.index(pred.sign), pred.home_goals,
                                pred.away_goals, proper_name(name).lower())
                    return (9, 0, 0, proper_name(name).lower())
                items.sort(key=grp_key)

            rows = []
            for name, pred, pts in items:
                if pred and pred.valid:
                    pron = f'{sign_chip(pred.sign)}<span class="mk">{pred.home_goals}-{pred.away_goals}</span>'
                    cls = ""
                    if played:
                        if pts and pts > 0:
                            cls = " win"
                        elif pred.sign != results.sign(m.number):
                            cls = " miss"
                    ptd = fmt(pts) if pts is not None else "—"
                else:
                    pron, cls, ptd = '<span class="dash">sin pronóstico</span>', " none", "—"
                rows.append(f'<tr class="{cls.strip()}"><td class="who">{proper_name(name)}</td>'
                            f'<td class="pr">{pron}</td><td class="pt">{ptd}</td></tr>')

            head_pts = "<th class='r'>Puntos</th>" if played else "<th class='r'></th>"
            st.markdown(
                '<table class="prd"><thead><tr><th>Jugador</th><th>Pronóstico</th>'
                f'{head_pts}</tr></thead><tbody>' + "".join(rows) + '</tbody></table>',
                unsafe_allow_html=True,
            )

        # =========================================================== eliminatorias
        else:
            ht, at = teams[m.number]
            real_pair = {ht.name, at.name} if ht and at else None

            def ko_pts(pred):
                if not (played and pred and pred.home_team and pred.away_team and pred.sign is not None):
                    return None
                if not real_pair or {pred.home_team, pred.away_team} != real_pair:
                    return 0.0 if real_pair else None
                if ht.name == pred.home_team:  # mismo orden que el jugador
                    a_sign, a_h, a_a = results.sign(m.number), g[0], g[1]
                else:  # orden invertido: trasponer el resultado real
                    a_h, a_a = g[1], g[0]
                    a_sign = "1" if a_h > a_a else "2" if a_h < a_a else "X"
                return score_match(data.rules, m.phase, m.bonus, pred.sign, pred.home_goals,
                                   pred.away_goals, a_sign, a_h, a_a)

            items = []
            for p in data.players:
                pred = p.ko_matches.get(m.number)
                hit = bool(real_pair and pred and pred.home_team
                           and {pred.home_team, pred.away_team} == real_pair)
                items.append((p.name, pred, ko_pts(pred), hit))

            if played:
                items.sort(key=lambda it: (-(it[2] or 0), not it[3], proper_name(it[0]).lower()))
            else:
                # 1X2 → resultado (marcador pronosticado) → alfabético
                def ko_key(it):
                    name, pred, _, _ = it
                    if pred and pred.home_team and pred.away_team and pred.sign is not None:
                        return (stats.SIGNS.index(pred.sign), pred.home_goals,
                                pred.away_goals, proper_name(name).lower())
                    return (9, 0, 0, proper_name(name).lower())
                items.sort(key=ko_key)

            rows = []
            for name, pred, pts, hit in items:
                if pred and pred.home_team and pred.away_team:
                    res = (f'{sign_chip(pred.sign)}<span class="mk">{pred.home_goals}-{pred.away_goals}</span>'
                           if pred.sign is not None else "")
                    badge = '<span class="ok">✓ cruce</span>' if hit else ""
                    pron = (f'{flag_img(pred.home_team, 13)}<span class="tn">{pred.home_team}</span>'
                            f' {res} '
                            f'{flag_img(pred.away_team, 13)}<span class="tn">{pred.away_team}</span>{badge}')
                    cls = " win" if (played and pts and pts > 0) else (" miss" if played and not hit else "")
                    ptd = fmt(pts) if pts is not None else "—"
                else:
                    pron, cls, ptd = '<span class="dash">sin pronóstico</span>', " none", "—"
                rows.append(f'<tr class="{cls.strip()}"><td class="who">{proper_name(name)}</td>'
                            f'<td class="pr">{pron}</td><td class="pt">{ptd}</td></tr>')

            if real_pair:
                nailed = sum(1 for _, _, _, hit in items if hit)
                st.caption(f"Cruce real: {ht.name} – {at.name}. "
                           f"{nailed} de {len([p for p in data.players if p.ko_matches.get(m.number)])} "
                           "clavaron la pareja.")
            else:
                st.caption("Cruce aún sin definir: cada jugador pronosticó **qué dos selecciones** "
                           "se enfrentan aquí. Se puntúa acertando la pareja (en cualquier orden).")

            head_pts = "<th class='r'>Puntos</th>" if played else "<th class='r'></th>"
            st.markdown(
                '<table class="prd"><thead><tr><th>Jugador</th><th>Pronóstico del cruce</th>'
                f'{head_pts}</tr></thead><tbody>' + "".join(rows) + '</tbody></table>',
                unsafe_allow_html=True,
            )

    render_detail()
