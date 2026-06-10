"""Introducir y editar los resultados de los partidos."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from porra.flags import with_flag
from porra.models import KO_ORDER, Phase
from porra.results_store import HONOR_KEYS
from porra.sources.base import sync_results
from porra.sources.espn import ESPNSource
from porra.sources.wikipedia import WikipediaSource
from porra.tournament import resolved_match_teams
from ui_common import HONOR_LABELS, PHASE_LABELS, configure_page, get_data, get_results, persist

configure_page()
st.title("📝 Resultados")

data = get_data()
results = get_results()

# --------------------------------------------------------------------------- sincronización
with st.expander("🔄 Sincronizar resultados (ESPN → Wikipedia)", expanded=False):
    st.caption(
        "Descarga los resultados publicados (ESPN como fuente principal, Wikipedia "
        "de reserva), los empareja con el calendario y te muestra los cambios antes "
        "de aplicarlos. La entrada manual siempre prevalece: revisa el diff."
    )
    if st.button("Buscar resultados"):
        with st.spinner("Consultando ESPN y Wikipedia…"):
            teams_now = resolved_match_teams(data, results)
            st.session_state.proposals = sync_results(
                data, results, [ESPNSource(), WikipediaSource()], teams_now)

    proposals = st.session_state.get("proposals")
    if proposals is not None:
        changes = []
        for num, mr in sorted(proposals.items()):
            m = data.match_by_number(num)
            current = results.goals(num)
            new = (mr.home_goals, mr.away_goals)
            if current != new:
                changes.append({"Nº": num,
                                "Partido": f"{with_flag(m.home)} - {with_flag(m.away)}" if m else str(num),
                                "Actual": f"{current[0]}-{current[1]}" if current else "—",
                                "Propuesto": f"{new[0]}-{new[1]}"})
        if not changes:
            st.success("Todo al día: no hay resultados nuevos que aplicar.")
        else:
            st.dataframe(pd.DataFrame(changes), hide_index=True, use_container_width=True)
            if st.button(f"✅ Aplicar {len(changes)} cambios", type="primary"):
                for num, mr in proposals.items():
                    results.set_match(num, mr.home_goals, mr.away_goals)
                    if mr.winner and mr.home_goals == mr.away_goals:
                        results.ko_winners[num] = mr.winner
                persist(results)
                del st.session_state.proposals
                st.success(f"{len(changes)} resultados aplicados.")
                st.rerun()

tab_grupos, tab_ko, tab_honor = st.tabs(["Fase de grupos", "Eliminatorias", "Cuadro de honor"])

# --------------------------------------------------------------------------- grupos
with tab_grupos:
    st.caption(
        "Introduce los goles de cada partido. Deja en blanco los no jugados. "
        "Los cambios se aplican al pulsar **Guardar**."
    )
    gm = sorted([m for m in data.matches if m.phase is Phase.GROUPS], key=lambda m: (m.group, m.number))
    rows = []
    for m in gm:
        g = results.goals(m.number)
        rows.append({"Nº": m.number, "Grupo": m.group, "Jor.": m.matchday,
                     "Local": with_flag(m.home),
                     "GL": g[0] if g else None, "GV": g[1] if g else None,
                     "Visitante": with_flag(m.away),
                     "Bonus": f"x{m.bonus}" if m.bonus > 1 else ""})
    edited = st.data_editor(
        pd.DataFrame(rows), hide_index=True, use_container_width=True,
        disabled=["Nº", "Grupo", "Jor.", "Local", "Visitante", "Bonus"],
        column_config={
            "GL": st.column_config.NumberColumn("GL", min_value=0, max_value=99, step=1),
            "GV": st.column_config.NumberColumn("GV", min_value=0, max_value=99, step=1),
        },
        key="editor_grupos",
    )
    if st.button("💾 Guardar resultados de grupos", type="primary"):
        n_set = 0
        for _, r in edited.iterrows():
            gl, gv = r["GL"], r["GV"]
            if pd.notna(gl) and pd.notna(gv):
                results.set_match(int(r["Nº"]), int(gl), int(gv))
                n_set += 1
            else:
                results.set_match(int(r["Nº"]), None, None)
        persist(results)
        st.success(f"Guardado. {n_set} partidos con resultado.")
        st.rerun()

# --------------------------------------------------------------------------- eliminatorias
with tab_ko:
    st.caption(
        "Los cruces se rellenan automáticamente con las selecciones reales según "
        "se completan las rondas anteriores. En caso de empate, indica quién pasa "
        "(penaltis) en la columna **Pasa**."
    )
    teams = resolved_match_teams(data, results)
    any_resolved = False
    for phase in KO_ORDER:
        matches = sorted([m for m in data.matches if m.phase is phase], key=lambda m: m.number)
        resolved = [m for m in matches if teams[m.number][0] and teams[m.number][1]]
        if not resolved:
            continue
        any_resolved = True
        st.markdown(f"**{PHASE_LABELS[phase]}**")
        rows = []
        for m in resolved:
            ht, at = teams[m.number]
            g = results.goals(m.number)
            side = results.ko_winners.get(m.number, "")
            pasa = ht.name if side == "home" else at.name if side == "away" else ""
            rows.append({"Nº": m.number, "Local": with_flag(ht.name),
                         "GL": g[0] if g else None, "GV": g[1] if g else None,
                         "Visitante": with_flag(at.name), "Pasa": pasa})
        names_by_num = {m.number: (teams[m.number][0].name, teams[m.number][1].name) for m in resolved}
        edited = st.data_editor(
            pd.DataFrame(rows), hide_index=True, use_container_width=True,
            disabled=["Nº", "Local", "Visitante"],
            column_config={
                "GL": st.column_config.NumberColumn("GL", min_value=0, max_value=99, step=1),
                "GV": st.column_config.NumberColumn("GV", min_value=0, max_value=99, step=1),
                "Pasa": st.column_config.SelectboxColumn(
                    "Pasa (si empate)",
                    options=[""] + [n for pair in names_by_num.values() for n in pair],
                    help="Solo si hay empate: quién avanza por penaltis"),
            },
            key=f"editor_ko_{phase.value}",
        )
        if st.button(f"💾 Guardar {PHASE_LABELS[phase]}", key=f"save_{phase.value}", type="primary"):
            for _, r in edited.iterrows():
                num = int(r["Nº"])
                gl, gv = r["GL"], r["GV"]
                if pd.notna(gl) and pd.notna(gv):
                    results.set_match(num, int(gl), int(gv))
                    hn, an = names_by_num[num]
                    if int(gl) == int(gv) and r["Pasa"] in (hn, an):
                        results.ko_winners[num] = "home" if r["Pasa"] == hn else "away"
                    else:
                        results.ko_winners.pop(num, None)
                else:
                    results.set_match(num, None, None)
                    results.ko_winners.pop(num, None)
            persist(results)
            st.success(f"{PHASE_LABELS[phase]} guardado.")
            st.rerun()
        st.divider()
    if not any_resolved:
        st.info("Completa la fase de grupos para que se generen los cruces de dieciseisavos.", icon="ℹ️")

# --------------------------------------------------------------------------- honor
with tab_honor:
    st.caption(
        "Campeón, subcampeón y 3er puesto se deducen del cuadro al completarse, "
        "pero las **botas** (goleadores) y **balones** (jugadores) son de entrada manual."
    )
    team_names = [""] + [t.name for t in data.teams]
    with st.form("form_honor"):
        new_honor = {}
        c1, c2, c3 = st.columns(3)
        for key, col in zip(["campeon", "subcampeon", "tercero"], [c1, c2, c3]):
            current = results.honor.get(key) or ""
            idx = team_names.index(current) if current in team_names else 0
            new_honor[key] = col.selectbox(HONOR_LABELS[key], team_names, index=idx,
                                           format_func=with_flag)
        st.markdown("**Botas y balones** — escribe el nombre del jugador")
        cols = st.columns(3)
        manual = [k for k in HONOR_KEYS if k not in ("campeon", "subcampeon", "tercero")]
        for i, key in enumerate(manual):
            new_honor[key] = cols[i % 3].text_input(HONOR_LABELS[key], value=results.honor.get(key) or "")
        if st.form_submit_button("💾 Guardar cuadro de honor", type="primary"):
            for key in HONOR_KEYS:
                val = (new_honor.get(key) or "").strip()
                results.honor[key] = val or None
            persist(results)
            st.success("Cuadro de honor guardado.")
