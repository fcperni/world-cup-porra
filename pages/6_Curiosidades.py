"""Curiosidades — el pulso de la porra partido a partido, agrupado por día.

* **Fase de grupos**: cómo se reparten los 19 pronósticos (1X2) — consenso,
  unanimidades y quién va a contracorriente (p. ej. en el inaugural todos dan
  ganador a México salvo Bonera —empate— y Paco —gana Sudáfrica—).
* **Eliminatorias**: qué selecciones mete la mayoría (y la minoría) en cada
  cruce, ya que ahí el jugador pronostica los equipos del enfrentamiento.

Cuando el partido ya se ha jugado, además revela si tenía razón la mayoría o la
minoría.
"""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    from datetime import date, timedelta

    from porra import stats
    from porra.flags import flag_img
    from porra.models import Phase
    from porra.tournament import resolved_match_teams
    from ui_common import PHASE_LABELS, configure_page, get_data, get_results, proper_name

    configure_page()
    st.title("🔮 Curiosidades")
    st.caption(
        "Cómo se reparten los **19 pronósticos** en cada partido: en grupos, el 1X2; "
        "en eliminatorias, qué selecciones prevén en cada cruce. Consensos, unanimidades "
        "y quién se sale del guion — y, si ya se jugó, si acertó la mayoría o la minoría."
    )

    data = get_data()
    results = get_results()  # dispara la sincronización automática y permite marcar aciertos
    splits = stats.match_sign_splits(data)
    ko_splits = stats.match_team_splits(data)
    ko_teams = resolved_match_teams(data, results)

    _WD = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    _MO = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
           7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}

    def fmt_day(d) -> str:
        return f"{_WD[d.weekday()]} {d.day} {_MO[d.month]}"

    def names_html(names: list[str]) -> str:
        return " · ".join(f'<span class="who">{proper_name(n)}</span>' for n in names)

    # ===================================================== fase de grupos (1X2)
    def outcome(sign: str, home: str, away: str) -> str:
        return {"1": f"gana {home}", "X": "empate", "2": f"gana {away}"}[sign]

    _OCLASS = {"1": "o1", "X": "ox", "2": "o2"}

    def outcome_html(sign: str, home: str, away: str) -> str:
        return f'<span class="{_OCLASS[sign]}">{outcome(sign, home, away)}</span>'

    def note_html(s, home: str, away: str) -> str:
        """La 'curiosidad' principal de un partido de grupos en lenguaje natural."""
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
        """Línea secundaria de grupos: marcador estrella y, si se jugó, quién acertó."""
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

    def head_html(m) -> str:
        g = results.goals(m.number)
        mid = (f'<span class="sc">{g[0]}-{g[1]}</span>' if g else '<span class="vs">vs</span>')
        tag = f"Grupo {m.group} · {m.matchday}" if m.matchday else f"Grupo {m.group}"
        return (
            '<div class="cz-head"><div class="cz-match">'
            f'{flag_img(m.home, 15)}<span>{m.home}</span>{mid}'
            f'{flag_img(m.away, 15)}<span>{m.away}</span></div>'
            f'<span class="cz-grp">{tag}</span></div>'
        )

    def group_card(m) -> str:
        s = splits[m.number]
        esp = " esp" if "España" in (m.home, m.away) else ""
        return (f'<div class="cz-card{esp}">' + head_html(m) + bar_html(s)
                + f'<div class="cz-note">{note_html(s, m.home, m.away)}</div>'
                + extras_html(s, m) + "</div>")

    # ===================================================== eliminatorias (equipos)
    def ko_head_html(m) -> str:
        ho, ao = data.bracket.get(m.number, (m.home, m.away))
        g = results.goals(m.number)
        score = f' <span class="sc">{g[0]}-{g[1]}</span>' if g else ""
        return ('<div class="cz-head">'
                f'<div class="cz-match cz-ko">{PHASE_LABELS[m.phase]}{score}</div>'
                f'<span class="cz-grp">{ho} vs {ao}</span></div>')

    def ko_chips_html(kt) -> str:
        if kt.total == 0:
            return ""
        lead = kt.ranked[0][1]
        chips = []
        for team, c in kt.ranked[:8]:
            cls = "cz-chip lead" if c == lead else "cz-chip solo" if c <= 2 else "cz-chip"
            chips.append(f'<span class="{cls}">{flag_img(team, 13)}<span>{team}</span>'
                         f'<span class="c">{c}</span></span>')
        return f'<div class="cz-teams">{"".join(chips)}</div>'

    def ko_note_html(kt) -> str:
        """Qué selecciones ve la mayoría (y la minoría) en el cruce."""
        if kt.total == 0:
            return '<span class="cz-extra">Sin pronósticos registrados.</span>'
        ranked = kt.ranked
        t0, c0 = ranked[0]
        # lobos solitarios: selecciones que mete muy poca gente (1-2)
        rare = sorted(((t, c) for t, c in ranked if c <= 2), key=lambda tc: tc[1])[:2]
        rare_html = ""
        if rare:
            partes = "; ".join(
                f'{flag_img(t, 12)}<span class="o2">{t}</span> — solo {names_html(kt.voters[t])}'
                for t, _ in rare)
            rare_html = f' El dato: {partes}.'
        if c0 == kt.total:  # todos meten a la misma selección
            head = (f'<span class="cz-badge uni">Unanimidad</span>'
                    f'Los {kt.total} meten a {flag_img(t0, 13)}<span class="o1">{t0}</span> '
                    f'en este cruce.')
            if len(ranked) > 1 and ranked[1][1] >= 3:
                t1, c1 = ranked[1]
                head += (f' El acompañante más repetido: {flag_img(t1, 12)}'
                         f'<span class="o1">{t1}</span> ({c1}).')
            return head + rare_html
        t1, c1 = ranked[1] if len(ranked) > 1 else (None, 0)
        pair = f'{flag_img(t0, 12)}<span class="o1">{t0}</span> (<b>{c0}</b>)'
        if t1:
            pair += f' y {flag_img(t1, 12)}<span class="o1">{t1}</span> (<b>{c1}</b>)'
        if c0 >= kt.total * 0.6:
            return f'El cruce más repetido: {pair}.' + rare_html
        return (f'<span class="cz-badge div">Repartido</span>'
                f'Cruce abierto entre {len(kt.counts)} selecciones; las más vistas: {pair}.'
                + rare_html)

    def ko_extras_html(kt, m) -> str:
        """Si el cruce ya está resuelto, la pareja real y cuántos la clavaron."""
        ht, at = ko_teams.get(m.number, (None, None))
        if not (ht and at):
            return ""
        real = {ht.name, at.name}
        nailed = sum(1 for p in data.players
                     if (pr := p.ko_matches.get(m.number)) and {pr.home_team, pr.away_team} == real)
        chip = (f'{flag_img(ht.name, 12)}{ht.name} - {flag_img(at.name, 12)}{at.name}')
        return (f'<div class="cz-extra">Cruce real: {chip} · '
                f'<b>{nailed}</b> de {kt.total} clavaron la pareja</div>')

    def ko_card(m) -> str:
        kt = ko_splits[m.number]
        esp = " esp" if "España" in kt.counts else ""
        return (f'<div class="cz-card{esp}">' + ko_head_html(m) + ko_chips_html(kt)
                + f'<div class="cz-note">{ko_note_html(kt)}</div>'
                + ko_extras_html(kt, m) + "</div>")

    # --------------------------------------------------------------- filtros
    # Los límites del selector abarcan todo el torneo (11 jun → 19 jul, la final),
    # no solo la fase de grupos, para poder navegar por todos los meses.
    span = [m.date.date() for m in data.matches if m.date]
    min_d, max_d = min(span), max(span)
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
        help="Unanimidades, casi-unanimidades y cruces con consenso fuerte o lobos solitarios.",
    )

    # st.date_input devuelve 1 o 2 fechas según se esté terminando de elegir el rango
    if isinstance(sel, (list, tuple)):
        start = sel[0] if sel else default_start
        end = sel[1] if len(sel) > 1 else max_d
    else:
        start = end = sel

    def is_juicy(m) -> bool:
        if m.phase is Phase.GROUPS:
            s = splits[m.number]
            return s.total > 0 and (s.is_unanimous or s.dissenters <= 2 or s.dissenters > 5)
        kt = ko_splits[m.number]
        return kt.total > 0 and (kt.ranked[0][1] == kt.total or any(c <= 2 for _, c in kt.ranked))

    matches = sorted(
        (m for m in data.matches if m.date and start <= m.date.date() <= end
         and (not only_curious or is_juicy(m))),
        key=lambda m: (m.date.timestamp(), m.number),
    )

    if not matches:
        st.info("No hay partidos en el rango seleccionado.", icon="🗓️")
        st.stop()

    # --------------------------------------------------------------- render por día
    html = ['<div class="cz">']
    current_day = None
    for m in matches:
        d = m.date.date()
        if d != current_day:
            current_day = d
            html.append(f'<div class="cz-day">{fmt_day(d)}</div>')
        html.append(group_card(m) if m.phase is Phase.GROUPS else ko_card(m))
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

    st.caption(f"{len(matches)} partidos en el rango seleccionado.")
