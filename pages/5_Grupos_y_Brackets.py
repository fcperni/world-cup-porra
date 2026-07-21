"""Clasificación de cada grupo y (próximamente) cuadro de eliminatorias."""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    import re
    from collections import defaultdict

    import analytics
    from porra.euro2028 import prettify
    from porra.flags import flag_img
    from porra.models import Phase
    from porra.tournament import (
        clinched_knockout,
        compute_group_standings,
        qualified_thirds_groups,
        resolved_match_teams,
        third_place_ranking,
    )
    from ui_common import configure_page, get_data, get_results

    configure_page()
    analytics.track("Grupos y Brackets")
    st.title("📊 Grupos y Brackets")

    data = get_data()
    results = get_results()
    fmt = data.format
    n_thirds = fmt.thirds_qualify
    first_ko_label = {Phase.R32: "dieciseisavos", Phase.R16: "octavos"}.get(fmt.first_ko_phase, "la ronda inicial")

    tab_grupos, tab_brackets = st.tabs(["Clasificación de grupos", "Eliminatorias"])

    with tab_grupos:
        standings = compute_group_standings(data, results)
        if not standings:
            st.info("Aún no hay grupos sorteados para esta competición. Puedes consultar el "
                    "calendario y las sedes en **Calendario y Resultados**.")
        st.caption(
            f"Avanzan a {first_ko_label} los **dos primeros** de cada grupo (verde) y los "
            f"**{n_thirds} mejores terceros** (ámbar)."
        )
        group_played = any(results.has(m.number) for m in data.matches if m.phase is Phase.GROUPS)
        # grupos cuyo 3º clasifica (provisional mientras se juega; vacío sin resultados)
        best_thirds = set(qualified_thirds_groups(standings, n_thirds)) if group_played else set()
        # selecciones con la clasificación a dieciseisavos ya asegurada (✓)
        clinched = clinched_knockout(data, results, standings)
        if clinched:
            st.caption(f"✓ = clasificación matemáticamente asegurada ({len(clinched)} selecciones).")
        cards = []
        for group, ranked in standings.items():
            body = []
            for pos, r in enumerate(ranked, 1):
                cls = "q" if pos <= 2 else "q3" if pos == 3 and group in best_thirds else ""
                if r.team.name == "España":
                    cls = (cls + " esp").strip()
                dg = f"+{r.gd}" if r.gd > 0 else str(r.gd)
                tick = '<span class="qtick">✓</span>' if r.team.name in clinched else ""
                body.append(
                    f'<tr class="{cls}"><td class="pos">{pos}</td>'
                    f'<td class="sel">{flag_img(r.team.name, 13)}<span class="nm">{r.team.name}</span>{tick}</td>'
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

        # --- Estado de las terceras posiciones ---
        if group_played:
            n_out = fmt.n_groups - n_thirds
            st.caption(
                f"Los **{fmt.n_groups} terceros** ordenados por los criterios FIFA (puntos → DG → "
                f"GF → ranking). Los **{n_thirds} primeros** (ámbar) se clasifican; los "
                f"**{n_out} últimos** (coral) quedan fuera. Este orden determinará los cruces "
                f"una vez terminen los {fmt.n_groups} grupos."
            )
            ranking = third_place_ranking(standings)  # todos los terceros, de mejor a peor
            rows = []
            for i, (group, r) in enumerate(ranking, 1):
                qualifies = i <= n_thirds
                classes = ["q3" if qualifies else "out"]
                if i == n_thirds:
                    classes.append("cut")  # separador entre clasificados y eliminados
                if r.team.name == "España":
                    classes.append("esp")
                dg = f"+{r.gd}" if r.gd > 0 else str(r.gd)
                tick = '<span class="qtick">✓</span>' if r.team.name in clinched else ""
                estado = "Clasificado" if qualifies else "Eliminado"
                rows.append(
                    f'<tr class="{" ".join(classes)}"><td class="pos">{i}</td>'
                    f'<td class="grp-c">{group}</td>'
                    f'<td class="sel">{flag_img(r.team.name, 13)}<span class="nm">{r.team.name}</span>{tick}</td>'
                    f'<td class="pts">{r.points}</td><td>{r.played}</td>'
                    f'<td>{r.gf}</td><td>{r.ga}</td><td>{dg}</td>'
                    f'<td class="st">{estado}</td></tr>'
                )
            st.markdown(
                '<div class="thirds"><div class="thirds-h">Mejores terceros</div>'
                '<table class="thirds-t"><thead><tr><th></th><th>Grupo</th>'
                '<th class="sel">Selección</th><th>Pts</th><th>J</th>'
                '<th>GF</th><th>GC</th><th>DG</th><th>Estado</th></tr></thead>'
                '<tbody>' + "".join(rows) + '</tbody></table></div>',
                unsafe_allow_html=True,
            )

    with tab_brackets:
        st.caption(
            "El cuadro se rellena con las selecciones reales conforme se aseguran: una "
            "posición aparece (p.ej. **1E → Alemania**) en cuanto es matemáticamente "
            "definitiva, aunque el grupo no haya terminado. Lo aún no determinado se "
            "muestra como su referencia (W74, 3ABCDF…). Desliza en horizontal para ver "
            "todas las rondas."
        )

        teams = resolved_match_teams(data, results)
        PHASE_SHORT = {Phase.R32: "1/16", Phase.R16: "1/8", Phase.QF: "1/4",
                       Phase.SF: "1/2", Phase.FINAL: "Final"}
        # fases del árbol principal (sin el 3er/4º puesto), de la final hacia atrás
        bracket_phases = [ph for ph in fmt.ko_order if ph is not Phase.THIRD]
        DEPTH_PHASE = {i: ph for i, ph in enumerate(reversed(bracket_phases))}

        _MATCH_RE = re.compile(r"Match\s+(\d+)")

        def feeders(n: int) -> list[int]:
            """Partidos que alimentan a ``n`` (tokens ``W##``/``L##`` o ``Winner Match ##``)."""
            out = []
            for t in data.bracket.get(n, ()):
                m = re.match(r"^[WL](\d+)$", t) or _MATCH_RE.search(t)
                if m:
                    out.append(int(m.group(1)))
            return out

        order: dict[int, list[int]] = defaultdict(list)

        def dfs(n: int, depth: int) -> None:
            for f in feeders(n):
                dfs(f, depth + 1)
            order[depth].append(n)

        dfs(fmt.final_match_number, 0)  # raíz: la final

        def side_html(token: str, team, score, win: bool) -> str:
            if team is not None:
                cls = "bk-side win" if win else "bk-side"
                inner = flag_img(team.name, 11) + f'<span class="nm">{team.name}</span>'
            else:
                cls = "bk-side ph"
                inner = f'<span class="nm">{prettify(token)}</span>'
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
        for depth in sorted(order, reverse=True):  # ronda inicial → … → Final (0)
            label = PHASE_SHORT.get(DEPTH_PHASE.get(depth), "")
            body = "".join(match_card(n) for n in order[depth])
            cols.append(f'<div class="bk-col"><div class="bk-col-label">{label}</div>'
                        f'<div class="bk-col-body">{body}</div></div>')
        st.markdown('<div class="bracket">' + "".join(cols) + "</div>", unsafe_allow_html=True)

        third_num = fmt.third_place_match_number
        if third_num is not None and third_num in data.bracket:
            st.markdown(
                '<div class="bk-third"><div class="bk-col-label">3er y 4º puesto</div>'
                + match_card(third_num) + "</div>",
                unsafe_allow_html=True,
            )
