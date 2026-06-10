"""Detalle de un participante: predicciones, aciertos y puntos."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from porra.flags import with_flag
from porra.models import KO_ORDER, Phase
from porra.scoring import score_match, score_player
from porra.tournament import resolved_match_teams
from ui_common import HONOR_LABELS, PHASE_LABELS, configure_page, fmt, get_data, get_results, proper_name

TEAM_HONOR = {"campeon", "subcampeon", "tercero"}  # claves de honor que son selecciones

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

score = score_player(data, results, player)
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
        rows.append({"Grupo": m.group, "Partido": f"{with_flag(m.home)}  -  {with_flag(m.away)}",
                     "Predicción": pred.raw if pred and pred.valid else "—",
                     "Resultado": results.result_string(m.number) or "—",
                     "Bonus": f"x{m.bonus}" if m.bonus > 1 else "",
                     "Puntos": round(pts, 1) if pts is not None else None})
    df = pd.DataFrame(rows)
    gsel = st.multiselect("Filtrar por grupo", sorted(df["Grupo"].unique()))
    if gsel:
        df = df[df["Grupo"].isin(gsel)]
    st.dataframe(df, hide_index=True, use_container_width=True,
                 column_config={"Puntos": st.column_config.NumberColumn(format="%.1f")})

with tab_ko:
    teams = resolved_match_teams(data, results)
    rows = []
    for phase in KO_ORDER:
        for m in sorted([m for m in data.matches if m.phase is phase], key=lambda m: m.number):
            pred = player.ko_matches.get(m.number)
            ht, at = teams[m.number]
            real = "—"
            if ht and at:
                g = results.goals(m.number)
                real = (f"{with_flag(ht.name)} {g[0]}-{g[1]} {with_flag(at.name)}" if g
                        else f"{with_flag(ht.name)} - {with_flag(at.name)}")
            rows.append({
                "Ronda": PHASE_LABELS[phase],
                "Pronóstico cruce": (f"{with_flag(pred.home_team)} - {with_flag(pred.away_team)}"
                                     if pred and pred.home_team else "—"),
                "Resultado pron.": (f"{pred.sign}|{pred.home_goals}-{pred.away_goals}"
                                    if pred and pred.sign else "—"),
                "Cruce real": real,
            })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

with tab_honor:
    honor_filled = {k: v for k, v in player.honor.items() if v}
    if honor_filled:
        st.table(pd.DataFrame([
            {"Categoría": HONOR_LABELS.get(k, k),
             "Pronóstico": with_flag(v) if k in TEAM_HONOR else v}
            for k, v in honor_filled.items()]))
    else:
        st.caption("Sin pronósticos de cuadro de honor.")
