"""Estadísticas — KPIs agregados de la porra (predicciones y aciertos)."""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    import analytics
    from porra import stats
    from porra.flags import flag_img
    from porra.models import Phase
    from ui_common import configure_page, get_data, get_results, proper_name

    configure_page()
    analytics.track("Estadísticas")
    st.title("📈 Estadísticas")

    data = get_data()
    results = get_results()
    N = len(data.players)

    def kpi_team(label: str, counter) -> str:
        if not counter:
            return f'<div class="kpi"><div class="lbl">{label}</div><div class="team">—</div></div>'
        team, votes = counter.most_common(1)[0]
        pct = round(votes / N * 100) if N else 0
        return (f'<div class="kpi"><div class="lbl">{label}</div>'
                f'<div class="team">{flag_img(team, 16)}<span>{team}</span></div>'
                f'<div class="val">{votes} de {N} ({pct}%)</div></div>')

    def kpi_player(label: str, counter) -> str:
        if not counter:
            return f'<div class="kpi"><div class="lbl">{label}</div><div class="team">—</div></div>'
        name, votes = counter.most_common(1)[0]
        return (f'<div class="kpi"><div class="lbl">{label}</div>'
                f'<div class="team"><span>{proper_name(name)}</span></div>'
                f'<div class="val">{votes} de {N} votos</div></div>')

    def rank_team(counter, n=6, fmt=lambda v: str(v)) -> str:
        items = []
        for i, (team, v) in enumerate(counter.most_common(n), 1):
            items.append(f'<div class="rank-item"><span class="n">{i}</span>'
                         f'<span class="who">{flag_img(team, 13)}<span>{team}</span></span>'
                         f'<span class="v">{fmt(v)}</span></div>')
        return '<div class="rank-list">' + "".join(items) + "</div>"

    def rank_avg(pairs) -> str:
        items = []
        for i, (team, (avg, _)) in enumerate(pairs, 1):
            items.append(f'<div class="rank-item"><span class="n">{i}</span>'
                         f'<span class="who">{flag_img(team, 13)}<span>{team}</span></span>'
                         f'<span class="v">{avg:.1f}</span></div>')
        return '<div class="rank-list">' + "".join(items) + "</div>"

    def kpi_stat(label: str, big: str, sub: str) -> str:
        return (f'<div class="kpi"><div class="lbl">{label}</div>'
                f'<div class="team"><span>{big}</span></div>'
                f'<div class="val">{sub}</div></div>')

    def rank_names(pairs, fmt=lambda v: str(v)) -> str:
        items = []
        for i, (name, v) in enumerate(pairs, 1):
            items.append(f'<div class="rank-item"><span class="n">{i}</span>'
                         f'<span class="who"><span>{proper_name(name)}</span></span>'
                         f'<span class="v">{fmt(v)}</span></div>')
        return '<div class="rank-list">' + "".join(items) + "</div>"

    def rank_matches(splits, fmt) -> str:
        items = []
        for i, s in enumerate(splits, 1):
            m = data.match_by_number(s.match_number)
            items.append(f'<div class="rank-item"><span class="n">{i}</span>'
                         f'<span class="who">{flag_img(m.home, 13)}<span>{m.home} · {m.away}</span></span>'
                         f'<span class="v">{fmt(s)}</span></div>')
        return '<div class="rank-list">' + "".join(items) + "</div>"

    # ------------------------------------------------------------ favoritos
    st.markdown('<div class="section-label">Favoritos de la porra</div>', unsafe_allow_html=True)
    champ = stats.champion_votes(data)
    fin = stats.finalist_votes(data)
    boot = stats.golden_boot_votes(data)
    st.markdown(
        '<div class="kpi-grid">'
        + kpi_team("Favorito a campeón", champ)
        + kpi_team("Finalista más repetido", fin)
        + kpi_player("Bota de Oro favorita", boot)
        + "</div>",
        unsafe_allow_html=True,
    )
    if champ:
        st.caption(f"{len(champ)} selecciones distintas reciben algún voto a campeón.")
        with st.expander("Reparto de votos a campeón"):
            st.markdown(rank_team(champ, n=8, fmt=lambda v: f"{v} ★"), unsafe_allow_html=True)

    # ------------------------------------------------------------ España
    st.markdown('<div class="section-label">España según la porra</div>', unsafe_allow_html=True)
    avg_pos = stats.team_group_position_avg(data, "España")
    pct_clasif = stats.pct_players(
        data, lambda p: any(t == "España" and pos <= 2 for (g, pos), t in p.group_positions.items()))
    pct_final = stats.pct_players(data, lambda p: "España" in p.qualified.get(Phase.FINAL, []))
    pct_champ = stats.pct_players(data, lambda p: p.honor.get("campeon") == "España")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Posición media (Grupo H)", f"{avg_pos:.1f}º" if avg_pos else "—")
    c2.metric("La clasifican", f"{round(pct_clasif * 100)}%")
    c3.metric("Llega a la final", f"{round(pct_final * 100)}%")
    c4.metric("La ven campeona", f"{round(pct_champ * 100)}%")

    # ------------------------------------------------------------ clasificados más votados
    st.markdown('<div class="section-label">Quién pasa de ronda (según la porra)</div>', unsafe_allow_html=True)
    colA, colB = st.columns(2)
    with colA:
        st.caption("Más votados para llegar a **semifinales**")
        st.markdown(rank_team(stats.qualified_votes(data, Phase.SF), n=6, fmt=lambda v: f"{v}"),
                    unsafe_allow_html=True)
    with colB:
        st.caption("Más votados para llegar a **cuartos**")
        st.markdown(rank_team(stats.qualified_votes(data, Phase.QF), n=6, fmt=lambda v: f"{v}"),
                    unsafe_allow_html=True)

    # ------------------------------------------------------------ aciertos (requiere resultados)
    st.markdown('<div class="section-label">Aciertos por selección</div>', unsafe_allow_html=True)
    if stats.group_matches_played(data, results) == 0:
        st.info("Disponible cuando se jueguen partidos de la fase de grupos.", icon="🗓️")
    else:
        acc = stats.team_accuracy(data, results)
        ranked = sorted(acc.items(), key=lambda kv: kv[1][0], reverse=True)
        colA, colB = st.columns(2)
        with colA:
            st.caption("Mejor pronosticadas (puntos medios)")
            st.markdown(rank_avg(ranked[:6]), unsafe_allow_html=True)
        with colB:
            st.caption("Peor pronosticadas")
            st.markdown(rank_avg(ranked[-6:][::-1]), unsafe_allow_html=True)

        ma = stats.match_accuracy(data, results)
        if ma:
            bn = max(ma, key=ma.get)
            wn = min(ma, key=ma.get)
            mb, mw = data.match_by_number(bn), data.match_by_number(wn)
            st.markdown('<div class="section-label">Partidos</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("Partido más acertado", f"{mb.home} - {mb.away}", f"{ma[bn]:.1f} pts de media")
            c2.metric("Partido más fallado", f"{mw.home} - {mw.away}", f"{ma[wn]:.1f} pts de media")

    # ------------------------------------------------------------ consenso (siempre disponible)
    # A diferencia de los aciertos, esto solo depende de las predicciones, así que
    # está disponible desde el primer día (antes incluso de que ruede el balón).
    st.markdown('<div class="section-label">El consenso de la porra</div>', unsafe_allow_html=True)
    splits = [s for s in stats.match_sign_splits(data).values() if s.total]
    if not splits:
        st.caption("Sin pronósticos de grupos registrados.")
    else:
        n_unan = sum(1 for s in splits if s.is_unanimous)
        score_c = stats.popular_scorelines(data)
        (sh, sa), sc_votes = score_c.most_common(1)[0]
        prof = stats.prediction_profile(data)
        st.markdown(
            '<div class="kpi-grid">'
            + kpi_stat("Partidos de grupos con unanimidad", str(n_unan), f"de {len(splits)} partidos")
            + kpi_stat("Marcador más pronosticado", f"{sh}-{sa}", f"{sc_votes} pronósticos")
            + kpi_stat("Goles por partido (media prevista)", f"{prof['avg_goals']:.1f}",
                       f"{round(prof['pct_draws'] * 100)}% son empates")
            + "</div>",
            unsafe_allow_html=True,
        )
        st.caption("Reparto de votos en formato **local · empate · visitante** (1·X·2).")
        most_div = sorted(splits, key=lambda s: (-s.dissenters, s.match_number))[:6]
        most_clear = sorted(splits, key=lambda s: (s.dissenters, s.match_number))[:6]
        colA, colB = st.columns(2)
        with colA:
            st.caption("Partidos más **reñidos**")
            st.markdown(
                rank_matches(most_div, lambda s: f"{s.counts['1']}·{s.counts['X']}·{s.counts['2']}"),
                unsafe_allow_html=True)
        with colB:
            st.caption("Partidos más **claros**")
            st.markdown(
                rank_matches(most_clear,
                             lambda s: f"{s.counts['1']}·{s.counts['X']}·{s.counts['2']}"),
                unsafe_allow_html=True)
        with st.expander("Marcadores más pronosticados"):
            st.markdown(
                rank_names([(f"{h}-{a}", v) for (h, a), v in score_c.most_common(8)],
                           fmt=lambda v: f"{v}"),
                unsafe_allow_html=True)

    # ------------------------------------------------------------ perfil de los participantes
    st.markdown('<div class="section-label">El perfil de los participantes</div>', unsafe_allow_html=True)
    dissent = stats.player_dissent(data)
    if not dissent or all(v == 0 for v in dissent.values()):
        st.caption("Sin datos suficientes de pronósticos de grupos.")
    else:
        ranked = dissent.most_common()
        colA, colB = st.columns(2)
        with colA:
            st.caption("Quién más se **moja** (pronósticos a contracorriente)")
            st.markdown(rank_names(ranked[:6]), unsafe_allow_html=True)
        with colB:
            st.caption("Quién va más con la **corriente**")
            st.markdown(rank_names(ranked[-6:][::-1]), unsafe_allow_html=True)
        st.caption("«A contracorriente» = veces que el jugador se aparta del signo "
                   "mayoritario en los 72 partidos de grupos.")
