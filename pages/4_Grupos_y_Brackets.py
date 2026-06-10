"""Clasificación de cada grupo y (próximamente) cuadro de eliminatorias."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
import streamlit as st

from porra.flags import flag_img, flag_url
from porra.models import Phase
from porra.tournament import compute_group_standings, resolved_match_teams
from ui_common import configure_page, get_data, get_results

configure_page()
st.title("📊 Grupos y Brackets")

data = get_data()
results = get_results()

tab_grupos, tab_brackets = st.tabs(["Clasificación de grupos", "Eliminatorias"])

with tab_grupos:
    standings = compute_group_standings(data, results)
    cols = st.columns(3)
    for i, (group, ranked) in enumerate(standings.items()):
        with cols[i % 3]:
            st.markdown(f"**Grupo {group}**")
            df = pd.DataFrame([{
                "Pos": pos,
                "🏳": flag_url(r.team.name),
                "Selección": r.team.name,
                "Pts": r.points,
                "J": r.played,
                "GF": r.gf,
                "GC": r.ga,
                "DG": r.gd,
            } for pos, r in enumerate(ranked, 1)])
            st.dataframe(
                df, hide_index=True, use_container_width=True,
                column_config={
                    "Pos": st.column_config.NumberColumn(width="small"),
                    "🏳": st.column_config.ImageColumn("", width="small"),
                },
            )

with tab_brackets:
    st.caption(
        "El cuadro se rellena con las selecciones reales (mejores terceros y "
        "ganadores) conforme avanzan las rondas; lo aún no determinado aparece como "
        "su referencia (W74, 3ABCDF…). Desliza en horizontal para ver todas las rondas."
    )
    teams = resolved_match_teams(data, results)
    SHORT = {Phase.R32: "1/16", Phase.R16: "1/8", Phase.QF: "1/4", Phase.SF: "1/2", Phase.FINAL: "Final"}
    DEPTH_PHASE = {0: Phase.FINAL, 1: Phase.SF, 2: Phase.QF, 3: Phase.R16, 4: Phase.R32}

    def feeders(n: int) -> list[int]:
        return [int(t[1:]) for t in data.bracket.get(n, ())
                if t[:1] in ("W", "L") and t[1:].isdigit()]

    order: dict[int, list[int]] = defaultdict(list)

    def dfs(n: int, depth: int) -> None:
        for f in feeders(n):
            dfs(f, depth + 1)
        order[depth].append(n)

    dfs(104, 0)  # raíz: la final

    def side_html(token: str, team, score, win: bool) -> str:
        if team is not None:
            cls = "bk-side win" if win else "bk-side"
            inner = flag_img(team.name, 11) + f'<span class="nm">{team.name}</span>'
        else:
            cls = "bk-side ph"
            inner = f'<span class="nm">{token}</span>'
        sc = "" if score is None else str(score)
        return f'<div class="{cls}">{inner}<span class="sc">{sc}</span></div>'

    def match_card(n: int) -> str:
        ht, at = teams[n]
        ho, ao = data.bracket[n]
        g = results.goals(n)
        ws = results.winner_side(n)
        return ('<div class="bk-match">'
                + side_html(ho, ht, g[0] if g else None, ws == "home")
                + side_html(ao, at, g[1] if g else None, ws == "away")
                + "</div>")

    cols = []
    for depth in sorted(order, reverse=True):  # R32 (4) → … → Final (0)
        body = "".join(match_card(n) for n in order[depth])
        cols.append(f'<div class="bk-col"><div class="bk-col-label">{SHORT[DEPTH_PHASE[depth]]}</div>'
                    f'<div class="bk-col-body">{body}</div></div>')
    st.markdown('<div class="bracket">' + "".join(cols) + "</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="bk-third"><div class="bk-col-label">3er y 4º puesto</div>'
        + match_card(103) + "</div>",
        unsafe_allow_html=True,
    )
