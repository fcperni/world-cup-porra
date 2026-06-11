"""Curiosidades — el pulso de la porra partido a partido, agrupado por día.

Para cada partido de la fase de grupos muestra cómo se reparten los 19
pronósticos (1X2): el consenso, las unanimidades y, sobre todo, quién va a
contracorriente (p. ej. en el inaugural todos dan ganador a México salvo Bonera
—empate— y Paco —gana Sudáfrica—). Cuando el partido ya se ha jugado, además
revela si tenía razón la mayoría o la minoría.
"""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    from datetime import date, timedelta

    from porra import stats
    from porra.flags import flag_img
    from porra.models import Phase
    from ui_common import configure_page, get_data, get_results, proper_name

    configure_page()
    st.title("🔮 Curiosidades")
    st.caption(
        "Cómo se reparten los **19 pronósticos** en cada partido de la fase de grupos: "
        "consensos, unanimidades y quién se sale del guion. Si el partido ya se jugó, "
        "verás si acertó la mayoría… o la minoría rebelde."
    )

    data = get_data()
    results = get_results()  # dispara la sincronización automática y permite marcar aciertos
    splits = stats.match_sign_splits(data)
    N = len(data.players)

    _WD = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    _MO = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
           7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}

    def fmt_day(d) -> str:
        return f"{_WD[d.weekday()]} {d.day} {_MO[d.month]}"

    def outcome(sign: str, home: str, away: str) -> str:
        return {"1": f"gana {home}", "X": "empate", "2": f"gana {away}"}[sign]

    _OCLASS = {"1": "o1", "X": "ox", "2": "o2"}

    def outcome_html(sign: str, home: str, away: str) -> str:
        return f'<span class="{_OCLASS[sign]}">{outcome(sign, home, away)}</span>'

    def names_html(names: list[str]) -> str:
        return " · ".join(f'<span class="who">{proper_name(n)}</span>' for n in names)

    def note_html(s, home: str, away: str) -> str:
        """La 'curiosidad' principal del partido en lenguaje natural."""
        if s.total == 0:
            return '<span class="cz-extra">Sin pronósticos registrados.</span>'
        maj = s.majority_sign
        if s.is_unanimous:
            return (f'<span class="cz-badge uni">Unanimidad</span>'
                    f'Los {s.total} coinciden: {outcome_html(maj, home, away)}.')
        # signos minoritarios (los que no son el mayoritario), de menos a más votados
        minor = sorted((sg for sg in stats.SIGNS if sg != maj and s.counts[sg]),
                       key=lambda sg: s.counts[sg])
        if s.dissenters <= 5:
            partes = "; ".join(
                f'{outcome_html(sg, home, away)} — {names_html(s.voters[sg])}' for sg in minor)
            return (f'<b>{s.counts[maj]}</b> lo tienen claro: {outcome_html(maj, home, away)}. '
                    f'Los únicos que se salen: {partes}.')
        # partido genuinamente repartido
        reparto = " · ".join(
            f'{outcome_html(sg, home, away)} (<b>{s.counts[sg]}</b>)'
            for sg in stats.SIGNS if s.counts[sg])
        extra = ""
        rare = minor[0] if minor else None
        if rare and s.counts[rare] <= 3:
            extra = (f' El dato: {outcome_html(rare, home, away)} — '
                     f'solo {names_html(s.voters[rare])}.')
        return f'<span class="cz-badge div">Repartido</span>Reparto: {reparto}.{extra}'

    def extras_html(s, m) -> str:
        """Línea secundaria: marcador estrella y, si se jugó, quién acertó."""
        bits = []
        if s.top_score and s.top_score[1] >= 3:
            (h, a), c = s.top_score
            bits.append(f"Marcador más repetido: <b>{h}-{a}</b> ({c})")
        if results.has(m.number):
            asign = results.sign(m.number)
            bits.append("Acertó la mayoría" if asign == s.majority_sign
                        else "¡Tenía razón la minoría!")
        return f'<div class="cz-extra">{" · ".join(bits)}</div>' if bits else ""

    def bar_html(s) -> str:
        if s.total == 0:
            return ""
        segs = "".join(
            f'<span class="seg {_OCLASS[sg].replace("o", "s")}" '
            f'style="width:{s.counts[sg] / s.total * 100:.4f}%"></span>'
            for sg in stats.SIGNS if s.counts[sg])
        return f'<div class="cz-bar">{segs}</div>'

    def head_html(m, home: str, away: str) -> str:
        g = results.goals(m.number)
        mid = (f'<span class="sc">{g[0]}-{g[1]}</span>' if g else '<span class="vs">vs</span>')
        tag = f"Grupo {m.group} · {m.matchday}" if m.matchday else f"Grupo {m.group}"
        return (
            '<div class="cz-head"><div class="cz-match">'
            f'{flag_img(home, 15)}<span>{home}</span>{mid}'
            f'{flag_img(away, 15)}<span>{away}</span></div>'
            f'<span class="cz-grp">{tag}</span></div>'
        )

    # --------------------------------------------------------------- filtros
    dated = [m for m in data.matches if m.phase is Phase.GROUPS and m.date]
    min_d = min(m.date.date() for m in dated)
    max_d = max(m.date.date() for m in dated)
    # Por defecto se ocultan los partidos disputados hace más de 3 días.
    default_start = min(max(min_d, date.today() - timedelta(days=3)), max_d)

    c1, c2 = st.columns([2, 1])
    sel = c1.date_input(
        "Rango de fechas", value=(default_start, max_d),
        min_value=min_d, max_value=max_d, format="DD/MM/YYYY",
        help="Por defecto se ocultan los partidos disputados hace más de 3 días; "
             "amplía el rango para revisar jornadas anteriores.",
    )
    only_curious = c2.toggle(
        "Solo los más jugosos", value=False,
        help="Unanimidades, casi-unanimidades (≤2 rebeldes) y partidos muy repartidos.",
    )

    # st.date_input devuelve 1 o 2 fechas según se esté terminando de elegir el rango
    if isinstance(sel, (list, tuple)):
        start = sel[0] if sel else default_start
        end = sel[1] if len(sel) > 1 else max_d
    else:
        start = end = sel

    def is_juicy(s) -> bool:
        return s.total > 0 and (s.is_unanimous or s.dissenters <= 2 or s.dissenters > 5)

    matches = sorted(
        (m for m in dated if start <= m.date.date() <= end
         and (not only_curious or is_juicy(splits[m.number]))),
        key=lambda m: (m.date.timestamp(), m.number),
    )

    if not matches:
        st.info("No hay partidos en el rango seleccionado.", icon="🗓️")
        st.stop()

    # --------------------------------------------------------------- render por día
    html = ['<div class="cz">']
    current_day = None
    for m in matches:
        s = splits[m.number]
        d = m.date.date() if m.date else None
        if d != current_day:
            current_day = d
            html.append(f'<div class="cz-day">{fmt_day(d) if d else "Por determinar"}</div>')
        esp = " esp" if "España" in (m.home, m.away) else ""
        html.append(
            f'<div class="cz-card{esp}">'
            + head_html(m, m.home, m.away)
            + bar_html(s)
            + f'<div class="cz-note">{note_html(s, m.home, m.away)}</div>'
            + extras_html(s, m)
            + "</div>"
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

    st.caption(f"{len(matches)} partidos en el rango seleccionado.")
