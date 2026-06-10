"""Clasificación de cada grupo y (próximamente) cuadro de eliminatorias."""

from __future__ import annotations

from collections import defaultdict

import streamlit as st

from porra.flags import flag_img
from porra.models import Phase
from porra.tournament import compute_group_standings, resolved_match_teams
from ui_common import configure_page, get_data, get_results

configure_page()
st.title("📊 Grupos y Brackets")

data = get_data()
results = get_results()

tab_grupos, tab_brackets = st.tabs(["Clasificación de grupos", "Eliminatorias"])

with tab_grupos:
    st.caption("Las dos primeras selecciones (en verde) avanzan a dieciseisavos.")
    standings = compute_group_standings(data, results)
    cards = []
    for group, ranked in standings.items():
        body = []
        for pos, r in enumerate(ranked, 1):
            cls = "q" if pos <= 2 else ""
            if r.team.name == "España":
                cls = (cls + " esp").strip()
            dg = f"+{r.gd}" if r.gd > 0 else str(r.gd)
            body.append(
                f'<tr class="{cls}"><td class="pos">{pos}</td>'
                f'<td class="sel">{flag_img(r.team.name, 13)}<span class="nm">{r.team.name}</span></td>'
                f'<td class="pts">{r.points}</td><td>{r.played}</td>'
                f'<td>{r.gf}</td><td>{r.ga}</td><td>{dg}</td></tr>'
            )
        cards.append(
            f'<div class="grp"><div class="grp-h">Grupo {group}</div>'
            '<table class="grp-t"><thead><tr><th></th><th class="sel">Selección</th>'
            '<th>Pts</th><th>J</th><th>GF</th><th>GC</th><th>DG</th></tr></thead>'
            '<tbody>' + "".join(body) + '</tbody></table></div>'
        )
    st.markdown('<div class="grp-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

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
