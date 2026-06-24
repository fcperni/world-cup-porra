"""Detalle de un participante: predicciones, aciertos y puntos."""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    import pandas as pd

    import analytics
    from porra.flags import flag_img
    from porra.models import KO_ORDER, Phase
    from porra.scoring import (HONOR_POINTS_KEY, actual_honor, actual_qualified_teams,
                               score_match, score_player)
    from porra.tournament import group_positions, resolved_match_teams
    from ui_common import HONOR_LABELS, PHASE_LABELS, configure_page, fmt, get_data, get_results, proper_name

    TEAM_HONOR = {"campeon", "subcampeon", "tercero"}  # categorías cuyo valor es una selección
    POS_LABEL = {1: "1º", 2: "2º", 3: "3º", 4: "4º"}

    PENDING = -1.0  # centinela: los pendientes ordenan por debajo de cualquier punto (>=0)

    def show_points(df: "pd.DataFrame") -> None:
        """Pinta una tabla cuya columna ``Puntos`` ordena dejando los pendientes
        siempre por debajo de los 0.

        Streamlit ordena ``st.dataframe`` por el **dato numérico** subyacente, no por
        el texto mostrado. Aprovechándolo: los pendientes se guardan como un centinela
        negativo (así ordenan bajo los 0) y un ``Styler`` los pinta en blanco; el resto
        de números se formatean con :func:`fmt`. Esto evita que los None se mezclen con
        los 0 al ordenar (cosa que pasa si la columna lleva ``NaN`` o es de tipo texto).
        """
        df = df.copy()
        fmts: dict = {}
        if "Puntos" in df:
            df["Puntos"] = pd.to_numeric(df["Puntos"], errors="coerce").fillna(PENDING)
            fmts["Puntos"] = lambda v: "" if v < 0 else fmt(v)
        if "Pts/equipo" in df:
            df["Pts/equipo"] = pd.to_numeric(df["Pts/equipo"], errors="coerce")
            fmts["Pts/equipo"] = lambda v: "" if pd.isna(v) else fmt(v)
        st.dataframe(df.style.format(fmts), hide_index=True, width="stretch")

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
    positions = group_positions(data, results)
    qualified_actual = actual_qualified_teams(data, teams)
    honor_actual = actual_honor(data, results, teams)
    score = score_player(data, results, player, positions=positions, resolved_teams=teams,
                         qualified_actual=qualified_actual, honor_actual=honor_actual)
    # resumen en 2x2: total (resaltado) + las tres grandes áreas de puntos.
    grupos = score.categories["F. Grupos"] + score.categories["Pos. Grupos"]
    honor = score.categories["Cuadro de Honor"]
    elim = score.total - grupos - honor  # todas las categorías de eliminatorias
    cards = [("Puntos totales", score.total, " total"), ("Fase de grupos", grupos, ""),
             ("Eliminatorias", elim, ""), ("Cuadro de honor", honor, "")]
    st.markdown(
        '<div class="pscore">' + "".join(
            f'<div class="card{cls}"><div class="lbl">{lbl}</div>'
            f'<div class="num">{fmt(v)}</div></div>' for lbl, v, cls in cards
        ) + "</div>",
        unsafe_allow_html=True,
    )

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

        # posiciones de grupo: se puntúan solo al cerrar el grupo (6 partidos)
        played: dict[str, int] = {}
        for m in gm:
            if results.has(m.number):
                played[m.group] = played.get(m.group, 0) + 1
        complete = {g for g, n in played.items() if n == 6}
        pos_rows = []
        for (g, pos), predicted in sorted(player.group_positions.items()):
            real_team = positions.get((g, pos))
            pts = real = None
            if g in complete and real_team:
                real = real_team.name
                pts = data.rules.points.get(("group_position", pos), 0.0) if predicted == real else 0.0
            pos_rows.append({"Grupo": g, "Posición": POS_LABEL.get(pos, str(pos)),
                             "Tu pronóstico": predicted or "—", "Real": real or "—",
                             "Puntos": pts})
        pos_df = pd.DataFrame(pos_rows)

        gsel = st.multiselect("Filtrar por grupo", sorted(df["Grupo"].unique()))
        if gsel:
            df = df[df["Grupo"].isin(gsel)]
            pos_df = pos_df[pos_df["Grupo"].isin(gsel)]

        st.markdown("**Partidos**")
        show_points(df)
        st.markdown("**Posiciones de grupo**")
        st.caption("Se puntúan al cerrar el grupo (5 puntos por posición acertada).")
        show_points(pos_df)

    with tab_ko:
        # equipos clasificados: por cada selección que sitúas en una ronda y que
        # realmente la alcanza. Reproduce score_qualified.
        eq_rows = []
        for phase in KO_ORDER:
            predicted = player.qualified.get(phase, [])
            reached = qualified_actual.get(phase, set())
            aciertos = [t for t in predicted if t in reached]
            per = data.rules.points.get((phase, "clasificado"), 0.0)
            eq_rows.append({"Ronda": PHASE_LABELS[phase],
                            "Aciertos": len(aciertos),
                            "Pts/equipo": per,
                            "Puntos": len(aciertos) * per if reached else None})
        st.markdown("**Equipos clasificados**")
        st.caption("Puntos por cada selección que sitúas en una ronda y que realmente la alcanza.")
        show_points(pd.DataFrame(eq_rows))

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
        st.markdown("**Partidos**")
        st.caption("Aciertas un partido si la **pareja** que pronosticaste se enfrenta "
                   "realmente en esa ronda (en cualquier orden); el marcador se valora en tu orden.")
        show_points(pd.DataFrame(rows))

    with tab_honor:
        honor_filled = {k: v for k, v in player.honor.items() if v}
        if honor_filled:
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
                    pts = fmt(0.0)
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
