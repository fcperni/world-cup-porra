"""Detalle de un participante: predicciones, aciertos y puntos."""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    import pandas as pd

    import analytics
    from porra.flags import flag_img
    from porra.models import KO_ORDER, Phase
    from porra.scoring import HONOR_POINTS_KEY, actual_honor, score_match, score_player
    from porra.tournament import resolved_match_teams
    from ui_common import HONOR_LABELS, PHASE_LABELS, configure_page, fmt, get_data, get_results, proper_name

    TEAM_HONOR = {"campeon", "subcampeon", "tercero"}  # categorías cuyo valor es una selección

    configure_page()
    st.title("👤 Detalle por jugador")

    data = get_data()
    results = get_results()

    player_names = sorted((p.name for p in data.players), key=lambda n: proper_name(n).lower())
    selected = st.selectbox(
        "Jugador", player_names, format_func=proper_name,
        placeholder="Escribe para buscar…",
    )
    player = next(p for p in data.players if p.name == selected)
    analytics.track("Jugador", player.name)

    teams = resolved_match_teams(data, results)
    score = score_player(data, results, player, resolved_teams=teams)
    st.metric("Puntos totales", fmt(score.total))

    # desglose por categoría con puntos
    active = {c: v for c, v in score.categories.items() if v}
    if active:
        cols = st.columns(min(5, len(active)))
        for i, (c, v) in enumerate(active.items()):
            cols[i % len(cols)].metric(c, fmt(v))

    tab_grupos, tab_ko, tab_honor = st.tabs(["Fase de grupos", "Eliminatorias", "Cuadro de honor"])

    with tab_grupos:
        gm = sorted([m for m in data.matches if m.phase is Phase.GROUPS], key=lambda m: (m.group, m.number))
        rows = []
        for m in gm:
            pred = player.group_matches.get(m.number)
            pts = None
            if pred and pred.valid and results.has(m.number):
                ah, aa = results.goals(m.number)
                pts = score_match(data.rules, Phase.GROUPS, m.bonus, pred.sign, pred.home_goals,
                                  pred.away_goals, results.sign(m.number), ah, aa)
            rows.append({"Grupo": m.group, "Partido": f"{m.home}  -  {m.away}",
                         "Predicción": pred.raw if pred and pred.valid else "—",
                         "Resultado": results.result_string(m.number) or "—",
                         "Bonus": f"x{m.bonus}" if m.bonus > 1 else "",
                         "Puntos": round(pts, 1) if pts is not None else None})
        df = pd.DataFrame(rows)
        gsel = st.multiselect("Filtrar por grupo", sorted(df["Grupo"].unique()))
        if gsel:
            df = df[df["Grupo"].isin(gsel)]
        st.dataframe(df, hide_index=True, width="stretch",
                     column_config={"Puntos": st.column_config.NumberColumn(format="%.1f")})

    with tab_ko:
        # partidos reales de cada ronda con resultado y ambas selecciones resueltas
        actual_by_phase: dict = {ph: [] for ph in KO_ORDER}
        for m in data.matches:
            if m.phase.is_knockout and results.has(m.number):
                ht, at = teams[m.number]
                if ht and at:
                    actual_by_phase[m.phase].append((m, ht.name, at.name))

        rows = []
        for phase in KO_ORDER:
            preds = [player.ko_matches[n] for n in sorted(player.ko_matches)
                     if (mo := data.match_by_number(n)) and mo.phase is phase]
            for pred in preds:
                real = "—"
                pts = None
                # se acierta el partido si la pareja predicha se enfrenta de verdad
                # en esta ronda (en cualquier orden); el marcador se evalúa en el
                # orden del jugador. Reproduce score_ko_matches.
                if pred.home_team and pred.away_team and pred.sign is not None:
                    pair = {pred.home_team, pred.away_team}
                    for m, ah_name, aa_name in actual_by_phase[phase]:
                        if {ah_name, aa_name} != pair:
                            continue
                        agh, aga = results.goals(m.number)
                        real = f"{ah_name} {agh}-{aga} {aa_name}"
                        if ah_name == pred.home_team:  # mismo orden que el jugador
                            a_sign, a_h, a_a = results.sign(m.number), agh, aga
                        else:  # orden invertido: trasponer el resultado real
                            a_h, a_a = aga, agh
                            a_sign = "1" if a_h > a_a else "2" if a_h < a_a else "X"
                        pts = score_match(data.rules, phase, m.bonus, pred.sign,
                                          pred.home_goals, pred.away_goals, a_sign, a_h, a_a)
                        break
                    # la ronda ya tiene resultados pero la pareja no se dio -> 0
                    if pts is None and actual_by_phase[phase]:
                        pts = 0.0
                rows.append({
                    "Ronda": PHASE_LABELS[phase],
                    "Tu cruce": (f"{pred.home_team}  -  {pred.away_team}"
                                 if pred.home_team else "—"),
                    "Tu resultado": (f"{pred.sign}|{pred.home_goals}-{pred.away_goals}"
                                     if pred.sign else "—"),
                    "Cruce real": real,
                    "Puntos": round(pts, 1) if pts is not None else None,
                })
        st.caption("Aciertas un partido si la **pareja** que pronosticaste se enfrenta "
                   "realmente en esa ronda (en cualquier orden); el marcador se valora en "
                   "tu orden. Los puntos por **equipos clasificados** se muestran arriba.")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={"Puntos": st.column_config.NumberColumn(format="%.1f")})

    with tab_honor:
        honor_filled = {k: v for k, v in player.honor.items() if v}
        if honor_filled:
            honor_actual = actual_honor(data, results, teams)

            def _honor_cell(key: str, value: str) -> str:
                if key in TEAM_HONOR:  # selección: bandera + nombre oficial
                    return f'{flag_img(value, 14)}<span class="nm">{value}</span>'
                return f'<span class="nm">{proper_name(value)}</span>'  # jugador

            rows = []
            for k, v in honor_filled.items():
                cat = HONOR_LABELS.get(k, k)
                actual = honor_actual.get(k)
                real = _honor_cell(k, actual) if actual else "—"
                if actual is None:          # aún no se conoce el real
                    pts = "—"
                elif v == actual:           # acierto
                    pts = fmt(data.rules.points.get((HONOR_POINTS_KEY, k), 0.0))
                else:                       # fallo
                    pts = "0"
                rows.append(
                    f'<tr><td class="cat">{cat}</td><td class="val">{_honor_cell(k, v)}</td>'
                    f'<td class="val">{real}</td><td class="pts">{pts}</td></tr>'
                )
            st.markdown(
                '<table class="honor"><thead><tr><th>Categoría</th><th>Pronóstico</th>'
                '<th>Real</th><th>Puntos</th></tr></thead>'
                '<tbody>' + "".join(rows) + "</tbody></table>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Sin pronósticos de cuadro de honor.")
