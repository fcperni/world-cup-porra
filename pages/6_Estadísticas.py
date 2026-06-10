"""Estadísticas — KPIs agregados de la porra (predicciones y aciertos)."""

from __future__ import annotations

import streamlit as st

from porra import stats
from porra.flags import flag_img
from porra.models import Phase
from ui_common import configure_page, get_data, get_results, proper_name

configure_page()
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
