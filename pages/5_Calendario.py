"""Calendario — consulta sencilla de todos los partidos y sus resultados."""

from __future__ import annotations

from datetime import date

import streamlit as st

from porra.flags import flag_img
from porra.models import Phase
from porra.tournament import resolved_match_teams
from ui_common import PHASE_LABELS, configure_page, get_data, get_results

configure_page()
st.title("📅 Calendario")

data = get_data()
results = get_results()
teams = resolved_match_teams(data, results)

_WD = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
_MO = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
       7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}


def fmt_day(d: date) -> str:
    return f"{_WD[d.weekday()]} {d.day} {_MO[d.month]}"


def tag(m) -> str:
    if m.phase is Phase.GROUPS:
        return f"Grupo {m.group} · {m.matchday}"
    return PHASE_LABELS[m.phase]


def names(m):
    """(nombre_local, nombre_visitante, es_placeholder) para el partido."""
    if m.phase is Phase.GROUPS:
        return m.home, m.away, False
    ht, at = teams[m.number]
    h = ht.name if ht else data.bracket.get(m.number, (m.home, m.away))[0]
    a = at.name if at else data.bracket.get(m.number, (m.home, m.away))[1]
    return h, a, (ht is None or at is None)


def team_html(name: str, side: str, placeholder: bool) -> str:
    cls = f"fx-team {side}" + (" ph" if placeholder else "")
    fl = "" if placeholder else flag_img(name, height=15)
    chip = f'<span class="fl">{fl}</span>' if fl else ""
    nm = f'<span class="nm">{name}</span>'
    inner = f"{nm} {chip}" if side == "home" else f"{chip} {nm}"
    return f'<div class="{cls}">{inner}</div>'


def score_html(m) -> str:
    g = results.goals(m.number)
    if g is None:
        when = m.date.strftime("%H:%M") if m.date else "vs"
        return f'<div class="fx-score pending">{when}</div>'
    extra = ""
    if m.phase.is_knockout and g[0] == g[1] and m.number in results.ko_winners:
        side = results.ko_winners[m.number]
        h, a, _ = names(m)
        extra = f'<span class="pen">pen {flag_img(h if side=="home" else a, height=9)}</span>'
    return f'<div class="fx-score played">{g[0]}-{g[1]}{extra}</div>'


# ----------------------------------------------------------------- filtros
c1, c2 = st.columns([3, 1])
choice = c1.radio("Fase", ["Todas", "Grupos", "Eliminatorias"], horizontal=True, label_visibility="collapsed")
only_played = c2.toggle("Solo jugados")

matches = sorted(data.matches, key=lambda m: ((m.date.timestamp() if m.date else 0), m.number))
if choice == "Grupos":
    matches = [m for m in matches if m.phase is Phase.GROUPS]
elif choice == "Eliminatorias":
    matches = [m for m in matches if m.phase.is_knockout]
if only_played:
    matches = [m for m in matches if results.has(m.number)]

if not matches:
    st.info("No hay partidos que mostrar con este filtro.")
    st.stop()

# ----------------------------------------------------------------- render por día
html = ['<div class="fx">']
current_day = None
for m in matches:
    d = m.date.date() if m.date else None
    if d != current_day:
        current_day = d
        html.append(f'<div class="fx-day">{fmt_day(d) if d else "Por determinar"}</div>')
    h, a, ph = names(m)
    html.append(
        '<div class="fx-row">'
        f'<div class="fx-tag">{tag(m)}</div>'
        f'{team_html(h, "home", ph)}'
        f'{score_html(m)}'
        f'{team_html(a, "away", ph)}'
        "</div>"
    )
html.append("</div>")
st.markdown("".join(html), unsafe_allow_html=True)

played = sum(1 for m in matches if results.has(m.number))
st.caption(f"{played} de {len(matches)} partidos jugados.")
