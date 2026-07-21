"""Clasificación general de los 19 participantes."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from page_guard import safe_page

with safe_page():
    import analytics
    from porra.scoring import CATEGORIES, position_history, scoreboard
    from ui_common import configure_page, fmt, get_data, get_results, proper_name, require_porra

    configure_page()
    analytics.track("Clasificación")
    st.title("🏆 Clasificación")

    data = get_data()
    require_porra(data)
    results = get_results()
    sb = scoreboard(data, results)

    if all(s.total == 0 for s in sb):
        st.info("Todavía no hay puntos: aún no se ha jugado ningún partido. La clasificación "
                "se actualizará automáticamente en cuanto haya resultados.", icon="🗓️")
        st.stop()

    # Sin scroll: con 19 jugadores cabe todo de un vistazo. Cada fila ocupa ~35px
    # y la cabecera otro tanto; damos la altura justa para que no aparezca scroll.
    def full_height(n: int) -> int:
        return (n + 1) * 35 + 3

    # Tabla principal: posición, jugador, total
    main = pd.DataFrame({
        "Pos": range(1, len(sb) + 1),
        "Jugador": [proper_name(s.name) for s in sb],
        "Puntos": [round(s.total, 1) for s in sb],
    })
    st.subheader("Ranking")
    st.dataframe(
        main,
        hide_index=True,
        width="stretch",
        height=full_height(len(main)),
        column_config={"Puntos": st.column_config.NumberColumn(format="%.1f")},
    )

    # Desglose por categoría (solo columnas con algún punto). Tabla temática (HTML)
    # para ser coherente con el resto de la app (Cuadro de honor, Grupos…).
    st.subheader("Desglose por categoría")
    active = [c for c in CATEGORIES if any(s.categories[c] for s in sb)]
    if not active:
        st.caption("Sin categorías con puntos todavía.")
    else:
        head = "".join(f"<th>{c}</th>" for c in active)
        body = []
        for i, s in enumerate(sb, 1):
            cells = "".join(f"<td>{fmt(s.categories[c])}</td>" for c in active)
            body.append(f'<tr><td class="pos">{i}</td>'
                        f'<td class="who">{proper_name(s.name)}</td>'
                        f'{cells}<td class="tot">{fmt(s.total)}</td></tr>')
        st.markdown(
            '<div class="cat-wrap"><table class="cat-t"><thead><tr>'
            f'<th class="pos"></th><th class="who">Jugador</th>{head}<th class="tot">Total</th>'
            '</tr></thead><tbody>' + "".join(body) + "</tbody></table></div>",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------ evolución
    # Gráfico de líneas por segmentos: cómo ha ido subiendo/bajando de posición
    # cada jugador, día a día, según se cerraban resultados.
    st.subheader("Evolución de posiciones")

    _WD = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    _MO = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
           7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}

    # El gráfico va en su propio try: si Altair fallara en algún entorno, la
    # clasificación (lo importante) sigue mostrándose en lugar de tirar la página.
    try:
        days, history = position_history(data, results)
        if len(days) < 2:
            st.caption("La evolución aparecerá cuando haya resultados de al menos dos días.")
        else:
            labels = [f"{_WD[d.weekday()]} {d.day} {_MO[d.month]}" for d in days]
            n = len(sb)
            rows = [
                {"Día": labels[i], "Jugador": proper_name(name), "Posición": pos, "_o": i}
                for name, positions in history.items()
                for i, pos in enumerate(positions)
            ]
            ev = pd.DataFrame(rows)

            TEXT, MUTED, LINE = "#eaf1f3", "#8a99a6", "#27333f"
            # Click en la leyenda para resaltar la línea de un jugador (el resto se atenúa).
            sel = alt.selection_point(fields=["Jugador"], bind="legend")

            base = alt.Chart(ev).encode(
                x=alt.X("Día:N", sort=labels, title=None,
                        axis=alt.Axis(labelAngle=-40, labelColor=MUTED, domainColor=LINE,
                                      tickColor=LINE, labelFontSize=11)),
                y=alt.Y("Posición:Q",
                        scale=alt.Scale(domain=[n + 0.5, 0.5]),
                        axis=alt.Axis(values=list(range(1, n + 1)), title="Posición",
                                      titleColor=MUTED, labelColor=MUTED, tickCount=n,
                                      domainColor=LINE, gridColor=LINE, gridOpacity=0.35)),
                color=alt.Color("Jugador:N",
                                scale=alt.Scale(scheme="tableau20"),
                                legend=alt.Legend(orient="bottom", title=None, columns=4,
                                                  symbolType="stroke", labelColor=TEXT,
                                                  labelFontSize=12, symbolStrokeWidth=3)),
                opacity=alt.condition(sel, alt.value(1.0), alt.value(0.12)),
                order=alt.Order("_o:Q"),
            )
            lines = base.mark_line(strokeWidth=2.5, interpolate="monotone")
            points = base.mark_point(filled=True, size=55, opacity=1).encode(
                opacity=alt.condition(sel, alt.value(1.0), alt.value(0.12)),
                tooltip=[alt.Tooltip("Jugador:N"),
                         alt.Tooltip("Posición:Q", title="Posición"),
                         alt.Tooltip("Día:N", title="Día")],
            )
            chart = (
                (lines + points)
                .add_params(sel)
                .properties(height=460)
                .configure_view(strokeWidth=0, fill="transparent")
                .configure(background="transparent")
                .configure_legend(labelLimit=140, symbolLimit=n)
            )
            st.altair_chart(chart, width="stretch")
            st.caption("La posición 1 es el liderato. Toca un jugador en la leyenda para "
                       "resaltar su recorrido; vuelve a tocarlo para ver todos.")
    except Exception:  # noqa: BLE001 — el gráfico es secundario; nunca debe tumbar la página
        st.caption("La evolución de posiciones no está disponible ahora mismo.")
